"""工具函数：帧数计算、图片处理、节点调用辅助"""

import torch
import logging
import comfy.utils
import nodes

# H3 常量
FPS = 24
FRAME_PER_TOKEN = (1, 4, 4, 4, 4)
AUDIO_SAMPLE_RATE = 32000

_LOG = logging.getLogger("MiniMaxH3-LongVideo")


def get_node_class(class_name):
    """从ComfyUI节点映射中获取节点类"""
    if class_name in nodes.NODE_CLASS_MAPPINGS:
        return nodes.NODE_CLASS_MAPPINGS[class_name]
    raise ValueError(f"节点未找到: {class_name}")


def call_node(class_name, **kwargs):
    """调用ComfyUI节点，返回结果元组"""
    cls = get_node_class(class_name)
    instance = cls()
    func = getattr(instance, cls.FUNCTION)  # 绑定方法，self自动传递
    return func(**kwargs)


def seconds_to_frames(seconds, fps=FPS):
    """秒转帧数"""
    return int(round(seconds * fps))


def frames_to_latent_steps(frame_count):
    """计算H3视频VAE的latent步数
    H3视频VAE的下采样公式：max(1, (n - 5) // 17 * 5 + 2)
    """
    if frame_count <= 1:
        return 1
    return max(1, (frame_count - 5) // 17 * 5 + 2)


def resize_image(image_tensor, width, height):
    """调整图片尺寸 [B,H,W,C] -> [B,height,width,3]"""
    samples = image_tensor[..., :3].movedim(-1, 1)
    samples = comfy.utils.common_upscale(samples, width, height, "lanczos", "crop")
    return samples.movedim(1, -1)


def parse_shots_data(shots_json):
    """解析分镜头数据JSON
    格式: {"shots": [{"id": "shot_1", "prompt": "...", "duration": 3, "seed": 12345, "enabled": true}]}
    """
    import json
    if not shots_json or shots_json.strip() == "":
        # 默认1段（用户要求最少1段），提示词强化景别约束和画面稳定
        return [
            {"id": "shot_1", "prompt": "极特写，人物面部，取景至锁骨，画面稳定无抖动，镜头固定，灵动表情，眨眼微笑，发丝飞扬，眼神明亮，禁止全身禁止中远景", "duration": 3, "seed": 42, "enabled": True}
        ]
    try:
        data = json.loads(shots_json)
        shots = data.get("shots", [])
        # 过滤启用的分镜头
        enabled = [s for s in shots if s.get("enabled", True)]
        if not enabled:
            raise ValueError("至少需要一个启用的分镜头")
        return enabled
    except json.JSONDecodeError as e:
        raise ValueError(f"分镜头数据JSON解析失败: {e}")


def _extend_audio_tail(waveform, target_length, sample_rate=32000):
    """用音频末尾的微小片段循环延伸，填补音频与目标长度的间隙

    不补静音（会导致拼接处可感知的静音间隙），而是用末尾约50ms的片段
    做平滑循环延伸。延伸部分在交叉淡入淡出区域（40ms）内，人耳几乎
    感知不到重复。

    Args:
        waveform: [B,C,L] 音频张量
        target_length: 目标长度（samples）
        sample_rate: 采样率

    Returns:
        延伸后的waveform [B,C,target_length]
    """
    current_len = waveform.shape[-1]
    if current_len >= target_length:
        return waveform[..., :target_length]

    need_pad = target_length - current_len
    # 取末尾50ms作为循环片段（至少100 samples）
    loop_len = max(int(sample_rate * 0.05), 100)
    loop_len = min(loop_len, current_len)  # 不超过当前长度
    loop_segment = waveform[..., -loop_len:].clone()

    # 在循环片段的开头和结尾做5ms fade，避免循环点咔嗒声
    fade_len = min(int(sample_rate * 0.005), loop_len // 4)
    if fade_len > 0:
        fade_in = torch.linspace(0, 1, fade_len, device=waveform.device)
        fade_out = torch.linspace(1, 0, fade_len, device=waveform.device)
        loop_segment[..., :fade_len] *= fade_in
        loop_segment[..., -fade_len:] *= fade_out

    # 循环延伸
    padded = waveform.clone()
    remaining = need_pad
    while remaining > 0:
        take = min(remaining, loop_len)
        padded = torch.cat([padded, loop_segment[..., :take]], dim=-1)
        remaining -= take

    return padded[..., :target_length]


def _trim_silence(waveform, sample_rate=32000, threshold_db=-45, min_silence_ms=20):
    """trim掉音频开头和结尾的静音

    MiniMax-H3生成的音频开头和结尾可能有静音（淡入淡出），导致拼接时出现
    可感知的间隙。本函数检测并trim掉首尾低于阈值的静音。

    Args:
        waveform: [B,C,L] 音频张量
        sample_rate: 采样率
        threshold_db: 静音阈值（dB），低于此值视为静音
        min_silence_ms: 最小静音时长（毫秒），短于此的不trim

    Returns:
        trim后的waveform [B,C,L']
    """
    if waveform.shape[-1] == 0:
        return waveform

    # 计算每帧的RMS（10ms粒度）
    frame_size = max(int(sample_rate * 0.01), 1)  # 10ms
    n_frames = waveform.shape[-1] // frame_size
    if n_frames == 0:
        return waveform

    # 取第一个batch/channel的能量作为参考（多通道应该一致）
    mono = waveform[0, 0] if waveform.dim() >= 2 else waveform[0]
    rms_list = []
    for i in range(n_frames):
        frame = mono[i*frame_size:(i+1)*frame_size]
        rms = torch.sqrt(torch.mean(frame.float()**2))
        rms_db = 20 * torch.log10(rms + 1e-10)
        rms_list.append(rms_db.item())

    threshold = threshold_db
    min_silence_frames = max(int(min_silence_ms / 10), 1)

    # 找开头第一个非静音帧
    start_frame = 0
    silence_count = 0
    for i, db in enumerate(rms_list):
        if db < threshold:
            silence_count += 1
            if silence_count >= min_silence_frames:
                start_frame = i + 1
        else:
            break

    # 找结尾最后一个非静音帧
    end_frame = n_frames
    silence_count = 0
    for i in range(n_frames - 1, -1, -1):
        if rms_list[i] < threshold:
            silence_count += 1
            if silence_count >= min_silence_frames:
                end_frame = i
        else:
            break

    if start_frame >= end_frame:
        return waveform  # 全是静音，不trim

    start_sample = start_frame * frame_size
    end_sample = end_frame * frame_size

    trimmed = waveform[..., start_sample:end_sample]
    if trimmed.shape[-1] > 0:
        return trimmed
    return waveform


def concat_audio(audio_list, crossfade_ms=100, target_lengths=None):
    """拼接多个音频字典，使用100ms等功率交叉淡入淡出（equal-power crossfade）

    社区成熟方案（参考H3 Motion Context v0.2.0和ComfyUI-H3-Multishot）：
    1. trim掉每段音频首尾的静音（MiniMax-H3生成的音频自带淡入淡出静音）
    2. 100ms等功率交叉淡入淡出拼接（不使用末尾循环延伸，避免可感知的重复）

    等功率曲线使用sqrt()而非线性，保证衔接处总功率恒定，人耳感知无音量波动。

    Args:
        audio_list: [{"waveform": [B,C,L], "sample_rate": int}, ...]
        crossfade_ms: 交叉淡入淡出时长（毫秒），默认100ms
        target_lengths: 每段音频对应的目标长度（samples），用于pad对齐。
                        如果为None，不做对齐。

    Returns:
        {"waveform": [B,C,L], "sample_rate": int} 或 None
    """
    if not audio_list:
        return None
    if len(audio_list) == 1:
        result = audio_list[0]
        if result is not None:
            # trim首尾静音
            wf = _trim_silence(result["waveform"], result["sample_rate"])
            # 仅截断过长的，不做循环延伸
            if target_lengths and len(target_lengths) > 0:
                target = target_lengths[0]
                if wf.shape[-1] > target:
                    wf = wf[..., :target]
            result = {"waveform": wf, "sample_rate": result["sample_rate"]}
        return result

    waveforms = []
    for i, a in enumerate(audio_list):
        if a is None:
            continue
        wf = a["waveform"]
        sr = a["sample_rate"]

        # Step 1: trim首尾静音（关键！解决MiniMax-H3音频开头静音导致的拼接间隙）
        original_len = wf.shape[-1]
        wf = _trim_silence(wf, sr)
        trimmed_len = wf.shape[-1]
        if trimmed_len < original_len:
            _LOG.info(f"[concat_audio] 第{i+1}段音频trim静音: {original_len} -> {trimmed_len} samples (去掉{original_len-trimmed_len}={ (original_len-trimmed_len)/sr*1000:.0f}ms)")

        # Step 2: 长度对齐（仅截断过长的，不做循环延伸避免重复）
        if target_lengths and i < len(target_lengths):
            target = target_lengths[i]
            if wf.shape[-1] > target:
                wf = wf[..., :target]
        waveforms.append(wf)

    if not waveforms:
        return None

    sr = audio_list[0]["sample_rate"]
    crossfade_samples = int(sr * crossfade_ms / 1000)  # 40ms = 1280 samples @ 32kHz

    # 等功率交叉淡入淡出曲线（sqrt保证功率恒定）
    fade_out = torch.sqrt(torch.linspace(1.0, 0.0, crossfade_samples, device=waveforms[0].device))
    fade_in = torch.sqrt(torch.linspace(0.0, 1.0, crossfade_samples, device=waveforms[0].device))

    result = waveforms[0].clone()

    for i in range(1, len(waveforms)):
        next_wave = waveforms[i]
        # 确保交叉区域不超过较短音频的长度
        cf = min(crossfade_samples, result.shape[-1], next_wave.shape[-1])
        if cf < 2:
            # 音频太短，直接拼接
            result = torch.cat([result, next_wave], dim=-1)
            continue

        # 取当前结果的最后cf帧做淡出
        tail = result[..., -cf:].clone()
        # 取下一段的前cf帧做淡入
        head = next_wave[..., :cf].clone()

        # 等功率交叉淡入淡出
        crossfaded = tail * fade_out[-cf:] + head * fade_in[:cf]

        # 拼接：去掉当前结果的最后cf帧，加上交叉区域，加上下一段剩余部分
        result = torch.cat([result[..., :-cf], crossfaded, next_wave[..., cf:]], dim=-1)

    return {"waveform": result, "sample_rate": sr}
