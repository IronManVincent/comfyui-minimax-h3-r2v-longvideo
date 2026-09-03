/**
 * MiniMax-H3 长视频导演节点 - 前端UI
 * 实现动态分镜头编辑界面：每个分镜头有独立的提示词/时长/种子输入框
 * 内部仍用shots_data JSON存储，编辑界面自动同步
 */
import { app } from "../../../scripts/app.js";

// 注入CSS样式：隐藏shots_data输入框，固定通用提示词高度
const style = document.createElement('style');
style.textContent = `
    /* 隐藏shots_data JSON输入框 */
    .minimax-h3-longvideo .comfy-widget:has(input[value*='"shots"']) {
        display: none !important;
    }
    /* 通用提示词固定高度 */
    .minimax-h3-longvideo textarea.comfy-multiline-input {
        height: 60px !important;
        min-height: 60px !important;
        max-height: 60px !important;
        resize: none !important;
    }
`;
document.head.appendChild(style);

const DEFAULT_SHOT_TEMPLATES = [
    {
        prompt: `主体定义：
<主体 1> 是参考图中的年轻女性，深色长发双马尾配白色蝴蝶结，白色无袖罗纹上衣，黑色项圈项链。

概述：
[参考生成] 目标视频是<主体 1>的青春活力少女写真，纯乐器背景音乐，无人声。

保留分析：
<主体 1>（出现在[镜头 1]）：完全保留 - 面部特征、发型配白色蝴蝶结、白色上衣、黑色项圈均保留。

详细描述：
[镜头 1] <主体 1>面部极端大特写，取景至锁骨。镜头固定稳定，自然呼吸。她自然眨眼，轻柔微笑，眼神明亮，嘴角上扬，手指轻触脸颊，头部微倾。柔光侧光，青春活力感，暖肤色。无全身镜头，无中远景。

整体音景：
安静的室内环境音，轻微的衣物摩擦声。

非剧情音乐：
轻快钢琴与弦乐纯乐器配乐，中等节奏，青春治愈风格，纯乐器，无人声，无歌唱，无歌词，无旁白。`,
        duration: 3, seed: 560001
    },
    {
        prompt: `主体定义：
<主体 1> 是参考图中的年轻女性，深色长发，白色无袖罗纹上衣，黑色项圈项链。

概述：
[参考生成] 目标视频继续<主体 1>的青春活力少女写真，聚焦肩颈胸部细节，纯乐器背景音乐。

保留分析：
<主体 1>（出现在[镜头 2]）：完全保留 - 服饰、项圈、整体造型均保留。

详细描述：
[镜头 2] <主体 1>肩颈胸部曲线极端特写，取景仅至胸部以上，绝对不包含腰部以下。镜头完全固定，无抖动，无运动模糊。肩部自然舒展，颈部线条优美，胸部曲线自然，呼吸起伏轻微，锁骨清晰。柔光侧光，青春活力感。绝对无全身镜头，无中远景，绝对无面部出现，画面中无人脸。

整体音景：
安静的室内环境音，轻微的衣物摩擦声。

非剧情音乐：
轻快钢琴与弦乐纯乐器配乐，中等节奏，青春治愈风格，纯乐器，无人声，无歌唱，无歌词，无旁白。`,
        duration: 3, seed: 560002
    },
    {
        prompt: `主体定义：
<主体 1> 是参考图中的年轻女性，穿着白色无袖罗纹上衣。

概述：
[参考生成] 目标视频继续<主体 1>的青春活力少女写真，聚焦腰臀曲线，纯乐器背景音乐。

保留分析：
<主体 1>（出现在[镜头 3]）：完全保留 - 服饰、整体造型均保留。

详细描述：
[镜头 3] <主体 1>腰臀部曲线特写，取景至胯部，绝对无面部，无胸部以上。镜头完全固定，无抖动，无运动模糊。腰部纤细，臀部曲线优美，姿态自然微转，腰线清晰。柔光侧光，青春活力感。绝对无全身镜头，无中远景，无面部出现。

整体音景：
安静的室内环境音，轻微的衣物摩擦声。

非剧情音乐：
轻快钢琴与弦乐纯乐器配乐，中等节奏，青春治愈风格，纯乐器，无人声，无歌唱，无歌词，无旁白。`,
        duration: 3, seed: 560003
    },
    {
        prompt: `主体定义：
<主体 1> 是参考图中的年轻女性。

概述：
[参考生成] 目标视频继续<主体 1>的青春活力少女写真，聚焦腿部姿态曲线，纯乐器背景音乐。

保留分析：
<主体 1>（出现在[镜头 4]）：完全保留 - 整体造型均保留。

详细描述：
[镜头 4] <主体 1>腿部姿态曲线特写，取景至大腿，绝对无面部，无上身。镜头完全固定，无抖动，无运动模糊。腿部修长，姿态自然交叉，膝盖微曲，小腿线条优美，脚踝纤细。柔光侧光，青春活力感。绝对无全身镜头，无中远景，无面部出现。

整体音景：
安静的室内环境音。

非剧情音乐：
轻快钢琴与弦乐纯乐器配乐，中等节奏，青春治愈风格，纯乐器，无人声，无歌唱，无歌词，无旁白。`,
        duration: 3, seed: 560004
    },
    {
        prompt: `主体定义：
<主体 1> 是参考图中的年轻女性，深色长发，白色无袖罗纹上衣，黑色项圈项链。

概述：
[参考生成] 目标视频以上半身收尾姿势结束<主体 1>的青春活力少女写真，纯乐器背景音乐。

保留分析：
<主体 1>（出现在[镜头 5]）：完全保留 - 面部特征、发型、服饰、项圈均保留。

详细描述：
[镜头 5] <主体 1>上半身收尾姿势近景，取景至腰部，无全身。镜头固定稳定。她双手叉腰，挺胸抬头，自信微笑，眼神坚定，姿态舒展有力。柔光正面光，青春活力感。无全身镜头，无导致面部细节丢失的中远景。

整体音景：
安静的室内环境音，轻微的衣物摩擦声。

非剧情音乐：
轻快钢琴与弦乐纯乐器配乐，中等节奏，青春治愈风格，纯乐器，无人声，无歌唱，无歌词，无旁白。`,
        duration: 3, seed: 560005
    },
];

