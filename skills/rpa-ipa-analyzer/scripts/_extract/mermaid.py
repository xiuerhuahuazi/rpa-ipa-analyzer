"""Mermaid 图表静态检查 —— 报告定稿前必跑。

**两起实测事故**（都表现为「图不渲染、正文正常」，纯文本看不见）：

1) 边标签里写括号（2026-10-27）：

       Main -->|int(total) != 0| Borrow
       Parse error on line 6: ... got 'PS'

2) 节点标签里写括号（2026-10-27，同一技能首次交付的报告）：

       G1[查找JSON → 数据合并(三分组去重) → EXCEL美化(3 sheet+判断点公式)]
       Parse error on line 15: ... expecting ..., got 'PS'

结论：**括号/方括号/花括号在 unquoted 标签里都属于形状语法**；边标签和节点标签
都要机器检查。节点标签想用括号，必须整体加双引号：`G1["…(…)…"]`。

本模块把「会让 mermaid 报错 / 变难看」的写法做成可执行的检查项，
由 `rpa.cmd check-mermaid <报告.md>` 调用。

检查项（ERROR 必须为 0 才能交付）：

E1 首个非空行不是受支持的图类型
E2 边标签为空，或含 `( ) [ ] { } ;`（mermaid 语法冲突）
E3 未被引号包裹的边标签里出现 `"`（v10+ 才支持，旧渲染器会挂）
E4 每行的 `|` 个数为奇数（边标签未闭合）
E5 引号内的节点标签里出现 `|`
E6 引号数量为奇数（标签未闭合）
E7 `subgraph` 与 `end` 不配对
E8 代码块为空 / 代码围栏未闭合
E9 制表符（部分渲染器会吞掉缩进）
E10 节点/子图标签**未加引号**且含 `( ) [ ] { } | ;`（第二起事故的根因）
E11 虚线边带文字写成 `-.文字.->`（合法形式：`-. 文字 .->` 或 `-.->|文字|`）

WARN（不阻断，但会在缩放后的报告里变成「字太小」）：

W1 单图节点 > 20，建议拆图
W2 `LR` 方向且节点 > 12，宽度会很大（3000px+），缩放后文字约 4px
W3 stateDiagram 用裸中文状态 ID，建议 `state "文案" as s1`
W4 标签里出现 `#` / `<` 等实体或 HTML（部分渲染器不支持）
W5 标签里出现字面量 `\\n`，建议改 `<br/>`
W6 边标签含 `"`（仅 mermaid ≥10 支持，旧渲染器会失败）
W7 节点标签未加引号（含中文/空格/箭头），按铁律应统一 `"…"`
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_HEADS = (
    "flowchart", "graph", "statediagram-v2", "statediagram", "sequencediagram",
    "classdiagram", "erdiagram", "gantt", "pie", "journey", "mindmap", "timeline",
)

# 边标签里禁止出现的字符：括号/方括号/花括号属于 mermaid 形状语法，分号是语句分隔
EDGE_LABEL_FORBIDDEN = {
    "(": "半角左括号 (",
    ")": "半角右括号 )",
    "[": "方括号 [",
    "]": "方括号 ]",
    "{": "花括号 {",
    "}": "花括号 }",
    ";": "分号 ;",
}

ARROW_RE = re.compile(r"(-->|---|-\.->|-\.-|==>|===|--o|--x|<-->|~~~)")
NODE_DEF_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?=[\[\(\{])")
KEYWORDS = {
    "subgraph", "end", "style", "classdef", "class", "click", "linkstyle",
    "direction", "graph", "flowchart", "statediagram-v2", "statediagram",
}

TAB = "\t"

# 节点/子图标签的禁用字符（未加引号时）：与边标签同一套，括号属于形状语法。
# 加了双引号的内层同名字符是纯文本，不在此列。
NODE_LABEL_FORBIDDEN = EDGE_LABEL_FORBIDDEN

# 形状识别顺序：复合形状必须先于简单形状，匹配到的整段会被遮蔽，
# 避免 `A([x])` 被当成「矩形 [x]」重复检查。
SHAPES = (
    ("stadium", re.compile(r"\(\[(?P<c>[^\[\]]*)\]\)")),
    ("cylinder", re.compile(r"\[\((?P<c>[^()]*)\)\]")),
    ("subroutine", re.compile(r"\[\[(?P<c>[^\[\]]*)\]\]")),
    ("circle", re.compile(r"\(\((?P<c>[^()]*)\)\)")),
    ("hexagon", re.compile(r"\{\{(?P<c>[^{}]*)\}\}")),
    ("rect", re.compile(r"\[(?P<c>[^\[\]]*)\]")),
    ("diamond", re.compile(r"\{(?P<c>[^{}]*)\}")),
    ("round", re.compile(r"\((?P<c>[^()]*)\)")),
)

# 只对这些图类型做「形状标签」检查（其余图类型语法不同，强行检查会误报）
FLOW_HEADS = ("flowchart", "graph")

# 虚线边带文字：`-.try.->` 非法；`-.->`、`-.->|x|`、`-. x .->` 合法
DOTTED_TEXT_RE = re.compile(r"-\.(?P<t>[^\s.]+?)\.->")

# 这些行不是节点定义（样式/类/点击/注释），跳过形状扫描
SKIP_LINE_PREFIXES = (
    "%%", "classdef", "class ", "style ", "linkstyle", "click ", "direction",
)


def _severity(level, line_no, msg):
    return {"level": level, "line": line_no, "msg": msg}


def split_blocks(text):
    """把 markdown 拆成 [(start_line_1based, lines)]，只取 ```mermaid 块。"""
    blocks = []
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].strip().startswith("```") and "mermaid" in lines[i].strip().lower():
            start = i + 1  # 1-based 行号（围栏行本身）
            i += 1
            buf = []
            closed = False
            while i < n:
                if lines[i].strip().startswith("```"):
                    closed = True
                    break
                buf.append(lines[i])
                i += 1
            blocks.append((start, buf, closed))
            i += 1
        else:
            i += 1
    return blocks


