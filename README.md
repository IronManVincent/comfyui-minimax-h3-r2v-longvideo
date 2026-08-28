# ComfyUI MiniMax-H3 R2V Long Video Workflow

基于 ComfyUI 的 MiniMax-H3 参考生视频（Reference-to-Video）长视频工作流。通过多段分镜头拼接突破单段时长限制，集成 Larry Turbo 加速，在 RTX 5060 8GB 入门级显卡上可稳定生成 15 秒+ 带音频的长视频。

---

## 速度对比

以下数据为相同测试条件下的参考值，实际速度因机器配置、分辨率、分镜头数量、提示词复杂度而异。

| 方案 | 15秒视频耗时 | 采样步数 | 说明 |
|------|-------------|----------|------|
| 社区导演台（默认配置） | ~50-60 分钟 | 25 步 | res_multistep 采样器，无加速 |
| 本工作流 v0.9 | ~18-22 分钟 | 6 步 | Larry Turbo LoRA + euler 采样器 |

**提速约 2.5-3 倍。**

### 测试环境

| 项目 | 配置 |
|------|------|
| CPU | Intel Core i5-14490F（10核） |
| 主板 | 技嘉 B760M POWER DDR4 |
| 内存 | 16GB DDR4 2400MHz（阿斯加特 8GB×2） |
| GPU | NVIDIA GeForce RTX 5060 8GB |
| 存储 | 致钛 Ti600 1TB NVMe SSD（ComfyUI 安装盘） |
| 系统 | Windows 11 专业版 64位 |
| ComfyUI | v0.34.0（秋叶整合包） |
| PyTorch | 2.8.0+cu129 |
| Python | 3.12.10 |
| 测试参数 | 0.3MP 分辨率，5 段分镜头，每段 3 秒，共 15 秒 |

> 8GB 显存是入门级配置，本工作流在该显存下可稳定运行 0.3MP 分辨率；更高配置的机器（如 RTX 4090/5090、24GB+ 显存）速度更快，可跑更高分辨率。

---

## 功能特点

- **多段分镜头**：5 段独立分镜头，每段可单独设置提示词和时长（1-10秒）
- **通用提示词**：人物/场景/音频约束统一编写，自动拼接到每段分镜头提示词前
- **Larry Turbo 加速**：v4-600 LoRA + 6 步 euler 采样，相比官方 25 步配置提速约 2.5-3 倍
- **自动拼接**：画面（ImageBatch）和音频（AudioConcatenate）自动拼接成完整长视频
- **参考图锁定**：所有分镜头共享同一参考图，保持人物身份和服饰一致性
- **全局分辨率控制**：统一调整所有分镜头的输出分辨率
- **灵活时长**：每段分镜头可独立调整时长，帧数自动适配 MiniMax-H3 的 17k+5 网格

---

## 版本更新日志

### v0.9（当前稳定版）

**发布状态**：已验证可正常运行

**能力提升**：
- 从单段视频升级为 5 段分镜头拼接，支持最长约 50 秒（每段10秒）
- 引入通用提示词节点，人物/场景/音频约束统一管理
- 集成 Larry Turbo LoRA v4-600 加速，6 步采样
- 每段分镜头独立时长控制（秒为单位，自动换算帧数）
- 全局分辨率选择器，统一控制画质
- 画面和音频自动拼接，无需手动处理

**已知缺陷**：
- 音频风格不连贯：每段分镜头独立生成音频，拼接后可能出现风格跳变，无法做到跨段音频一致性
- 人物细节轻微衰减：多段生成后，后续分镜头的人物面部细节可能比第一段略糊
- 镜头硬切：分镜头之间为直接拼接，无过渡帧，切换可能生硬
- 分镜头数量固定：当前为 5 段，增减需要手动复制/删除一组节点（提示词+时长+生成子图+拼接连接）
- 无动态分镜头管理：不支持点击增删分镜头（v1.0 导演台版本将支持）

**适用场景**：
- 人物参考图驱动的多镜头短视频
- 对音频连贯性要求不高的内容（如纯环境音、背景音乐可后期替换）
- 8GB 显存入门级显卡用户

---

## 依赖安装

### 1. ComfyUI 版本要求

需要 **ComfyUI v0.30.0 及以上**（含官方 MiniMax-H3 节点支持，PR #15224、#15228）。

推荐使用秋叶整合包，或从官方仓库更新到最新版。

### 2. 自定义节点（必装 3 个插件）

| 插件 | 用途 | 安装地址 |
|------|------|----------|
| ComfyUI-MiniMax-H3-Turbo | Larry Turbo 加速节点（Turbo LoRA + Turbo Sampler） | `https://github.com/larryvrh/ComfyUI-MiniMax-H3-Turbo.git` |
| ComfyUI-Custom-Scripts | StringFunction 字符串拼接节点（pythongosssss） | `https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git` |
| ComfyUI-VideoHelperSuite | 视频拼接节点（VHS：ImageBatch、AudioConcatenate） | `https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git` |

