from __future__ import annotations
import re
import hashlib
from typing import Any


def safe_name(text: str, max_len: int = 20) -> str:
    text = str(text).strip() or "unnamed"
    text = text.replace("：", "_").replace("，", "_").replace("、", "_")
    text = text.replace(" ", "_").replace("\n", "").replace("\r", "")
    text = re.sub(r"[^\w一-鿿\-]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len] if len(text) > max_len else text


def flow_shortname(path: str) -> str:
    name = path.replace("\\", "/").replace(".json", "")
    name = name.replace("/", "_").replace(".", "_")
    name = name.replace("cw_通用_", "")
    return name


def code_hash(code: str) -> str:
    normalized = re.sub(r"\s+", " ", code.strip())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def count_code_lines(code: str) -> int:
    lines = code.strip().splitlines()
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("//"):
            count += 1
    return count


def find_param(properties: list[dict], prop_type: str, param_id: str) -> Any:
    for prop in properties:
        if prop.get("type") != prop_type:
            continue
        for param in prop.get("params", []):
            if param.get("id") == param_id:
                return param.get("value")
    return None


def _describe_value(v: Any) -> str:
    if isinstance(v, str):
        lines = v.strip().splitlines()
        if len(lines) > 1 and any(
            kw in v for kw in ("def ", "import ", "from ", "function", "=>", "var ", "let ", "const ")
        ):
            return f"<code: {len(lines)} lines, {len(v)} chars>"
        if len(v) > 500:
            return f"<str: {len(v)} chars>"
        return v
    if isinstance(v, dict):
        return f"<dict: {len(v)} keys>"
    if isinstance(v, list):
        return f"<list: {len(v)} items>"
    return str(v)[:500]