def scan_node_labels(raw):
    """抽取一行里所有「节点/子图标签」的文本内容。

    返回 [(content, shape_name)]。已剔除：
      - 样式/类/注释行
      - 边标签区域 `|...|`（由 E2/E4 单独负责）
    匹配到的形状整段被遮蔽，防止复合形状被二次匹配。
    """
    stripped = raw.strip()
    if not stripped:
        return []
    low = stripped.lower()
    for pre in SKIP_LINE_PREFIXES:
        if low.startswith(pre):
            return []

    work = re.sub(r"\|[^|]*\|", lambda m: " " * len(m.group(0)), raw)
    found = []
    for shape, pattern in SHAPES:
        while True:
            m = pattern.search(work)
            if not m:
                break
            found.append((m.group("c"), shape))
            work = work[:m.start()] + " " * (m.end() - m.start()) + work[m.end():]
    return found


def _is_quoted(text):
    text = text.strip()
    return len(text) >= 2 and text.startswith('"') and text.endswith('"')


def check_block(lines):
    """检查单个 mermaid 块，返回 (errors, warnings)。"""
    errors = []
    warnings = []

    if not any(x.strip() for x in lines):
        errors.append(_severity("ERROR", 0, "E8 空 mermaid 块"))
        return errors, warnings

    # 首个非空行 = 图类型
    head = ""
    head_idx = 0
    for idx, raw in enumerate(lines):
        if raw.strip():
            head = raw.strip()
            head_idx = idx
            break
    head_word = head.split()[0].lower() if head else ""
    if head_word not in ALLOWED_HEADS:
        errors.append(_severity("ERROR", head_idx + 1,
                                "E1 未知图类型 %r（支持：flowchart/stateDiagram-v2/…）" % head))

    orientation = head.split()[1].upper() if len(head.split()) > 1 else ""

    # 逐行检查
    node_ids = set()
    unquoted_labels = []   # (行号, 文本)：W7 聚合上报，避免几百条同类 WARN 淹没真问题
    subgraph_depth = 0
    for idx, raw in enumerate(lines):
        line_no = idx + 1
        if TAB in raw:
            errors.append(_severity("ERROR", line_no, "E9 缩进用了制表符，改用空格"))

        has_arrow = bool(ARROW_RE.search(raw))

        # E7 subgraph/end 配对
        low = raw.strip().lower()
        if low.startswith("subgraph"):
            subgraph_depth += 1
        elif low == "end":
            subgraph_depth -= 1
            if subgraph_depth < 0:
                errors.append(_severity("ERROR", line_no, "E7 多余的 end（没有对应 subgraph）"))
                subgraph_depth = 0

        # E4 / E2 / E3：边标签
        if has_arrow and "|" in raw:
            parts = raw.split("|")
            if len(parts) % 2 == 0:
                errors.append(_severity("ERROR", line_no, "E4 边标签未闭合（| 个数为奇数）"))
            else:
                for label in parts[1::2]:
                    text = label.strip()
                    if not text:
                        errors.append(_severity("ERROR", line_no, "E2 空边标签"))
                        continue
                    for ch, name in EDGE_LABEL_FORBIDDEN.items():
                        if ch in text:
                            errors.append(_severity(
                                "ERROR", line_no,
                                "E2 边标签 %r 含 %s；mermaid 会把它当形状语法并整图报错"
                                "（改写为无括号形式，如 total!=0 / IsOpen=True）" % (text, name)))
                            break
                    if '"' in text:
                        # v10.2+ 支持带引号的边标签；旧渲染器（部分编辑器内置 mermaid 9）不支持，
                        # 因此降级为 WARN：目标渲染器是 11.x（DSH 桌面端）时可忽略。
                        warnings.append(_severity(
                            "WARN", line_no,
                            "W6 边标签 %r 含双引号（仅 mermaid ≥10 支持；旧渲染器会失败）" % text))
                    if "#" in text:
                        warnings.append(_severity("WARN", line_no,
                                                  "W4 边标签 %r 含 #（实体转义，部分渲染器不支持）" % text))
                    if "\\n" in text:
                        warnings.append(_severity("WARN", line_no,
                                                  "W5 边标签 %r 含字面量 \\\\n，建议用 <br/>" % text))

        # E5 / E6：引号内标签
        for m in re.finditer(r'"([^"]*)"', raw):
            inner = m.group(1)
            if "|" in inner:
                errors.append(_severity("ERROR", line_no,
                                        "E5 节点标签 %r 含 |；| 只用于边标签" % inner))
        if raw.count('"') % 2 == 1:
            errors.append(_severity("ERROR", line_no, "E6 双引号数量为奇数（节点标签未闭合）"))

        # E11：虚线边带文字（`-.try.->` 非法）
        dm = DOTTED_TEXT_RE.search(raw)
        if dm:
            errors.append(_severity(
                "ERROR", line_no,
                "E11 虚线边 %r 写法错误；合法形式是 `-. 文字 .->` 或 `-.->|文字|`"
                % ("-." + dm.group("t") + ".->")))

        # E10 / W4 / W5 / W7：节点与子图标签（仅 flowchart / graph）
        if head_word in FLOW_HEADS:
            for content, shape in scan_node_labels(raw):
                text = content.strip()
                if not text or _is_quoted(content):
                    continue
                bad = [ch for ch in NODE_LABEL_FORBIDDEN if ch in content]
                if bad:
                    errors.append(_severity(
                        "ERROR", line_no,
                        "E10 节点标签 %r 含 %s（未加引号）；括号属于形状语法，"
                        "请整体加双引号，如 A[\"...(…)...\"]"
                        % (text, NODE_LABEL_FORBIDDEN[bad[0]])))
                    continue
                if "#" in content:
                    warnings.append(_severity(
                        "WARN", line_no,
                        "W4 节点标签 %r 含 #（实体转义，部分渲染器不支持）" % text))
                if "\\n" in content:
                    warnings.append(_severity(
                        "WARN", line_no,
                        "W5 节点标签 %r 含字面量 \\\\n，建议用 <br/>" % text))
                if any(ord(c) > 127 for c in content) or " " in content or "→" in content:
                    unquoted_labels.append((line_no, text))

        # 节点统计（用于 W1/W2）
        for m in NODE_DEF_RE.finditer(raw):
            tok = m.group(1)
            if tok.lower() not in KEYWORDS:
                node_ids.add(tok)

        # W3 stateDiagram 裸中文状态
        if head_word in ("statediagram", "statediagram-v2"):
            sm = re.match(r"\s*([^\s:\[\](){}\"|<>-][^\s:]*?)\s*(?:-->|---)", raw)
            if sm and any(ord(c) > 127 for c in sm.group(1)):
                if " as " not in raw:
                    warnings.append(_severity(
                        "WARN", line_no,
                        "W3 状态 ID %r 含中文，建议 `state \"文案\" as s1` 再用 s1" % sm.group(1)))

    if unquoted_labels:
        first_lines = ", ".join(str(n) for n, _ in unquoted_labels[:5])
        sample = unquoted_labels[0][1]
        warnings.append(_severity(
            "WARN", unquoted_labels[0][0],
            "W7 本图有 %d 处节点标签未加引号（首行 %s，如 %r）；"
            "按铁律统一写成 A[\"…\"]（中文/空格/箭头都要进引号）"
            % (len(unquoted_labels), first_lines, sample)))

    if subgraph_depth > 0:
        errors.append(_severity("ERROR", len(lines), "E7 subgraph 未用 end 关闭"))

    if len(node_ids) > 20:
        warnings.append(_severity("WARN", 0,
                                  "W1 单图节点 %d 个（>20），建议拆分" % len(node_ids)))
    if orientation == "LR" and len(node_ids) > 12:
        warnings.append(_severity(
            "WARN", 0,
            "W2 LR 方向 + %d 节点，图会很宽（实测可达 3000px），缩放后字过小；"
            "建议改 TB 或拆分" % len(node_ids)))

    return errors, warnings