**安装方法**：
- 方法一：打开 ComfyUI Manager → Install Custom Nodes → 搜索插件名安装
- 方法二：手动 clone 到 `ComfyUI/custom_nodes/` 目录，重启 ComfyUI

安装后重启 ComfyUI，确认节点列表中出现以下节点：
- `MiniMaxH3TurboLoRA`
- `MiniMaxH3TurboSampler`
- `StringFunction|pysssss`
- `ImageBatch`（VHS）
- `AudioConcatenate`（VHS）

### 3. 模型文件（共 5 个）

将以下模型放入对应目录：

| 用途 | 文件名 | 存放目录 |
|------|--------|----------|
| UNET（r2v 参考生视频专用） | `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | `ComfyUI/models/diffusion_models/` |
| Larry Turbo LoRA | `minimax_h3_turbo_v4_step600_ema.safetensors` | `ComfyUI/models/loras/` |
| CLIP 文本编码器 | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `ComfyUI/models/text_encoders/` |
| 视频 VAE | `minimax_h3_video_vae_fp16.safetensors` | `ComfyUI/models/vae/` |
| 音频 VAE | `minimax_h3_audio_vae_fp32.safetensors` | `ComfyUI/models/vae/` |

**模型下载地址**：
- 官方模型（UNET/CLIP/Video VAE/Audio VAE）：[Comfy-Org/MiniMax-H3 (Hugging Face)](https://huggingface.co/Comfy-Org/MiniMax-H3)
- Larry Turbo LoRA：[MiniMax-H3-Turbo-Lora (Hugging Face)](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora)

> 注意：r2v 模式必须使用 `ref2va` 版本的 UNET，不能用 `fl2va` 版本。Turbo LoRA 推荐 v4-600 版本，支持 4-8 步采样。

---

## 快速开始（傻瓜式步骤）

### 第一步：确认环境

1. 确认 ComfyUI 版本 ≥ v0.30.0
2. 确认已安装上述 3 个自定义节点插件
3. 确认 5 个模型文件已放入对应目录
4. 启动 ComfyUI，无报错

### 第二步：加载工作流

1. 打开 ComfyUI 网页界面
2. 将 `workflows/minimax_h3_r2v_长视频_5段分镜头_larry加速_v0.9.json` 拖入画布
3. 工作流自动加载，所有节点显示正常（无红色缺失节点）

### 第三步：加载参考图

1. 找到 **LoadImage** 节点（画布左侧）
2. 点击上传按钮，选择一张人物参考图
3. 参考图建议：清晰的单人或多人正面/半身照，分辨率不限（工作流会自动缩放到 0.6MP 编码）

### 第四步：编写提示词

1. **通用提示词**节点（蓝色大文本框）：已预填模板，按需修改人物描述、场景、音频约束
   - 必须包含：人物参考声明（如"以下画面人物参考参考图"）
   - 建议包含：场景描述、光影风格、音频约束（如"纯环境音，无人声旁白"）
2. **分镜头1-5提示词**节点：分别编写每段的景别、动作、剧情
   - 每段提示词会自动与通用提示词拼接
   - 建议格式：景别 + 角度 + 人物动作 + 表情 + 环境细节

### 第五步：调整参数

1. **每段时长**：5 个时长节点（PrimitiveFloat），默认 3 秒，可独立调整（1-10秒）
2. **全局分辨率**：ResolutionSelector 节点，默认 0.3MP（8GB显存推荐），可选 0.2/0.4/0.5MP
3. **随机种子**：每个分镜头有独立 seed，默认 randomize，可固定复现

### 第六步：生成

1. 点击 **Queue Prompt**
2. 等待生成（5段×3秒约18-22分钟，RTX 5060 8GB）
3. 生成完成后，视频保存在 `ComfyUI/output/` 目录

---

## 工作流结构

```
参考图(LoadImage) → 预缩小(0.6MP) ──────────────────────┐
                                                         │
通用提示词 ──┬── 字符串拼接 ──→ 分镜头1(提示词+时长) ──→ 生成视频段1 ─┐
             ├── 字符串拼接 ──→ 分镜头2(提示词+时长) ──→ 生成视频段2 ─┤
             ├── 字符串拼接 ──→ 分镜头3(提示词+时长) ──→ 生成视频段3 ─┼→ ImageBatch拼接画面
             ├── 字符串拼接 ──→ 分镜头4(提示词+时长) ──→ 生成视频段4 ─┤  +
             └── 字符串拼接 ──→ 分镜头5(提示词+时长) ──→ 生成视频段5 ─┘  AudioConcatenate拼接音频
                                                                          ↓