function genId() {
    return "shot_" + Date.now() + "_" + Math.random().toString(36).substr(2, 5);
}

function defaultShot(index) {
    // 前5个分镜头使用模板提示词，第6个及以上留空让用户自行编写
    if (index < DEFAULT_SHOT_TEMPLATES.length) {
        const template = DEFAULT_SHOT_TEMPLATES[index];
        return {
            id: genId(),
            prompt: template.prompt,
            duration: template.duration,
            seed: template.seed || Math.floor(Math.random() * 1000000),
            enabled: true,
        };
    } else {
        return {
            id: genId(),
            prompt: "",
            duration: 3,
            seed: Math.floor(Math.random() * 1000000),
            enabled: true,
        };
    }
}

function parseShots(text) {
    if (!text || !text.trim()) {
        return [defaultShot(0)];
    }
    try {
        const data = JSON.parse(text);
        const shots = data.shots || [];
        if (shots.length === 0) return [defaultShot(0)];
        return shots;
    } catch (e) {
        console.warn("[MiniMaxH3-LongVideo] JSON解析失败，使用默认", e);
        return [defaultShot(0)];
    }
}

function serializeShots(shots) {
    return JSON.stringify({ shots: shots }, null, 2);
}

// 在节点原型上定义初始化和渲染方法
function initShotEditor(node) {
    console.log("[MiniMaxH3-LongVideo] initShotEditor 被调用");

    if (node._editorInitialized) {
        console.log("[MiniMaxH3-LongVideo] 编辑器已初始化，跳过");
        return;
    }

    // 立即设置标志，防止onNodeCreated和onConfigure重复调用
    node._editorInitialized = true;

    // 给节点DOM元素添加class，用于CSS选择器
    if (node.root && node.root.children) {
        // 延迟添加class，确保DOM已渲染
        setTimeout(() => {
            const nodeEl = document.querySelector(`.litegraph-node[data-node-id="${node.id}"]`);
            if (nodeEl) nodeEl.classList.add('minimax-h3-longvideo');
        }, 100);
    }

    // 找到shots_data widget
    node.shotsWidget = node.widgets.find(w => w.name === "shots_data");
    if (!node.shotsWidget) {
        console.warn("[MiniMaxH3-LongVideo] 找不到shots_data widget, widgets:", node.widgets.map(w => w.name));
        return;
    }

    console.log("[MiniMaxH3-LongVideo] 找到shots_data widget, 当前值长度:", node.shotsWidget.value ? node.shotsWidget.value.length : 0);

    // 如果shots_data为空，设置默认值
    if (!node.shotsWidget.value || !node.shotsWidget.value.trim()) {
        console.log("[MiniMaxH3-LongVideo] shots_data为空，设置默认值");
        node.shotsWidget.value = serializeShots([defaultShot(0)]);
    }

    // 隐藏原始的shots_data输入框
    node.shotsWidget.type = "hidden";
    if (node.shotsWidget.element) {
        node.shotsWidget.element.style.display = 'none';
        const widgetRow = node.shotsWidget.element.closest('.comfy-widget');
        if (widgetRow) widgetRow.style.display = 'none';
    }

    // 给通用提示词widget添加清晰的中文标签
    const globalPromptWidget = node.widgets.find(w => w.name === "global_prompt");
    if (globalPromptWidget) {
        globalPromptWidget.name = "通用提示词（应用于所有分镜头）";
        // customtext类型的widget不显示名称，手动添加标签
        if (globalPromptWidget.element && globalPromptWidget.element.parentElement) {
            const parent = globalPromptWidget.element.parentElement;
            if (!parent.querySelector('.global-prompt-label')) {
                const label = document.createElement("div");
                label.className = "global-prompt-label";
                label.textContent = "通用提示词（应用于所有分镜头）";
                label.style.cssText = "color:#c5d4ee;font-size:12px;font-weight:bold;margin-bottom:4px;";
                parent.insertBefore(label, globalPromptWidget.element);
            }
            // 固定通用提示词的高度，防止节点大小调整时被拉伸
            if (globalPromptWidget.element.tagName === 'TEXTAREA') {
                globalPromptWidget.element.classList.remove('h-full');
                globalPromptWidget.element.style.height = "60px";
                globalPromptWidget.element.style.minHeight = "60px";
                globalPromptWidget.element.style.maxHeight = "60px";
                globalPromptWidget.element.style.resize = "none";
            }
        }
        console.log("[MiniMaxH3-LongVideo] 通用提示词标签和高度已设置");
    }

    // 添加操作按钮（放在编辑器之前，确保默认可见）
    try {
        node.addWidget("button", "➕ 添加分镜头", null, () => {
            const shots = parseShots(node.shotsWidget.value);
            shots.push(defaultShot(shots.length));
            node.shotsWidget.value = serializeShots(shots);
            node.renderShotEditor();
        });

        node.addWidget("button", "➖ 删除最后一段", null, () => {
            const shots = parseShots(node.shotsWidget.value);
            if (shots.length <= 1) {
                alert("至少保留一个分镜头");
                return;
            }
            shots.pop();
            node.shotsWidget.value = serializeShots(shots);
            node.renderShotEditor();
        });

        node.addWidget("button", "🔄 重置为1段", null, () => {
            node.shotsWidget.value = serializeShots([defaultShot(0)]);
            node.renderShotEditor();
        });

        node.addWidget("button", "📋 加载五段模板", null, () => {
            const shots = DEFAULT_SHOT_TEMPLATES.map((_, i) => defaultShot(i));
            node.shotsWidget.value = serializeShots(shots);
            node.renderShotEditor();
        });

        console.log("[MiniMaxH3-LongVideo] 按钮添加成功");
    } catch (e) {
        console.error("[MiniMaxH3-LongVideo] 添加按钮失败:", e);
    }

    // 清理旧的编辑器容器和widget（防止重复初始化）
    if (node.editorContainer && node.editorContainer.parentNode) {
        node.editorContainer.parentNode.removeChild(node.editorContainer);
    }
    const oldEditorWidget = node.widgets.find(w => w.name === "shot_editor");
    if (oldEditorWidget) {
        node.widgets = node.widgets.filter(w => w !== oldEditorWidget);
    }

    // 创建分镜头编辑器容器
    const editorContainer = document.createElement("div");
    editorContainer.className = "minimax-shot-editor";
    editorContainer.style.cssText = "width:100%;padding:6px;background:#1e1e1e;border:1px solid #444;border-radius:4px;max-height:500px;overflow-y:auto;";

    node.editorContainer = editorContainer;

    // 添加DOM widget作为分镜头编辑器
    try {
        node.addDOMWidget("shot_editor", "分镜头编辑器", editorContainer, () => {});
        console.log("[MiniMaxH3-LongVideo] DOM widget添加成功");
    } catch (e) {
        console.error("[MiniMaxH3-LongVideo] addDOMWidget失败:", e);
        return;
    }

    // 定义渲染方法
    node.renderShotEditor = function () {
        // 每次都从shots_data解析最新数据，不使用闭包变量
        const shots = parseShots(node.shotsWidget.value);

        // 总是通过DOM查询找到实际显示的编辑器容器，不依赖可能失效的引用
        let container = null;
        const allEditors = document.querySelectorAll('.minimax-shot-editor');
        for (const ed of allEditors) {
            if (ed.closest('.dom-widget')) {
                container = ed;
                node.editorContainer = ed;
                break;
            }
        }

        if (!container) {
            console.warn("[MiniMaxH3-LongVideo] 找不到编辑器容器");
            return;
        }

        container.innerHTML = "";

        if (shots.length === 0) {
            const empty = document.createElement("div");
            empty.textContent = "暂无分镜头，点击下方按钮添加";
            empty.style.cssText = "color:#888;text-align:center;padding:20px;";
            container.appendChild(empty);
        } else {
            shots.forEach((shot, index) => {
                const shotDiv = document.createElement("div");
                shotDiv.style.cssText = "margin-bottom:10px;padding:8px;background:#2a2a2a;border:1px solid #3a3a3a;border-radius:4px;";

                // 分镜头标题栏
                const header = document.createElement("div");
                header.style.cssText = "display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;";
                const title = document.createElement("span");
                title.textContent = `分镜头 ${index + 1}`;
                title.style.cssText = "color:#c5d4ee;font-weight:bold;font-size:12px;";
                header.appendChild(title);

                // 删除按钮 - 不使用闭包变量，每次点击重新解析
                const delBtn = document.createElement("button");
                delBtn.textContent = "删除";
                delBtn.style.cssText = "background:#5a2a2a;color:#ffaaaa;border:1px solid #7a3a3a;border-radius:3px;padding:2px 8px;font-size:11px;cursor:pointer;";
                delBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const currentShots = parseShots(node.shotsWidget.value);
                    if (currentShots.length <= 1) {
                        alert("至少保留一个分镜头");
                        return;
                    }
                    currentShots.splice(index, 1);
                    node.shotsWidget.value = serializeShots(currentShots);
                    node.renderShotEditor();
                });
                header.appendChild(delBtn);
                shotDiv.appendChild(header);

                // 提示词标签
                const promptLabel = document.createElement("div");
                promptLabel.textContent = "提示词:";
                promptLabel.style.cssText = "color:#999;font-size:11px;margin-bottom:2px;";
                shotDiv.appendChild(promptLabel);

                // 提示词输入框
                const promptInput = document.createElement("textarea");
                promptInput.value = shot.prompt || "";
                promptInput.placeholder = "输入分镜头提示词...";
                promptInput.style.cssText = "width:100%;height:100px;background:#1a1a1a;color:#ddd;border:1px solid #555;border-radius:3px;padding:4px;font-size:11px;resize:vertical;box-sizing:border-box;line-height:1.4;";
                promptInput.addEventListener("input", () => {
                    const currentShots = parseShots(node.shotsWidget.value);
                    if (currentShots[index]) {
                        currentShots[index].prompt = promptInput.value;
                        node.shotsWidget.value = serializeShots(currentShots);
                    }
                });
                shotDiv.appendChild(promptInput);

                // 时长和种子行
                const rowDiv = document.createElement("div");
                rowDiv.style.cssText = "display:flex;gap:8px;margin-top:6px;";

                // 时长
                const durationWrap = document.createElement("div");
                durationWrap.style.cssText = "flex:1;";
                const durLabel = document.createElement("div");
                durLabel.textContent = "时长(秒):";
                durLabel.style.cssText = "color:#999;font-size:11px;margin-bottom:2px;";
                durationWrap.appendChild(durLabel);
                const durationInput = document.createElement("input");
                durationInput.type = "number";
                durationInput.value = shot.duration || 3;
                durationInput.min = 1;
                durationInput.max = 30;
                durationInput.step = 1;
                durationInput.style.cssText = "width:100%;background:#1a1a1a;color:#ddd;border:1px solid #555;border-radius:3px;padding:2px;font-size:11px;box-sizing:border-box;";
                durationInput.addEventListener("input", () => {
                    const currentShots = parseShots(node.shotsWidget.value);
                    if (currentShots[index]) {
                        currentShots[index].duration = parseInt(durationInput.value) || 3;
                        node.shotsWidget.value = serializeShots(currentShots);
                    }
                });
                durationWrap.appendChild(durationInput);
                rowDiv.appendChild(durationWrap);

                // 种子
                const seedWrap = document.createElement("div");
                seedWrap.style.cssText = "flex:1;";
                const seedLabel = document.createElement("div");
                seedLabel.textContent = "种子:";
                seedLabel.style.cssText = "color:#999;font-size:11px;margin-bottom:2px;";
                seedWrap.appendChild(seedLabel);
                const seedInput = document.createElement("input");
                seedInput.type = "number";
                seedInput.value = shot.seed || 0;
                seedInput.min = 0;
                seedInput.max = 999999999;
                seedInput.style.cssText = "width:100%;background:#1a1a1a;color:#ddd;border:1px solid #555;border-radius:3px;padding:2px;font-size:11px;box-sizing:border-box;";
                seedInput.addEventListener("input", () => {
                    const currentShots = parseShots(node.shotsWidget.value);
                    if (currentShots[index]) {
                        currentShots[index].seed = parseInt(seedInput.value) || 0;
                        node.shotsWidget.value = serializeShots(currentShots);
                    }
                });
                seedWrap.appendChild(seedInput);
                rowDiv.appendChild(seedWrap);

                shotDiv.appendChild(rowDiv);
                container.appendChild(shotDiv);
            });
        }

        // 隐藏shots_data：遍历所有widget，找到shots_data并隐藏其DOM行
        for (const w of node.widgets) {
            if (w.name === 'shots_data' && w.element) {
                w.element.style.display = 'none';
                let el = w.element;
                while (el && el.parentElement) {
                    if (el.classList && (el.classList.contains('comfy-widget') || el.classList.contains('widget'))) {
                        el.style.display = 'none';
                        break;
                    }
                    el = el.parentElement;
                }
            }
        }

        // 根据分镜头数量设置固定高度（每个分镜头约250px，最小150，最大500）
        const shotCount = shots.length;
        const editorHeight = Math.max(Math.min(shotCount * 250, 500), 150);

        const domWidget = container.closest('.dom-widget');
        if (domWidget) {
            domWidget.style.height = editorHeight + "px";
            domWidget.style.minHeight = editorHeight + "px";
            domWidget.style.maxHeight = editorHeight + "px";
            domWidget.style.overflow = "visible";
        }

        // 节点总高度：其他widget(320) + 编辑器高度 + 间距(20)
        const totalHeight = Math.min(850, 320 + editorHeight + 20);
        node.setSize([480, totalHeight]);

        // 固定通用提示词高度
        const gpw = node.widgets.find(w => w.name === "通用提示词（应用于所有分镜头）");
        if (gpw && gpw.element) {
            gpw.element.classList.remove('h-full');
            gpw.element.style.height = "60px";
            gpw.element.style.minHeight = "60px";
            gpw.element.style.maxHeight = "60px";
            gpw.element.style.resize = "none";
        }
    };

    console.log("[MiniMaxH3-LongVideo] 编辑器初始化完成");

    // 调整widget顺序：把按钮移到编辑器之前，确保默认可见
    try {
        const buttonNames = ["➕ 添加分镜头", "➖ 删除最后一段", "🔄 重置为1段", "📋 加载五段模板"];
        const buttons = buttonNames.map(name => node.widgets.find(w => w.name === name)).filter(Boolean);
        const editorWidget = node.widgets.find(w => w.name === "shot_editor");

        if (buttons.length > 0 && editorWidget) {
            // 从widgets中移除按钮和编辑器
            const otherWidgets = node.widgets.filter(w => !buttonNames.includes(w.name) && w.name !== "shot_editor");
            // 重新排列：其他widget + 按钮 + 编辑器
            node.widgets = [...otherWidgets, ...buttons, editorWidget];
            console.log("[MiniMaxH3-LongVideo] widget顺序已调整，按钮移到编辑器之前");
        }
    } catch (e) {
        console.error("[MiniMaxH3-LongVideo] 调整widget顺序失败:", e);
    }

    // 设置节点默认大小，确保按钮和编辑区都可见
    node.setSize([480, 780]);

    // 初始渲染
    node.renderShotEditor();
}

