#!/usr/bin/env python3
"""
IPA Studio RPA Node Extractor
==============================
Extract code-bearing nodes (script_python_execute, browser_inject_js_code)
from IPA Studio JSON flow files into standalone script files with metadata headers.

Usage:
    python extract_nodes.py <project_path> [--force]

Output:
    {project_path}/.extracted_nodes/
        manifest.json          # node index with I/O mappings, hashes, categories
        N1_主流程_xxx.py       # per-node script files
        N2_业务流程_xxx.py
        ...

The script reads project.json to discover flow files, then parses each flow JSON
to locate code nodes, extracting: python_script / js_code, input_variables,
output_variables, and node metadata into structured file headers.

Token savings: Instead of reading multi-MB JSON flow files (~250KB), subsequent
analysis can read just the extracted .py/.js files (~32KB total for 5 nodes).
"""

from __future__ import annotations

import json
import re
import sys
import hashlib
from datetime import date
from pathlib import Path
from typing import Any


# ── Functional Tagging System ────────────────────────────────────────────
# Instead of matching hardcoded node_ids (which are project-specific),
# classify nodes by their functional role using code signature + show_name
# keywords + structural features. This is domain-agnostic and works across
# any IPA Studio project regardless of developer or business domain.

# Tags and their meaning:
#   [BOILERPLATE]  - Infrastructure/scaffolding code shared across projects
#   [SKELETON]     - Minimal node (< 10 code lines), no business logic
#   [SHARED:Nx,Ny] - Code identical to another node within the same project
#   [CROSS:proj]   - Code identical to nodes in other projects (batch mode)
#   [GLUE]         - Parameter conversion / data reshaping between nodes
#   [BUSINESS]     - Contains domain-specific business logic

BOILERPLATE_PATTERNS: list[dict] = [
    {
        "tag": "项目文件夹初始化",
        "keywords": ["初始化项目文件夹路径", "创建工作目录", "项目文件夹"],
        "min_lines": 40,
        "signatures": ["project_name", "keep_days", "today_file_path"],
        "desc": "创建项目目录结构并清理过期文件",
    },
    {
        "tag": "随机CPU延迟",
        "keywords": ["执行python脚本"],
        "max_lines": 20,
        "signatures": ["random.uniform", "time.sleep"],
        "desc": "模拟处理耗时（仅用于测试/演示）",
    },
    {
        "tag": "Tkinter对话框",
        "keywords": ["异常终止提示对话框", "流程结束提示对话框", "流程开始提示对话框", "提示对话框"],
        "signatures": ["tkinter", "Tk"],
        "desc": "Tkinter GUI 弹框提示",
    },
    {
        "tag": "日志类初始化",
        "keywords": ["日志类初始化", "Logger", "日志类-"],
        "signatures": ["log_path", "out_logger"],
        "desc": "日志系统初始化",
    },
    {
        "tag": "Chrome配置管理",
        "keywords": ["Chrome_Preferences", "Chrome进程", "Chrome缓存"],
        "signatures": ["taskkill", "Preferences"],
        "desc": "Chrome 浏览器配置管理",
    },
    {
        "tag": "离线依赖安装",
        "keywords": ["离线安装", "安装第三方库"],
        "signatures": ["pip", ".whl"],
        "desc": "离线 pip 安装依赖库",
    },
]

# Known token-extraction JS pattern (SSCM StorageUtils)
STORAGE_UTILS_SIGNATURE = "StorageUtils"

# Legacy node_id mapping for backward compatibility with old template projects
KNOWN_COMMON_NODE_IDS: dict[str, str] = {
    "script_python_execute0531249916773": "日志类初始化 (Logger init)",
    "script_python_execute5185304017217": "工作目录创建 (Work dir creation)",
    "script_python_execute7484671234258": "日志类-控制中心 (Logger for control center)",
    "script_python_execute9697639560316": "输出日志文件 (Output log file)",
    "script_python_execute0147252387490": "日志类初始化 v2 (Logger init v2)",
    "script_python_execute7612873743676": "工作目录创建 v2 (Work dir creation v2)",
    "script_python_execute2388776339421": "日志类-大音版 (Logger - Dayin variant)",
    "script_python_execute8852352551163": "更新日志 (Changelog updater)",
}