UNET → Larry Turbo LoRA → 共享给所有分镜头采样                    CreateVideo → SaveVideo
```

每个分镜头的生成子图包含：
- MiniMaxH3ReferenceToVideo（官方参考生视频 conditioning）
- MiniMaxH3TurboSampler（Larry 加速采样器）
- BasicScheduler（simple 调度器，6步）
- KSamplerSelect（euler 采样器）
- VAE 解码（画面+音频分离解码）

---

## 关键参数说明

| 参数 | 默认值 | 合理范围 | 说明 |
|------|--------|----------|------|
| 全局分辨率 | 0.3MP (736×416) | 0.2-0.5MP | 8GB显存推荐0.3MP；12GB+可尝试0.4MP |
| 采样步数 | 6 | 4-8 | Larry Turbo推荐范围；4步最快但大动态可能拖影；6-8步质量更好；超过8步会过锐化 |
| 采样器 | euler | euler | 新版ComfyUI中等同于Turbo Sampler；不建议换其他采样器 |
| 调度器 | simple | simple | Larry推荐，不建议修改 |
| LoRA strength | 1.0 | 0.8-1.2 | 固定1.0为Larry调优值；模糊可微调到1.05-1.2，过锐可降到0.8-0.95 |
| 每段时长 | 3秒 | 1-10秒 | 帧数自动适配17k+5网格；单段过长可能OOM |
| CFG | 1.0 | 1.0 | MiniMax-H3官方推荐固定值 |
| 参考图预缩小 | 0.6MP | 0.5-1.0MP | 降低编码显存占用；原图很糊时可提高到0.8MP |

---

## 帧数规则

MiniMax-H3 的视频帧数必须符合 `17×k+5` 网格，工作流自动计算，无需手动调整：

| 时长（秒） | 帧数 | 计算公式 |
|-----------|------|----------|
| 1 | 22 | 17×1+5 |
| 2 | 39 | 17×2+5 |
| 3 | 73 | 17×4+5 |
| 5 | 124 | 17×7+5 |
| 7 | 175 | 17×10+5 |
| 10 | 243 | 17×14+5 |

---

## 常见问题 FAQ

**Q: 爆显存（CUDA OOM）怎么办？**
A: 按以下顺序尝试：
1. 降低全局分辨率到 0.2MP
2. 减少每段时长（如从5秒降到3秒）
3. 开启 Turbo LoRA 节点的 `low_vram` 模式（merge模式，画质略软但显存占用更低）
4. 关闭其他占用显存的程序

**Q: 人物不一致/变脸怎么办？**
A:
1. 确保通用提示词中明确声明人物参考（如"所有画面人物严格参考参考图的外貌、服饰、体型"）
2. 参考图选择清晰的正面照，避免遮挡
3. 分镜头提示词避免描述与参考图矛盾的外貌特征
4. 降低采样步数到4步（减少重绘幅度）

**Q: 音频有人声旁白/说话声怎么办？**
A: 在通用提示词中明确声明："纯环境音效，无人声旁白，无对话，无唱歌，无语音"。工作流默认已包含此约束，如被修改请补回。

**Q: 如何增加/减少分镜头数量？**
A: 当前版本需要手动操作：
1. 复制一整组分镜头节点（提示词+时长+生成子图）
2. 将新分镜头的画面输出连接到 ImageBatch
3. 将新分镜头的音频输出连接到 AudioConcatenate
4. 调整通用提示词的字符串拼接节点数量
5. v1.0 导演台版本将支持点击动态增删分镜头

**Q: 输出视频在哪里？**
A: 保存在 `ComfyUI/output/` 目录，文件名格式为 `ComfyUI_xxxxx_.mp4`。

**Q: 可以用这个工作流做纯风景/动物视频吗？**
A: 可以，参考图换成风景或动物即可，提示词相应调整。但 r2v 模式主要优化人物参考，非人物场景效果可能不如 t2v/i2v。

---

## 已知限制

1. **音频连贯性**：多段音频独立生成，无法跨段保持风格一致。建议后期用音频编辑软件替换背景音乐。
2. **长视频质量衰减**：超过5段后，后续分镜头质量可能明显下降。建议控制在5段以内。
3. **无过渡效果**：分镜头间为硬切，如需淡入淡出等过渡需后期处理。
4. **显存限制**：8GB显存最多稳定运行0.3MP、每段5秒以内。更高分辨率或更长单段需要更大显存。
5. **提示词语言**：推荐中文提示词，CLIP编码器（Qwen3-VL）对中文支持良好。

---

## 后续版本规划

- **v1.0**（开发中）：基于社区导演台插件（AIMixer/ComfyUI_MiniMaxH3_Director），支持点击动态增删分镜头、公共参数区统一管理参考图和通用提示词、自动拼接。仍集成 Larry Turbo 加速。

---

## 致谢

- [Larryvrh/ComfyUI-MiniMax-H3-Turbo](https://github.com/larryvrh/ComfyUI-MiniMax-H3-Turbo) — Turbo 加速节点和 LoRA 权重
- [AIMixer/ComfyUI_MiniMaxH3_Director](https://github.com/AIMixer/ComfyUI_MiniMaxH3_Director) — 导演台插件，v1.0 版本参考
- [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3) — 官方模型权重
- [pythongosssss/ComfyUI-Custom-Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts) — StringFunction 节点
- [Kosinkadink/ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) — VHS 视频拼接节点

---

## License

MIT License — 详见 [LICENSE](LICENSE) 文件。
