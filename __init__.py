"""MiniMax-H3 长视频导演节点包
动态分镜头管理，循环生成多段视频，自动latent传递和拼接
"""

import os
import importlib

WEB_DIRECTORY = "./web"

# 动态导入nodes子模块
_NODE_MODULES = ["director", "utils"]
for mod_name in _NODE_MODULES:
    try:
        importlib.import_module(f".nodes.{mod_name}", __name__)
    except Exception as e:
        print(f"[MiniMaxH3-LongVideo] 导入 {mod_name} 失败: {e}")

# 收集节点映射
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

try:
    from .nodes.director import NODE_CLASS_MAPPINGS as _d_mappings
    from .nodes.director import NODE_DISPLAY_NAME_MAPPINGS as _d_display
    NODE_CLASS_MAPPINGS.update(_d_mappings)
    NODE_DISPLAY_NAME_MAPPINGS.update(_d_display)
except Exception as e:
    print(f"[MiniMaxH3-LongVideo] 加载导演节点失败: {e}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

print(f"[MiniMaxH3-LongVideo] 节点包已加载: {list(NODE_CLASS_MAPPINGS.keys())}")
