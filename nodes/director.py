"""MiniMax-H3 长视频导演节点
动态分镜头管理，循环生成多段视频，自动latent传递和拼接
"""

import json
import logging
import torch
import comfy.utils
import comfy.model_management

from .utils import (
    call_node, seconds_to_frames, resize_image,
    parse_shots_data, concat_audio, FPS, AUDIO_SAMPLE_RATE
)

_LOG = logging.getLogger("minimax_h3_longvideo")


def build_prompt(global_prompt, shot_prompt, shot_index):
    """组装MiniMax-H3官方六段式提示词格式

    参考：ComfyUI-H3-Multishot项目验证的格式
    1. subject_definitions - 主体定义（人物外观，每段逐字重复保证一致性）
    2. summary - 摘要
    3. detailed_description - 详细描述（镜头语言+动作）
    4. overall_soundscape - 整体音景
    5. non_diegetic_music - 非剧情音乐（明确无歌词人声）

    Args:
        global_prompt: 通用提示词（人物外观描述，每段逐字重复）
        shot_prompt: 该分镜头的详细描述（镜头语言+动作）
        shot_index: 分镜头索引（从0开始）

    Returns:
        组装后的完整提示词
    """
    # subject_definitions：人物外观，每段逐字重复（保证人物一致性的核心）
    subject = global_prompt.strip() if global_prompt else "青春活力的少女写真"

    # summary：任务类型摘要
    summary = "参考生视频任务，基于参考图生成连续视频片段"

    # detailed_description：该段的镜头语言和动作
    detailed = shot_prompt.strip() if shot_prompt else "人物自然姿态"

    # overall_soundscape：整体音景（纯乐器配乐）
    soundscape = "纯乐器背景音乐，节奏舒缓，氛围柔和，环境音自然"

    # non_diegetic_music：非剧情音乐（明确无歌词人声）
    music = "无歌词人声，无旁白，无歌唱，纯乐器配乐贯穿始终"

    # 组装六段式
    full_prompt = (
        f"[subject_definitions]\n{subject}\n\n"
        f"[summary]\n{summary}\n\n"
        f"[detailed_description]\n{detailed}\n\n"
        f"[overall_soundscape]\n{soundscape}\n\n"
        f"[non_diegetic_music]\n{music}"
    )

    return full_prompt