def check_text(text, label="<text>"):
    all_errors, all_warnings = [], []
    blocks = split_blocks(text)
    if not blocks:
        all_errors.append(_severity("ERROR", 0, "E8 未找到任何 ```mermaid 代码块（%s）" % label))
        return all_errors, all_warnings
    for start, lines, closed in blocks:
        if not closed:
            all_errors.append(_severity("ERROR", 0, "E8 mermaid 代码围栏未闭合（%s:%d）" % (label, start)))
        errs, warns = check_block(lines)
        for e in errs:
            e["loc"] = "%s:%d" % (label, start + e["line"])
            all_errors.append(e)
        for w in warns:
            w["loc"] = "%s:%d" % (label, start + w["line"])
            all_warnings.append(w)
    return all_errors, all_warnings


def check_paths(paths, strict=False):
    """检查若干 .md / .mmd 文件或目录；返回进程退出码（0 通过，2 失败）。"""
    files = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
            files.extend(sorted(path.rglob("*.mmd")))
        elif path.exists():
            files.append(path)
        else:
            print("[check-mermaid] 路径不存在：%s" % p)
            return 2

    total_err = total_warn = 0
    blocks = 0
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        if f.suffix.lower() in (".mmd", ".mermaid"):
            text = "```mermaid\n" + text + "\n```\n"
        errs, warns = check_text(text, label=str(f))
        if errs and errs[0]["msg"].startswith("E8 未找到"):
            continue  # 没有 mermaid 的 md 静默跳过
        blocks += 1
        for e in errs:
            print("[ERROR] %s  %s" % (e["loc"], e["msg"]))
        for w in warns:
            print("[WARN ] %s  %s" % (w["loc"], w["msg"]))
        total_err += len(errs)
        total_warn += len(warns)

    print("")
    print("[check-mermaid] 文件 %d 个 / 含 mermaid 的 %d 个 / ERROR %d / WARN %d"
          % (len(files), blocks, total_err, total_warn))
    if total_err:
        print("[check-mermaid] 失败：先修 ERROR 再交付（规则见 references/mermaid_check.md）")
        return 2
    if strict and total_warn:
        print("[check-mermaid] --strict：WARN 也算失败")
        return 2
    print("[check-mermaid] 通过")
    return 0


