from __future__ import annotations
import re


def _auto_desc(meta: dict) -> str:
    """Generate a meaningful @desc from available metadata instead of [待补充]."""
    show_name = meta.get("show_name", "")
    code = meta.get("code", "")
    code_lines = meta.get("code_lines", 0)
    ext = meta.get("ext", "")
    input_vars = meta.get("input_vars", {})
    output_vars = meta.get("output_vars", {})

    parts = []

    # 1. Library usage
    libs = []
    if "import pandas" in code or "from pandas" in code:
        libs.append("pandas")
    if "import openpyxl" in code or "from openpyxl" in code:
        libs.append("openpyxl")
    if "import os" in code:
        libs.append("os")
    if "import re" in code and ext == ".py":
        libs.append("re")
    if "import shutil" in code:
        libs.append("shutil")
    if "win32api" in code:
        libs.append("win32api")
    if "document.querySelector" in code or "getElementById" in code:
        libs.append("DOM查询")
    if libs:
        parts.append("依赖: " + ", ".join(libs))

    # 2. I/O hints
    io_hints = []
    if "pd.read_excel" in code:
        io_hints.append("读取Excel")
    if "to_excel" in code:
        io_hints.append("写入Excel")
    if "os.path.exists" in code:
        io_hints.append("检查文件存在")
    if "os.listdir" in code or "os.walk" in code:
        io_hints.append("遍历目录")
    if ".save(" in code and "openpyxl" in code:
        io_hints.append("保存Excel备份")
    if io_hints:
        parts.append(" | ".join(io_hints))

    # 3. Structural patterns
    if code_lines <= 3:
        parts.append("单行工具脚本")
    elif code_lines <= 8:
        parts.append("简短处理")
    elif "def " in code:
        func_names = re.findall(r"def (\w+)", code)
        if func_names:
            parts.append("函数: " + ", ".join(func_names[:3]))

    # 4. Category hints from JS code
    if ext == ".js":
        if ".click()" in code and len(code.strip().splitlines()) <= 2:
            parts.append("导航点击")
        elif "textContent" in code or "innerText" in code:
            parts.append("DOM文本提取")
        elif "return true" in code or "return false" in code:
            parts.append("状态检测")
        elif "for (" in code or "for(" in code and "querySelectorAll" in code:
            parts.append("列表遍历匹配")

    # 5. Special purpose detection
    if "备份" in show_name or "backup" in show_name.lower():
        parts.append("备份操作")
    if "删除" in show_name:
        parts.append("文件删除/清理")
    if "上传" in show_name or "upload" in show_name.lower():
        parts.append("上传处理")
    if "判断" in show_name or "check" in show_name.lower():
        parts.append("条件判断")
    if "提取" in show_name:
        parts.append("数据提取")

    # Build final
    if not parts:
        # fallback: use show_name + code_lines
        desc = f"{'Python' if ext == '.py' else 'JS'}脚本"
        if input_vars:
            desc += f"，入参: {', '.join(list(input_vars.keys())[:3])}"
        if output_vars:
            desc += f"，出参: {', '.join(list(output_vars.keys())[:3])}"
        return desc

    return "。".join(parts)


def node_header_python(meta: dict, seq: int) -> str:
    input_str = ", ".join(f"{k} ← {v}" for k, v in meta["input_vars"].items()) or "(无)"
    output_str = ", ".join(f"{k} → {v}" for k, v in meta["output_vars"].items()) or "(无)"
    block_tag = f" [BLOCK: {meta['parent_block']}]" if meta.get("parent_block") else ""
    desc = _auto_desc(meta)
    return f'''"""
@node: N{seq} — {meta["show_name"]}{block_tag}
@id: {meta["node_id"]}
@flow: {meta["flow_path"]}
@input:  {input_str}
@output: {output_str}
@lines: {meta["code_lines"]}
@hash: {meta["code_hash"][:12]}
@desc:   {desc}
"""
'''


def node_header_js(meta: dict, seq: int) -> str:
    input_str = ", ".join(f"{k} ← {v}" for k, v in meta["input_vars"].items()) or "(无)"
    output_str = ", ".join(f"{k} → {v}" for k, v in meta["output_vars"].items()) or "(无)"
    block_tag = f" [BLOCK: {meta['parent_block']}]" if meta.get("parent_block") else ""
    desc = _auto_desc(meta)
    return f'''/**
 * @node: N{seq} — {meta["show_name"]}{block_tag}
 * @id: {meta["node_id"]}
 * @flow: {meta["flow_path"]}
 * @input:  {input_str}
 * @output: {output_str}
 * @lines: {meta["code_lines"]}
 * @hash: {meta["code_hash"][:12]}
 * @desc:   {desc}
 */

'''