class MiniMaxH3LongVideoDirector:
    """长视频导演节点：动态分镜头，循环生成，自动拼接"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "MiniMax-H3 Ref2VA UNET模型"}),
                "clip": ("CLIP", {"tooltip": "Qwen3-VL文本编码器"}),
                "vae": ("VAE", {"tooltip": "MiniMax-H3视频VAE"}),
                "audio_vae": ("VAE", {"tooltip": "MiniMax-H3音频VAE"}),
                "sampler": ("SAMPLER", {"tooltip": "采样器（推荐MiniMax-H3 Turbo Sampler）"}),
                "sigmas": ("SIGMAS", {"tooltip": "Sigmas（BasicScheduler输出）"}),
                "reference_image": ("IMAGE", {"tooltip": "参考图，全部分镜共享"}),
                "global_prompt": ("STRING", {
                    "multiline": True,
                    "default": "青春活力的少女写真，纯乐器配乐，无人声，光影柔和",
                    "tooltip": "通用提示词，应用于所有分镜头"
                }),
                "shots_data": ("STRING", {
                    "multiline": False,
                    "default": "",
                    "hidden": True,
                    "tooltip": "分镜头数据JSON（由前端UI自动管理，无需手动编辑）"
                }),
            },
            "optional": {
                "lora_name": (["None"] + __import__("folder_paths").get_filename_list("loras"), {
                    "tooltip": "Larry Turbo LoRA（可选）"
                }),
                "lora_strength": ("FLOAT", {
                    "default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01,
                    "tooltip": "LoRA强度"
                }),
                "context_length": (["22", "5", "39", "56"], {
                    "default": "22",
                    "tooltip": "Motion Context帧数（上一段传递给下一段的帧数）"
                }),
                "audio_context_length": ("INT", {
                    "default": 24, "min": 0, "max": 240,
                    "tooltip": "音频Context帧数（0=跟随视频）"
                }),
                "seed": ("INT", {
                    "default": 42, "min": 0, "max": 0xffffffffffffffff,
                    "tooltip": "基础随机种子（每段自动偏移）"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "FLOAT", "INT", "STRING")
    RETURN_NAMES = ("images", "audio", "fps", "shot_count", "shots_info")
    FUNCTION = "generate"
    CATEGORY = "MiniMax H3/LongVideo"
    DESCRIPTION = (
        "长视频导演节点：动态管理分镜头，循环生成多段视频，"
        "自动latent传递实现画面延续，自动拼接画面和音频。"
        "配合前端UI可点击添加/删除分镜头。"
    )

    @torch.inference_mode()
    def generate(self, model, clip, vae, audio_vae, sampler, sigmas,
                 reference_image, global_prompt, shots_data,
                 lora_name="None", lora_strength=1.0,
                 context_length="22", audio_context_length=24, seed=42):

        # 1. 解析分镜头数据
        shots = parse_shots_data(shots_data)
        shot_count = len(shots)
        _LOG.info(f"[LongVideoDirector] 开始生成 {shot_count} 个分镜头")

        # 2. 应用LoRA（如果指定）
        working_model = model
        if lora_name != "None" and lora_name:
            try:
                result = call_node("MiniMaxH3TurboLoRA",
                                   model=model, lora_name=lora_name,
                                   strength=lora_strength, low_vram=False)
                working_model = result[0]
                _LOG.info(f"[LongVideoDirector] 已应用LoRA: {lora_name}")
            except Exception as e:
                _LOG.warning(f"[LongVideoDirector] LoRA应用失败，使用原始模型: {e}")

        # 3. 缩放参考图到0.3MP（H3稳定档位），保持宽高比，尺寸为16的倍数
        ref_h, ref_w = reference_image.shape[1], reference_image.shape[2]
        target_pixels = 300000  # 0.3MP
        scale = (target_pixels / (ref_w * ref_h)) ** 0.5
        new_w = int(round(ref_w * scale / 16) * 16)
        new_h = int(round(ref_h * scale / 16) * 16)
        new_w = max(16, new_w)
        new_h = max(16, new_h)

        if new_w != ref_w or new_h != ref_h:
            reference_image = resize_image(reference_image, new_w, new_h)
            _LOG.info(f"[LongVideoDirector] 参考图已缩放: {ref_w}x{ref_h} -> {new_w}x{new_h}")
        else:
            _LOG.info(f"[LongVideoDirector] 参考图尺寸: {ref_w}x{ref_h} (无需缩放)")

        ref_h, ref_w = new_h, new_w

        # 4. 循环生成每个分镜头
        all_images = []
        all_audio = []
        all_audio_targets = []  # 每段音频对应的目标长度（samples），用于pad对齐
        prev_latent = None
        shots_info = []

        pbar = comfy.utils.ProgressBar(shot_count)

        # 预创建无状态节点实例，循环中复用（性能优化：避免重复初始化）
        import nodes as _nodes
        _noise_cls = _nodes.NODE_CLASS_MAPPINGS["RandomNoise"]
        _guider_cls = _nodes.NODE_CLASS_MAPPINGS["BasicGuider"]
        _noise_inst = _noise_cls()
        _guider_inst = _guider_cls()
        _noise_func = getattr(_noise_inst, _noise_cls.FUNCTION)
        _guider_func = getattr(_guider_inst, _guider_cls.FUNCTION)

        for idx, shot in enumerate(shots):
            comfy.model_management.throw_exception_if_processing_interrupted()

            shot_prompt = shot.get("prompt", "")
            duration = float(shot.get("duration", 3))
            shot_seed = int(shot.get("seed", seed + idx * 1000))
            shot_id = shot.get("id", f"shot_{idx+1}")

            # 使用六段式提示词格式（参考Multishot验证方案）
            full_prompt = build_prompt(global_prompt, shot_prompt, idx)
            frame_count = seconds_to_frames(duration)

            _LOG.info(f"[LongVideoDirector] 分镜 {idx+1}/{shot_count}: {shot_id}, "
                      f"{duration}s/{frame_count}f, seed={shot_seed}")

            # 4.1 生成conditioning和latent
            try:
                cond_result = call_node(
                    "MiniMaxH3ReferenceToVideo",
                    clip=clip,
                    vae=vae,
                    audio_vae=audio_vae,
                    prompt=full_prompt,
                    ref_images={"0": reference_image},
                    width=ref_w,
                    height=ref_h,
                    length=frame_count,
                    ref_image_size="match",
                )
                positive = cond_result[0]
                latent = cond_result[1]
            except Exception as e:
                _LOG.error(f"[LongVideoDirector] 分镜{idx+1} conditioning生成失败: {e}")
                raise

            # 4.2 应用Motion Context（第2段及以后）
            trim_frames = 0
            if idx > 0 and prev_latent is not None:
                try:
                    mc_result = call_node(
                        "MiniMaxH3MotionContext",
                        conditioning=positive,
                        vae=vae,
                        latent=latent,
                        context_length=context_length,
                        audio_context_length=audio_context_length,
                        context_latent=prev_latent,
                    )
                    positive = mc_result[0]
                    trim_frames = int(mc_result[1])
                    _LOG.info(f"[LongVideoDirector] 分镜{idx+1} Motion Context已应用, trim={trim_frames}")
                except Exception as e:
                    _LOG.warning(f"[LongVideoDirector] 分镜{idx+1} Motion Context失败: {e}")

            # 4.3 采样
            try:
                # 使用预创建的节点实例（性能优化：避免重复初始化）
                noise_result = _noise_func(noise_seed=shot_seed)
                noise = noise_result[0]

                guider_result = _guider_func(model=working_model, conditioning=positive)
                guider = guider_result[0]

                # 采样
                sample_result = call_node(
                    "SamplerCustomAdvanced",
                    noise=noise,
                    guider=guider,
                    sampler=sampler,
                    sigmas=sigmas,
                    latent_image=latent,
                )
                sampled_latent = sample_result[0]
            except Exception as e:
                _LOG.error(f"[LongVideoDirector] 分镜{idx+1} 采样失败: {e}")
                raise

            # 保存latent用于下一段
            prev_latent = sampled_latent

            # 4.4 解码视频
            try:
                decode_result = call_node("VAEDecode", samples=sampled_latent, vae=vae)
                images = decode_result[0]
            except Exception as e:
                _LOG.error(f"[LongVideoDirector] 分镜{idx+1} 视频解码失败: {e}")
                raise

            # 4.5 解码音频
            audio = None
            try:
                audio_decode_result = call_node(
                    "VAEDecodeAudio",
                    samples=sampled_latent,
                    vae=audio_vae,
                )
                audio = audio_decode_result[0]
            except Exception as e:
                _LOG.warning(f"[LongVideoDirector] 分镜{idx+1} 音频解码失败: {e}")

            # 4.6 裁剪Motion Context的头部帧
            if trim_frames > 0:
                try:
                    trim_result = call_node(
                        "MiniMaxH3MotionContextTrim",
                        images=images,
                        trim_frames=trim_frames,
                        audio=audio,
                        fps=float(FPS),
                        match_tail=True,
                    )
                    images = trim_result[0]
                    audio = trim_result[1]
                    _LOG.info(f"[LongVideoDirector] 分镜{idx+1} 已裁剪{trim_frames}帧, "
                              f"剩余{images.shape[0]}帧")
                except Exception as e:
                    _LOG.warning(f"[LongVideoDirector] 分镜{idx+1} 裁剪失败: {e}")

            all_images.append(images)
            if audio is not None:
                all_audio.append(audio)
                # 记录该段视频对应的音频目标长度（samples），用于pad对齐
                # 音频采样率32000Hz，帧率24fps
                audio_target_len = int(images.shape[0] / FPS * AUDIO_SAMPLE_RATE)
                all_audio_targets.append(audio_target_len)

            shots_info.append({
                "id": shot_id,
                "index": idx + 1,
                "duration": duration,
                "frames": int(images.shape[0]),
                "seed": shot_seed,
                "trim_frames": trim_frames,
            })

            pbar.update_absolute(idx + 1, shot_count)

            # 释放中间变量并清空CUDA缓存
            # 8GB显存环境下必须清理，否则显存积累导致模型offloading反而更慢
            del latent, sampled_latent, positive
            comfy.model_management.soft_empty_cache()

        # 5. 拼接所有视频帧（使用Overlap cross-fade避免接缝明暗突变，社区成熟方案）
        crossfade_frames = 5  # 5帧约0.2秒，人眼几乎不可感知但能平滑光影过渡
        if len(all_images) > 1:
            final_images = all_images[0].clone()
            for i in range(1, len(all_images)):
                next_img = all_images[i]
                cf = min(crossfade_frames, final_images.shape[0], next_img.shape[0])
                if cf >= 2:
                    # 线性交叉淡入淡出
                    fade_out = torch.linspace(1.0, 0.0, cf, device=final_images.device).view(-1, 1, 1, 1)
                    fade_in = torch.linspace(0.0, 1.0, cf, device=final_images.device).view(-1, 1, 1, 1)
                    tail = final_images[-cf:] * fade_out
                    head = next_img[:cf] * fade_in
                    crossfaded = tail + head
                    final_images = torch.cat([final_images[:-cf], crossfaded, next_img[cf:]], dim=0)
                else:
                    final_images = torch.cat([final_images, next_img], dim=0)
        else:
            final_images = all_images[0]
        _LOG.info(f"[LongVideoDirector] 视频拼接完成: {final_images.shape[0]}帧 "
                  f"({final_images.shape[0]/FPS:.1f}s), 交叉淡入淡出{crossfade_frames}帧")

        # 6. 拼接所有音频（传入target_lengths进行pad对齐，解决拼接间隙问题）
        final_audio = concat_audio(all_audio, target_lengths=all_audio_targets) if all_audio else None

        # 7. 生成分镜头信息JSON
        info_json = json.dumps({"shots": shots_info}, ensure_ascii=False, indent=2)

        _LOG.info(f"[LongVideoDirector] 全部完成: {shot_count}个分镜, "
                  f"{final_images.shape[0]}帧, 音频={'有' if final_audio else '无'}")

        return (final_images, final_audio, float(FPS), shot_count, info_json)


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3LongVideoDirector": MiniMaxH3LongVideoDirector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3LongVideoDirector": "MiniMax-H3 长视频导演",
}