SELF_TESTS = (
    # (名称, 图内容, 必须出现的 ERROR 码, 必须出现的 WARN 码)
    ("ok_quoted_labels", 'graph TB\n  A["开始"] --> B["结束"]', set(), set()),
    ("ok_quoted_parens", 'graph TB\n  G1["合并(去重) → 美化"]', set(), set()),
    ("ok_shapes", 'graph TB\n  A(["体育场"]) --> B[(圆柱)]\n  B --> C((圆))\n  C --> D{判断}', set(), set()),
    ("ok_subgraph_quoted", 'graph TB\n  subgraph L0["主控层 主流程"]\n    A["x"]\n  end', set(), set()),
    ("ok_dotted_text_proper", 'graph TB\n  A -. "try" .-> B', set(), set()),
    ("ok_edge_label_plain", 'graph TB\n  A -->|total!=0| B', set(), set()),
    ("bad_node_parens",
     'graph TB\n  G1[查找JSON → 数据合并(三分组去重) → EXCEL美化(3 sheet+判断点公式)]',
     {"E10"}, set()),
    ("bad_node_semicolon", 'graph TB\n  A[x;y]', {"E10"}, set()),
    ("bad_edge_parens", 'graph TB\n  A -->|int(total) != 0| B', {"E2"}, set()),
    ("bad_dotted_text", 'graph TB\n  A-.try.->B', {"E11"}, set()),
    ("bad_subgraph_unclosed", 'graph TB\n  subgraph L0["x"]\n    A["y"]', {"E7"}, set()),
    ("warn_unquoted_cjk", 'graph TB\n  A[开始]', set(), {"W7"}),
)