# Map specific pattern tags to broader functional categories
PATTERN_CATEGORY_MAP = {
    "项目文件夹初始化": "BOILERPLATE",
    "随机CPU延迟": "BOILERPLATE",
    "Tkinter对话框": "BOILERPLATE",
    "日志类初始化": "BOILERPLATE",
    "Chrome配置管理": "BOILERPLATE",
    "离线依赖安装": "BOILERPLATE",
}


def classify_boilerplate(show_name: str, code: str, code_lines: int) -> tuple[str, str, list[str]]:
    """Classify a node into functional tags based on show_name + code signatures.
    Returns (category, primary_tag, [all_tags]).
    Domain-agnostic — works across any IPA Studio project.
    """
    tags = []
    for pattern in BOILERPLATE_PATTERNS:
        kw_match = any(kw in show_name for kw in pattern["keywords"])
        sig_match = not pattern.get("signatures") or any(
            sig in code for sig in pattern["signatures"]
        )
        min_ok = "min_lines" not in pattern or code_lines >= pattern["min_lines"]
        max_ok = "max_lines" not in pattern or code_lines <= pattern["max_lines"]
        if kw_match and sig_match and min_ok and max_ok:
            tags.append(pattern["tag"])
            break  # first match wins for primary

    if not tags:
        # Check structural features
        if code_lines <= 5:
            tags.append("SKELETON")
        elif all(kw not in show_name for kw in ["读取", "写入", "处理", "查询", "核查", "报表", "下载", "提取", "发送", "上传", "初始化"]):
            if code_lines < 15:
                tags.append("GLUE")

    primary = tags[0] if tags else "BUSINESS"
    category = PATTERN_CATEGORY_MAP.get(primary, primary)
    return category, primary, tags

# ── JS Category Classification Patterns ───────────────────────────────────

JS_CATEGORY_PATTERNS: dict[str, list[str]] = {
    "navigation": [
        r"querySelector\(.*\)\.click\(\)", r"location\.href", r"window\.open",
        r"\.click\(\)", r"navigate", r"menu.*click",
        r"tab.*close", r"closeTab", r"close.*window",
    ],
    "form_fill": [
        r"\.value\s*=", r"dispatchEvent", r"input.*value",
        r"select.*value", r"setAttribute.*value",
        r"getApplicationValue", r"getFieldValue",
    ],
    "form_read": [
        r"\.value\b(?!\s*=)", r"\.innerText\b(?!\s*=)", r"\.textContent\b(?!\s*=)",
        r"\.selectedIndex", r"\.checked",
    ],
    "state_detect": [
        r"return\s+(true|false)", r"\.loading", r"\.completed",
        r"querySelector.*exist", r"getElementById.*exist",
        r"\.style\.display", r"classList\.contains",
        r"\.style\.visibility", r"\.disabled",
    ],
    "data_extract": [
        r"window\.\w+\s*=",
        r"sessionStorage\.getItem", r"localStorage\.getItem",
        r"storage\.getItem", r"getStorageInstance",
        r"getStorageValue", r"getStorageField", r"StorageUtils\.",
        r"document\.cookie", r"\.innerText", r"\.textContent",
        r"JSON\.parse\(.*getItem", r"JSON\.parse\(.*storage",
        r"(?:var|let|const)\s+\w+\s*=\s*StorageUtils\.",
    ],
    "page_cleanup": [
        r"window\.close", r"removeChild", r"\.remove\(\)",
        r"\.innerHTML\s*=\s*\"\"", r"close.*tab", r"removeEventListener",
        r"closeTab", r"tabClose",
    ],
    "button_click": [
        r"querySelector\(.*\)\.click\(\)",
        r"getElementById\(.*\)\.click\(\)",
        r"getElementsByClassName\(.*\)\.click\(\)",
        r"\.click\(\s*\)",
        r"dispatchEvent.*click",
    ],
}