app.registerExtension({
    name: "MiniMaxH3.LongVideoDirector",

    init() {
        console.log("[MiniMaxH3-LongVideo] 前端UI初始化");
    },

    beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "MiniMaxH3LongVideoDirector") return;

        console.log("[MiniMaxH3-LongVideo] 注册导演节点UI扩展, nodeData.name:", nodeData.name);

        // 重写onNodeCreated
        const onNodeCreatedOriginal = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            console.log("[MiniMaxH3-LongVideo] onNodeCreated 被调用");
            if (onNodeCreatedOriginal) {
                onNodeCreatedOriginal.apply(this, arguments);
            }
            initShotEditor(this);
        };

        // 重写onConfigure（加载工作流时调用）
        const onConfigureOriginal = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            console.log("[MiniMaxH3-LongVideo] onConfigure 被调用");
            if (onConfigureOriginal) {
                onConfigureOriginal.apply(this, arguments);
            }
            const self = this;
            setTimeout(() => {
                if (!self._editorInitialized) {
                    console.log("[MiniMaxH3-LongVideo] onConfigure中初始化编辑器");
                    initShotEditor(self);
                } else {
                    console.log("[MiniMaxH3-LongVideo] 编辑器已初始化，重新渲染");
                    self.renderShotEditor();
                }
            }, 100);
        };
    },
});

console.log("[MiniMaxH3-LongVideo] 前端UI脚本已加载");
