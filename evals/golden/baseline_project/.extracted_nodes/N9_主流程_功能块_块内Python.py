"""
@node: N9 — 块内Python [BLOCK: 功能块]
@id: block_node_py
@flow: 主流程.json::功能块
@input:  path ← C:/data
@output: files → list
@lines: 3
@hash: ff3384de3605
@desc:   依赖: os。遍历目录。单行工具脚本
"""

import os
files = os.listdir(path)
print(len(files))