def classify_js_code(code: str) -> str:
    """Classify a JS code snippet into one of 5 categories based on pattern matching."""
    scores: dict[str, int] = {}
    for category, patterns in JS_CATEGORY_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                score += 1
        scores[category] = score

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "unknown"


# ── helpers ────────────────────────────────────────────────────────────────

def safe_name(text: str, max_len: int = 20) -> str:
    """Sanitize a show_name for use in filenames."""
    text = str(text).strip() or "unnamed"
    # replace Chinese punctuation and spaces
    text = text.replace("：", "_").replace("，", "_").replace("、", "_")
    text = text.replace(" ", "_").replace("\n", "").replace("\r", "")
    text = re.sub(r"[^\w一-鿿\-]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len] if len(text) > max_len else text


def flow_shortname(path: str) -> str:
    """Convert flow file path to a short identifier."""
    name = path.replace("\\", "/").removesuffix(".json")
    name = name.replace("/", "_").replace(".", "_")
    # shorten known patterns
    name = name.replace("cw_通用_", "")
    return name


def code_hash(code: str) -> str:
    """MD5 hash of normalized code for cross-project duplicate detection."""
    normalized = re.sub(r"\s+", " ", code.strip())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def count_code_lines(code: str) -> int:
    """Count non-empty, non-comment-only lines of code."""
    lines = code.strip().splitlines()
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("//"):
            count += 1
    return count


# ── extraction ──────────────────────────────────────────────────────────────

def find_param(properties: list[dict], prop_type: str, param_id: str) -> Any:
    """Find a parameter value in a node's properties list."""
    for prop in properties:
        if prop.get("type") != prop_type:
            continue
        for param in prop.get("params", []):
            if param.get("id") == param_id:
                return param.get("value")
    return None


def extract_node_meta(node: dict, flow_path: str) -> Optional[dict]:
    """Extract metadata and code from a single JSON node. Returns None if not a code node."""
    component_id = node.get("component_id", "")
    node_id = node.get("id", "")
    show_name_raw = node.get("properties", [{}])[0].get("params", [{}])[0].get("value", "")
    show_name = show_name_raw.strip('"') if isinstance(show_name_raw, str) else str(show_name_raw)

    props = node.get("properties", [])

    if component_id == "script_python_execute":
        code = find_param(props, "input_params", "python_script")
        input_vars = find_param(props, "input_params", "python_input_variables") or {}
        output_vars_raw = find_param(props, "output_params", "_script_execute_result") or {}
        output_vars = output_vars_raw if isinstance(output_vars_raw, dict) else {}
        ext = ".py"
        code_field = "python_script"
        js_category = None
    elif component_id == "browser_inject_js_code":
        code = find_param(props, "input_params", "js_code")
        input_vars = find_param(props, "input_params", "js_input_variables") or {}
        output_vars_raw = find_param(props, "output_params", "_script_execute_result") or {}
        output_vars = output_vars_raw if isinstance(output_vars_raw, dict) else {}
        ext = ".js"
        code_field = "js_code"
    else:
        return None

    if not code or not isinstance(code, str) or len(code.strip()) < 10:
        return None  # skip empty/skeleton nodes

    chash = code_hash(code)
    clines = count_code_lines(code)

    # Functional tagging (domain-agnostic, works across any IPA project)
    category, primary_tag, tags = classify_boilerplate(show_name, code, clines)

    # Legacy node_id check (backward compatibility with old template projects)
    is_legacy_common = node_id in KNOWN_COMMON_NODE_IDS
    if is_legacy_common and category == "BUSINESS":
        category = "BOILERPLATE"
        primary_tag = KNOWN_COMMON_NODE_IDS[node_id]
        tags = [KNOWN_COMMON_NODE_IDS[node_id]] + tags

    # JS classification
    js_category = classify_js_code(code) if ext == ".js" else None

    # Detect StorageUtils wrapper pattern
    if ext == ".js" and STORAGE_UTILS_SIGNATURE in code and js_category == "unknown":
        js_category = "data_extract"

    return {
        "node_id": node_id,
        "component_id": component_id,
        "show_name": show_name,
        "code": code,
        "code_field": code_field,
        "input_vars": input_vars,
        "output_vars": output_vars,
        "ext": ext,
        "flow_path": flow_path,
        "code_hash": chash,
        "code_lines": clines,
        "is_common": is_legacy_common,
        "common_desc": KNOWN_COMMON_NODE_IDS.get(node_id, ""),
        "functional_category": category,
        "functional_tag": primary_tag,
        "functional_tags": tags,
        "js_category": js_category,
    }


def node_header_python(meta: dict, seq: int) -> str:
    """Generate the @node docstring header for a .py file."""
    input_str = ", ".join(f"{k} ← {v}" for k, v in meta["input_vars"].items()) or "(无)"
    output_str = ", ".join(f"{k} → {v}" for k, v in meta["output_vars"].items()) or "(无)"
    fcat = meta.get("functional_category", "BUSINESS")
    ftag = meta.get("functional_tag", "BUSINESS")
    tags_str = ", ".join(meta.get("functional_tags", []))
    common_tag = f" [LEGACY_COMMON: {meta['common_desc']}]" if meta.get("is_common") else ""
    block_tag = f" [BLOCK: {meta['parent_block']}]" if meta.get("parent_block") else ""
    return f'''"""
@node: N{seq} — {meta["show_name"]}{common_tag}{block_tag}
@id: {meta["node_id"]}
@flow: {meta["flow_path"]}
@tag: {fcat}:{ftag}{' (' + tags_str + ')' if tags_str else ''}
@input:  {input_str}
@output: {output_str}
@lines: {meta["code_lines"]}
@hash: {meta["code_hash"][:12]}
@desc:   [待补充]
"""
'''


def node_header_js(meta: dict, seq: int) -> str:
    """Generate the @node docstring header for a .js file."""
    input_str = ", ".join(f"{k} ← {v}" for k, v in meta["input_vars"].items()) or "(无)"
    output_str = ", ".join(f"{k} → {v}" for k, v in meta["output_vars"].items()) or "(无)"
    js_cat = meta.get("js_category", "unknown")
    fcat = meta.get("functional_category", "BUSINESS")
    ftag = meta.get("functional_tag", "BUSINESS")
    block_tag = f" [BLOCK: {meta['parent_block']}]" if meta.get("parent_block") else ""
    return f'''/**
 * @node: N{seq} — {meta["show_name"]}{block_tag}
 * @id: {meta["node_id"]}
 * @flow: {meta["flow_path"]}
 * @tag: {fcat}:{ftag}
 * @input:  {input_str}
 * @output: {output_str}
 * @js_category: {js_cat}
 * @lines: {meta["code_lines"]}
 * @hash: {meta["code_hash"][:12]}
 * @desc:   [待补充]
 */

'''


# ── duplicate detection ────────────────────────────────────────────────────

def detect_duplicates(all_metas: list[dict]) -> dict[str, list[int]]:
    """Find nodes with identical code (same hash) within the same project."""
    hash_to_seqs: dict[str, list[int]] = {}
    for meta in all_metas:
        h = meta.get("code_hash", "")
        if h:
            hash_to_seqs.setdefault(h, []).append(meta["seq"])

    return {h: seqs for h, seqs in hash_to_seqs.items() if len(seqs) > 1}


# ── block recursion ───────────────────────────────────────────────────────

def _find_block(blocks: list[dict], block_id: str) -> dict | None:
    """Find a block by id in the blocks list."""
    for blk in blocks:
        if blk.get("id") == block_id:
            return blk
    return None


def extract_nodes_from_flow(flow: dict, flow_path: str) -> list[dict]:
    """Recursively extract code nodes from a flow JSON, including nested blocks.

    Handles process_function_block nesting by traversing `blocks` list entries.
    """
    all_metas: list[dict] = []
    graph = flow.get("graphData", {})
    nodes = graph.get("nodes", [])
    blocks = flow.get("blocks", [])
    if not isinstance(blocks, list):
        blocks = []

    # Process top-level nodes
    for node in nodes:
        meta = extract_node_meta(node, flow_path)
        if meta:
            all_metas.append(meta)

        # Recurse into process_function_block content
        if node.get("component_id") == "process_function_block":
            block_id = node.get("id", "")
            block_data = _find_block(blocks, block_id)
            if block_data and isinstance(block_data, dict):
                block_graph = block_data.get("graphData", {})
                block_nodes = block_graph.get("nodes", [])
                block_blocks = block_data.get("blocks", [])
                if not isinstance(block_blocks, list):
                    block_blocks = []
                # Tag nested nodes with block origin
                block_name = (node.get("properties", [{}])[0].get("params", [{}])[0].get("value", "")
                              or block_data.get("name", block_id))
                nested_path = f"{flow_path}::{block_name}"
                for bnode in block_nodes:
                    bmeta = extract_node_meta(bnode, nested_path)
                    if bmeta:
                        bmeta["parent_block"] = block_name
                        all_metas.append(bmeta)
                    # Recurse deeper into nested blocks
                    if bnode.get("component_id") == "process_function_block":
                        bbid = bnode.get("id", "")
                        bbdata = _find_block(block_blocks, bbid)
                        if bbdata and isinstance(bbdata, dict):
                            bb_graph = bbdata.get("graphData", {})
                            bb_nodes = bb_graph.get("nodes", [])
                            bb_name = (bnode.get("properties", [{}])[0].get("params", [{}])[0].get("value", "")
                                       or bbdata.get("name", bbid))
                            nested2_path = f"{nested_path}::{bb_name}"
                            for bbn in bb_nodes:
                                bbmeta = extract_node_meta(bbn, nested2_path)
                                if bbmeta:
                                    bbmeta["parent_block"] = f"{block_name}/{bb_name}"
                                    all_metas.append(bbmeta)

    return all_metas


# ── UI node extraction ────────────────────────────────────────────────────

UI_COMPONENTS = {
    "mouse_single_click": ["element_selector", "click_type", "wait_timeout"],
    "keyboard_text_input": ["element_selector", "text_content", "wait_timeout"],
    "keyboard_hot_send": ["key_combination", "press_count"],
    "ui_element_wait_show": ["element_selector", "wait_timeout"],
    "ui_element_wait_vanish": ["element_selector", "wait_timeout"],
    "ui_element_exist": ["element_selector"],
    "ui_get_target_location": ["element_selector"],
    "mouse_wheel_scroll": ["scroll_lines", "scroll_direction"],
    "app_user_interaction": ["ui_type", "ui_content", "ui_options", "timeout"],
}


def extract_ui_node_meta(node: dict, flow_path: str) -> Optional[dict]:
    """Extract structured metadata from a UI automation node."""
    component_id = node.get("component_id", "")
    if component_id not in UI_COMPONENTS:
        return None

    props = node.get("properties", [])
    show_name_raw = props[0].get("params", [{}])[0].get("value", "")
    show_name = str(show_name_raw).strip('"') if isinstance(show_name_raw, str) else str(show_name_raw)

    ui_meta: dict[str, str] = {}
    for field in UI_COMPONENTS[component_id]:
        val = find_param(props, "input_params", field) or find_param(props, "base_params", field)
        if val is not None:
            ui_meta[field] = str(val)[:500]  # truncate long values

    selectors = ui_meta.get("element_selector", "")
    selector_type = None
    if selectors:
        if selectors.startswith("//") or selectors.startswith("(//"):
            selector_type = "xpath"
        elif "[" in selectors and ("@" in selectors or "=" in selectors):
            selector_type = "css"

    return {
        "node_id": node.get("id", ""),
        "component_id": component_id,
        "show_name": show_name,
        "flow_path": flow_path,
        "selector": selectors,
        "selector_type": selector_type,
        "ui_params": ui_meta,
    }


def extract_ui_nodes_from_flow(flow: dict, flow_path: str) -> list[dict]:
    """Extract UI automation node metadata from a flow file's top-level nodes."""
    ui_nodes: list[dict] = []
    nodes = flow.get("graphData", {}).get("nodes", [])
    for node in nodes:
        ui_meta = extract_ui_node_meta(node, flow_path)
        if ui_meta:
            ui_nodes.append(ui_meta)
    return ui_nodes


# ── cross-project detection ────────────────────────────────────────────────

def detect_cross_project_shared(manifests: list[dict]) -> dict:
    """Compare multiple project manifests to find cross-project shared code."""
    hash_map: dict[str, list[dict]] = {}
    for m in manifests:
        proj = m.get("project", "unknown")
        for n in m.get("nodes", []):
            h = n.get("code_hash", "")
            if not h:
                continue
            hash_map.setdefault(h, []).append({
                "project": proj,
                "seq": n["seq"],
                "show_name": n["show_name"],
                "component": n.get("component", ""),
            })

    cross = {}
    for h, entries in hash_map.items():
        projects = set(e["project"] for e in entries)
        if len(projects) > 1:
            cross[h] = entries
    return cross


# ── main ────────────────────────────────────────────────────────────────────

def extract_project(project_path: str, force: bool = False) -> str:
    """Extract all code nodes from an IPA Studio RPA project.

    Recursively extracts from nested process_function_block content,
    UI automation nodes, and code-bearing nodes. Produces .extracted_nodes/
    with manifest.json, .py/.js script files, and ui_nodes.json.

    Returns the path to the .extracted_nodes directory.
    """
    root = Path(project_path)
    if not root.is_dir():
        sys.exit(f"错误: 项目路径不存在: {root}")

    project_json = root / "project.json"
    if not project_json.exists():
        project_json = root / "project.rpa"
    if not project_json.exists():
        sys.exit(f"错误: 找不到 project.json 或 project.rpa: {root}")

    # Discover flow files
    with open(project_json, "r", encoding="utf-8") as f:
        proj = json.load(f)

    project_name = proj.get("project_info", {}).get("project_name", root.name)
    process_list = proj.get("process_list", [])

    out_dir = root / ".extracted_nodes"

    # Check if up-to-date
    if out_dir.exists() and not force:
        manifest_file = out_dir / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            existing_date = manifest.get("extracted_at", "")
            print(f"[跳过] .extracted_nodes 已存在 (提取日期: {existing_date})，使用 --force 强制重新提取")
            return str(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    all_metas: list[dict] = []
    all_ui_nodes: list[dict] = []
    seq = 0
    stats = {"py": 0, "js": 0, "boilerplate": 0, "skeleton": 0, "glue": 0, "business": 0, "total_lines": 0, "ui_nodes": 0}

    for proc in process_list:
        flow_path_rel = proc.get("process_path", "")
        flow_path = root / flow_path_rel
        if not flow_path.exists():
            print(f"[警告] 流程文件不存在，跳过: {flow_path_rel}")
            continue

        print(f"[解析] {flow_path_rel}")
        with open(flow_path, "r", encoding="utf-8") as f:
            flow = json.load(f)

        # Recursively extract code nodes (including nested blocks)
        metas = extract_nodes_from_flow(flow, flow_path_rel)
        for meta in metas:
            seq += 1
            short = flow_shortname(flow_path_rel)
            sname = safe_name(meta["show_name"])
            block_suffix = f"_{safe_name(meta['parent_block'], 12)}" if meta.get("parent_block") else ""
            filename = f"N{seq}_{short}{block_suffix}_{sname}{meta['ext']}"

            if meta["ext"] == ".py":
                header = node_header_python(meta, seq)
                stats["py"] += 1
            else:
                header = node_header_js(meta, seq)
                stats["js"] += 1

            fcat = meta.get("functional_category", "BUSINESS")
            if fcat == "BOILERPLATE":
                stats["boilerplate"] += 1
            elif fcat == "SKELETON":
                stats["skeleton"] += 1
            elif fcat == "GLUE":
                stats["glue"] += 1
            else:
                stats["business"] += 1
            stats["total_lines"] += meta["code_lines"]

            script_path = out_dir / filename
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(header + "\n" + meta["code"] + "\n")

            tag_parts = []
            fcat = meta.get("functional_category", "BUSINESS")
            ftag = meta.get("functional_tag", "BUSINESS")
            if fcat != "BUSINESS":
                tag_parts.append(f"{fcat}:{ftag}")
            if meta.get("js_category") and meta["js_category"] != "unknown":
                tag_parts.append(meta["js_category"])
            if meta.get("parent_block"):
                tag_parts.append(f"block:{meta['parent_block']}")

            tag_str = f" [{' | '.join(tag_parts)}]" if tag_parts else ""
            print(f"  → {filename} ({meta['code_lines']} lines, {len(meta['code'])} chars){tag_str}")

            all_metas.append({
                "seq": seq,
                "node_id": meta["node_id"],
                "show_name": meta["show_name"],
                "file": filename,
                "flow_file": meta["flow_path"],
                "component": meta["component_id"],
                "input_vars": meta["input_vars"],
                "output_vars": meta["output_vars"],
                "code_hash": meta["code_hash"],
                "code_lines": meta["code_lines"],
                "functional_category": meta.get("functional_category", "BUSINESS"),
                "functional_tag": meta.get("functional_tag", "BUSINESS"),
                "functional_tags": meta.get("functional_tags", []),
                "parent_block": meta.get("parent_block", ""),
                "is_common": meta.get("is_common", False),
                "common_desc": meta.get("common_desc", ""),
                "js_category": meta.get("js_category"),
                "description": "",
            })

        # Extract UI automation nodes
        ui_nodes = extract_ui_nodes_from_flow(flow, flow_path_rel)
        all_ui_nodes.extend(ui_nodes)
        stats["ui_nodes"] += len(ui_nodes)

    # Detect duplicates (within project)
    duplicates = detect_duplicates(all_metas)
    dup_groups = len(duplicates)
    dup_nodes = sum(len(v) - 1 for v in duplicates.values())

    # Build shared-node groups (same hash -> mark shared)
    hash_to_seqs: dict[str, list[int]] = {}
    for m_item in all_metas:
        h = m_item.get("code_hash", "")
        if h:
            hash_to_seqs.setdefault(h, []).append(m_item["seq"])
    for h, seqs in hash_to_seqs.items():
        if len(seqs) > 1:
            for m_item in all_metas:
                if m_item["seq"] in seqs[1:]:  # subsequent copies
                    existing = m_item.get("functional_tags", [])
                    m_item["functional_tags"] = existing + [f"SHARED:N{seqs[0]}"]

    # Write manifest
    manifest = {
        "project": project_name,
        "extracted_at": str(date.today()),
        "total_nodes": seq,
        "stats": {
            "py_nodes": stats["py"],
            "js_nodes": stats["js"],
            "boilerplate": stats["boilerplate"],
            "skeleton": stats["skeleton"],
            "glue": stats["glue"],
            "business": stats["business"],
            "ui_nodes": stats["ui_nodes"],
            "total_code_lines": stats["total_lines"],
            "duplicate_groups": dup_groups,
            "duplicate_nodes": dup_nodes,
        },
        "duplicates": {h: seqs for h, seqs in duplicates.items()} if duplicates else {},
        "ui_nodes": all_ui_nodes,
        "nodes": all_metas,
    }
    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 提取 {seq} 个代码节点 → {out_dir}")
    print(f"   Python: {stats['py']} | JS: {stats['js']} | BOILERPLATE: {stats['boilerplate']} | SKELETON: {stats['skeleton']} | GLUE: {stats['glue']} | BUSINESS: {stats['business']}")
    print(f"   UI节点: {stats['ui_nodes']} | 总代码行数: {stats['total_lines']}")
    if duplicates:
        print(f"   重复代码组: {dup_groups} (重复节点: {dup_nodes})")
        for h, seqs in list(duplicates.items())[:3]:
            print(f"     hash={h[:12]} → 节点 N{', N'.join(map(str, seqs))}")
    print(f"   manifest: {manifest_path}")
    return str(out_dir)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="提取 IPA Studio RPA 项目的代码节点到独立脚本文件"
    )
    parser.add_argument("project_path", help="IPA Studio 项目根目录路径")
    parser.add_argument("--force", action="store_true", help="强制重新提取，覆盖已有的 .extracted_nodes")
    args = parser.parse_args()

    extract_project(args.project_path, force=args.force)
