# 示例产出详细说明

本文档记录项目示例产出的详细信息，包括参考图生成参数、提示词、视频工作流配置等，供社区用户参考复现。

---

## 一、输入参考图

### 基本信息

| 项目 | 内容 |
|------|------|
| 文件 | `assets/examples/reference_input.png` |
| 分辨率 | 720×1280（9:16竖屏） |
| 生成模型 | Z-Image Turbo（ComfyUI 官方文生图模板） |
| 生成耗时 | 约40秒（模型预热后） |

### 模型配置

| 组件 | 模型文件 |
|------|----------|
| 扩散模型 | `z_image_turbo_bf16.safetensors` |
| 文本编码器 | `qwen_3_4b.safetensors` (lumina2) |
| VAE | `ae.safetensors` |

### 生成参数（官方/社区推荐）

| 参数 | 值 | 说明 |
|------|-----|------|
| 采样步数 | 8步 | Z-Image Turbo 官方推荐，增加步数会导致过拟合 |
| CFG | 1.5 | 官方推荐 1.0-2.0，1.5 细节更好 |
| 采样器 | euler | 官方推荐 |
| 调度器 | sgm_uniform | 官方推荐 |
| Shift | 3.0 | 调整噪声调度，后期细化细节 |
| 分辨率 | 720×1280 | 9:16竖屏，720P直接生成效果优于1080P |

### 正向提示词

```
电影感人像写真，18岁亚洲甜妹，青春靓丽，双马尾蝴蝶结发型，精致妆容，
choker叠戴项链，紧身露腰针织衫，高腰百褶短裙，纯白色过膝轻薄丝袜，厚底运动鞋，
摄影棚深灰色纯色背景，伦勃朗光打亮面部，轮廓光勾勒发丝边缘，发丝飞扬，
单腿抬起倚靠，手撩头发，眨眼甜笑，动态姿势，生动自然不死板，
高清细节，皮肤质感真实，8k画质，专业人像摄影
```

### 负向提示词（防过拟合关键）

```
低质量，模糊，变形，畸形，多余手指，缺失手指，坏手，坏脚，
水印，文字，签名，边框，
silhouette, double image, ghosting, overexposed, blown highlights,
chromatic aberration, oversaturated, unnatural skin, plastic skin
```

> **经验总结**：Z-Image Turbo 是蒸馏模型，8步是绝对甜点。高步数(16/24)+高CFG(2.5)会导致过拟合，出现虚假剪影、过曝虚化、色差等问题。720P直接生成效果优于1080P直接生成，需要1080P时建议先生成720P再超分放大。

---

## 二、输出视频

### 基本信息

| 项目 | 内容 |
|------|------|
| 文件 | `assets/examples/demo_output.mp4` |
| 总时长 | 15秒（5段×3秒） |
| 分辨率 | 0.3MP（9:16竖屏） |
| 工作流 | minimax_h3_r2v_longvideo_v1.4.0 |
| 生成耗时 | 约23.6分钟（RTX 5060 8GB） |
| 文件大小 | 约2MB |

### 工作流配置

| 参数 | 值 |
|------|-----|
| 分镜头数量 | 5段 |
| 每段时长 | 3秒 |
| 全局分辨率 | 0.3MP |
| 采样步数 | 5步（Larry Turbo） |
| 采样器 | euler |
| 调度器 | simple |
| LoRA strength | 1.0 |
| CFG | 1.0 |
| context_length | 22帧 |
| audio_context_length | 24帧 |

### 通用提示词（音频控制部分）

```
【音频控制】纯乐器配乐，无人声，无唱歌，无对话，无旁白。
青春甜美的钢琴旋律，轻柔的吉他/尤克里里，轻快明亮的节奏，
温暖治愈的少女写真氛围，旋律清新自然，与画面青春活力的情绪同步。
instrumental only, no vocals, no singing, no human voice, no dialogue,
sweet youthful piano melody, light acoustic guitar, bright cheerful rhythm,
warm healing atmosphere, fresh natural melody, matching youthful vibrant mood,
clear audio quality
```

### 分镜头设计

| 分镜头 | 景别 | 内容 | 镜头运动 |
|--------|------|------|----------|
| 1 | 上半身中景 | 人物动态姿势，展现整体造型 | 微推 |
| 2 | 脸部特写 | 细腻表情，眨眼微笑 | 固定/微晃 |
| 3 | 腿部特写 | 自然交叉动作，展现过膝丝袜 | 环绕 |
| 4 | 腰臀曲线特写 | 侧身姿态 | 固定 |
| 5 | 肩颈胸部特写 | 拉远收尾 | 拉远 |

---

## 三、测试环境

| 项目 | 配置 |
|------|------|
| CPU | Intel Core i5-14490F（10核） |
| 主板 | 技嘉 B760M POWER DDR4 |
| 内存 | 16GB DDR4 2400MHz |
| GPU | NVIDIA GeForce RTX 5060 8GB |
| 存储 | 致钛 Ti600 1TB NVMe SSD |
| 系统 | Windows 11 专业版 64位 |
| ComfyUI | v0.34.0（秋叶整合包） |
| PyTorch | 2.8.0+cu129 |
| Python | 3.12.10 |

---

## 四、已知问题

1. **音频质量衰减**：多段分镜头独立生成音频后拼接，后续段落音质可能略有衰减。该问题计划在后续版本中通过统一音频生成方案解决。
2. **分镜头过渡**：当前为直接拼接，平滑过渡效果正在优化中。
3. **分镜头数量固定**：当前为5段，动态增删分镜头功能正在开发中。
