# ComfyUI MiniMax-H3 长视频导演台

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-0.34.3+-green.svg)](https://github.com/comfyanonymous/ComfyUI)

ComfyUI自定义节点包，实现MiniMax-H3参考生视频的**真正动态分镜头长视频生成**。一个导演节点替代50+节点的复杂工作流，支持可视化分镜头增删、音画自动衔接、Larry Turbo加速。

## 核心特性

- **真正动态分镜头管理**：可视化UI，点击添加/删除分镜头，支持1-N段动态增删，最少保留1段
- **五段式人像写真模板**：内置头→肩颈胸→腰臀→腿→上半身ending pose的专业镜头调度模板
- **画面自动延续**：基于H3 Motion Context，上一段latent自动传递给下一段，保持人物一致性
- **音画双交叉淡入淡出**：画面5帧+音频100ms等功率交叉淡入淡出，衔接自然无突变
- **纯乐器配乐控制**：六段式提示词结构，明确指定纯乐器配乐，避免人声歌唱
- **Larry Turbo加速集成**：支持MiniMaxH3TurboLoRA自定义节点，4-8步快速采样
- **即装即用**：git clone到custom_nodes即可使用，无需额外配置

## 安装方法

### 方法1：git clone（推荐）

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/IronManVincent/comfyui-minimax-h3-r2v-longvideo.git
```

重启ComfyUI，在节点列表中搜索 `MiniMaxH3LongVideoDirector` 即可找到导演节点。

### 方法2：ComfyUI Manager

1. 打开ComfyUI Manager
2. 搜索 `MiniMax-H3 LongVideo`
3. 点击安装
4. 重启ComfyUI

## 依赖要求

### 必需节点包

| 节点包 | 用途 |
|--------|------|
| [ComfyUI-H3-Motion-Context](https://github.com/NikoDemon80/ComfyUI-H3-Motion-Context) | 画面延续（latent上下文传递） |
| [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | 视频输出合并 |

### 推荐节点包（加速用）

| 节点包 | 用途 |
|--------|------|
| [ComfyUI-MiniMax-H3-Turbo](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo) | Larry Turbo 4-8步加速 |

### 必需模型文件

| 模型 | 文件名 | 放置目录 |
|------|--------|---------|
| UNET（主模型） | `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | `models/diffusion_models/` |
| CLIP（文本编码器） | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `models/text_encoders/` |
| 视频VAE | `minimax_h3_video_vae_fp16.safetensors` | `models/vae/` |
| 音频VAE | `minimax_h3_audio_vae_fp32.safetensors` | `models/vae/` |
| Larry Turbo LoRA（推荐） | `minimax_h3_turbo_v4_step600_ema.safetensors` | `models/loras/` |

> **注意**：CLIPLoader节点的 `type` 参数必须设置为 `minimax`。

## 快速开始

1. 打开ComfyUI，加载 `workflows/minimax_h3_r2v_longvideo_v2.0.0.json`
2. 在LoadImage节点设置参考图
3. 找到 `MiniMaxH3LongVideoDirector` 节点，默认1个分镜头
4. 点击 `➕ 添加分镜头` 添加更多分镜头，或点击 `📋 加载五段模板` 一键加载人像写真模板
5. 点击 `Queue Prompt` 生成视频

## 节点参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| model | MODEL | - | MiniMax-H3 Ref2VA UNET（必需） |
| clip | CLIP | - | Qwen3-VL文本编码器，type=minimax（必需） |
| vae | VAE | - | 视频VAE（必需） |
| audio_vae | VAE | - | 音频VAE（必需） |
| reference_image | IMAGE | - | 参考图，全部分镜共享（必需） |
| sampler | SAMPLER | - | 采样器（推荐MiniMaxH3TurboSampler） |
| sigmas | SIGMAS | - | BasicScheduler输出（推荐5步，simple） |
| global_prompt | STRING | 空 | 通用提示词，应用于所有分镜头 |
| context_length | COMBO | 5 | Motion Context帧数：5/22/39/56 |
| audio_context_length | INT | 24 | 音频Context帧数 |
| seed | INT | 42 | 基础随机种子 |

## 五段式人像写真模板

点击 `📋 加载五段模板` 一键加载专业镜头调度：

| 分镜头 | 景别 | 取景范围 |
|--------|------|---------|
| 第1段 | 极端大特写 | 面部至锁骨 |
| 第2段 | 极端特写 | 肩颈胸部 |
| 第3段 | 特写 | 腰臀部 |
| 第4段 | 特写 | 腿部 |
| 第5段 | 近景 | 上半身至腰部 |

## 提示词编写规范（六段式中文结构）

每个分镜头提示词包含六个部分：

1. **主体定义**：定义参考图中的人物、场景、服饰
2. **概述**：一句话总结任务类型和目标视频
3. **保留分析**：描述参考内容如何保留
4. **详细描述**：按镜头顺序描述画面、动作、光影、运镜
5. **整体音景**：描述环境音和物理声音
6. **非剧情音乐**：描述背景音乐，**必须明确写"纯乐器，无人声，无歌唱"**

## Larry Turbo加速配置

1. 使用 `MiniMaxH3TurboLoRA` 自定义节点（禁止标准LoraLoader）
2. 使用v4版本LoRA：`minimax_h3_turbo_v4_step600_ema.safetensors`
3. 参数：strength=1.0，low_vram=false（bypass模式，最锐利）
4. 采样器：`MiniMaxH3TurboSampler`，调度器：simple，5步

## 性能参考（RTX 5060 8G）

| 配置 | 2段×3秒 | 5段×3秒 |
|------|---------|---------|
| 5步采样，bypass模式 | ~13分钟 | ~25分钟 |
| 8步采样，bypass模式 | ~25分钟 | ~45分钟 |

## 常见问题

**Q: 为什么音频有人声歌唱？**
A: 提示词中必须明确写"纯乐器，无人声，无歌唱"。

**Q: 为什么分镜头衔接处有明暗突变？**
A: 本节点已内置5帧画面交叉淡入淡出。检查各分镜头光影描述是否一致。

**Q: 导演节点的分镜头编辑界面看不到？**
A: 将导演节点拉大（宽度>480px，高度>780px）。

## 版本历史

见 [CHANGELOG.md](CHANGELOG.md)

## 许可证

MIT License

## 致谢

- [Larryvrh](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo) - MiniMax-H3 Turbo加速
- [NikoDemon80](https://github.com/NikoDemon80/ComfyUI-H3-Motion-Context) - H3 Motion Context
- [Kosinkadink](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) - VideoHelperSuite
