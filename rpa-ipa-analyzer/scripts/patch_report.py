#!/usr/bin/env python3
"""Surgically replace a node section in 分析报告_*.md by #### 节点 N{n} anchor.

Usage:
    python patch_report.py <report.md> --node 12 --from-file node_N12.md
    python patch_report.py <report.md> --node 12 --delete
    python patch_report.py <report.md> --meta "分析日期：2026-07-28（增量更新） | 变更节点：N12"
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path


NODE_RE = re.compile(
    r"(?m)^(#### 节点 N(\d+):[^\n]*\n)(.*?)(?=^#### 节点 N\d+:|^## |\Z)",
    re.DOTALL,
)


def replace_node_section(text: str, seq: int, new_body: str) -> str:
    """Replace or append #### 节点 N{seq} section. new_body should include the heading."""
    new_body = new_body.strip() + "\n\n"
    if not new_body.lstrip().startswith("####"):
        sys.exit("错误: --from-file 内容必须以 #### 节点 N{n}: 开头")

    matches = list(NODE_RE.finditer(text))
    for m in matches:
        if int(m.group(2)) == seq:
            return text[: m.start()] + new_body + text[m.end() :]

    # Append after last node section, or before ## 三 / Appendix
    insert_at = None
    if matches:
        insert_at = matches[-1].end()
    else:
        m2 = re.search(r"(?m)^## 三、", text)
        insert_at = m2.start() if m2 else len(text)
    return text[:insert_at] + new_body + text[insert_at:]


def delete_node_section(text: str, seq: int) -> str:
    matches = list(NODE_RE.finditer(text))
    for m in matches:
        if int(m.group(2)) == seq:
            return text[: m.start()] + text[m.end() :]
    sys.exit(f"错误: 未找到 #### 节点 N{seq}")


def update_meta(text: str, meta_line: str) -> str:
    """Replace first blockquote meta line, or insert after H1."""
    meta_line = meta_line.strip()
    if not meta_line.startswith(">"):
        meta_line = "> " + meta_line
    m = re.search(r"(?m)^> .+$", text)
    if m:
        return text[: m.start()] + meta_line + text[m.end() :]
    m2 = re.search(r"(?m)^# .+$", text)
    if m2:
        end = m2.end()
        return text[:end] + "\n\n" + meta_line + "\n" + text[end:]
    return meta_line + "\n\n" + text


def main():
    ap = argparse.ArgumentParser(description="Patch node sections in analysis report")
    ap.add_argument("report")
    ap.add_argument("--node", type=int, help="Node seq to replace/delete")
    ap.add_argument("--from-file", help="Markdown file for new node section")
    ap.add_argument("--delete", action="store_true")
    ap.add_argument("--meta", help="Replace report meta blockquote line")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = Path(args.report)
    if not path.exists():
        sys.exit(f"错误: 报告不存在: {path}")
    text = path.read_text(encoding="utf-8")

    if args.meta:
        text = update_meta(text, args.meta)

    if args.node is not None:
        if args.delete:
            text = delete_node_section(text, args.node)
        elif args.from_file:
            body = Path(args.from_file).read_text(encoding="utf-8")
            text = replace_node_section(text, args.node, body)
        else:
            sys.exit("错误: --node 需配合 --from-file 或 --delete")

    if args.dry_run:
        print(text[:2000])
        print("... (dry-run, not written)")
        return

    path.write_text(text, encoding="utf-8")
    print(f"[完成] 已更新 {path}")


if __name__ == "__main__":
    main()