def self_test():
    """内置回归用例：保证两起事故的写法永远被抓到。返回退出码。"""
    failed = 0
    for name, body, must_err, must_warn in SELF_TESTS:
        text = "```mermaid\n" + body.strip("\n") + "\n```\n"
        errs, warns = check_text(text, label=name)
        err_codes = {}
        for e in errs:
            code = e["msg"].split()[0]
            err_codes[code] = err_codes.get(code, 0) + 1
        warn_codes = {}
        for w in warns:
            code = w["msg"].split()[0]
            warn_codes[code] = warn_codes.get(code, 0) + 1

        missing_e = sorted(must_err - set(err_codes))
        missing_w = sorted(must_warn - set(warn_codes))
        ok = not missing_e and not missing_w
        if ok:
            print("[self-test] ok   %-22s ERROR=%s WARN=%s"
                  % (name, sorted(err_codes) or "-", sorted(warn_codes) or "-"))
        else:
            failed += 1
            print("[self-test] FAIL %-22s 缺少 %s%s（实际 ERROR=%s WARN=%s）"
                  % (name, missing_e or "", missing_w or "",
                     sorted(err_codes) or "-", sorted(warn_codes) or "-"))
            for e in errs:
                print("             ERROR %s" % e["msg"])
    print("")
    if failed:
        print("[self-test] 失败 %d / %d" % (failed, len(SELF_TESTS)))
        return 2
    print("[self-test] 全部通过（%d 例）" % len(SELF_TESTS))
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--self-test" in argv:
        sys.exit(self_test())
    strict = "--strict" in argv
    argv = [a for a in argv if a != "--strict"]
    if not argv:
        argv = ["."]
    sys.exit(check_paths(argv, strict=strict))
