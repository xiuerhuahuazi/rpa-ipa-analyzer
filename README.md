# rpa-ipa-analyzer

Analyze IPA Studio RPA projects to produce comprehensive business and code analysis reports with Mermaid flowcharts.

## Overview

This skill analyzes IPA Studio RPA projects and generates professional analysis reports covering:

- Project architecture and workflow visualization (Mermaid diagrams)
- Code extraction from Python (`script_python_execute`) and JavaScript (`browser_inject_js_code`) nodes
- Business logic interpretation with domain glossary
- End-to-end data lineage mapping
- Risk assessment and optimization suggestions
- Cross-project code deduplication

## Supported Project Types

| Type | Description | Key Components |
|------|-------------|----------------|
| **Data Processing** | Excel/CSV manipulation, pandas workflows | `script_python_execute`, `log_task` |
| **Web Automation** | Browser interaction, JS injection | `browser_inject_js_code`, `mouse_single_click` |
| **Mixed** | Combines both patterns | Multiple component types |

---

## Installation

### Prerequisites

- **Python 3.8+** (standard library only, no pip install required)
- IPA Studio project files (`project.json`, flow JSON files)
- One of the supported AI coding platforms (see [Platform Setup](#platform-setup))

### Step 1: Clone the Repository

```bash
git clone https://github.com/xiuerhuahuazi/rpa-ipa-analyzer.git
```

### Step 2: Platform Setup

> **Important:** This repo contains files for multiple platforms plus repo metadata. Only copy the files your platform actually needs. The table below shows what's required per platform.

#### What to Copy (Per Platform)

| File | Claude Code | OpenAI Codex | OpenClaw |
|------|:-----------:|:------------:|:--------:|
| `SKILL.md` | ✅ Required | ✅ Required | ✅ Required |
| `scripts/` | ✅ Required | ✅ Required | ✅ Required |
| `references/` | ✅ Required | ✅ Required | ✅ Required |
| `evals/` | ✅ Optional | ❌ Not needed | ❌ Not needed |
| `platforms/codex/` | ❌ Not needed | ✅ Required | ❌ Not needed |
| `platforms/openclaw/` | ❌ Not needed | ❌ Not needed | ✅ Required |
| `README.md` | ❌ Not needed | ❌ Not needed | ❌ Not needed |
| `LICENSE` | ❌ Not needed | ❌ Not needed | ❌ Not needed |
| `CHANGELOG.md` | ❌ Not needed | ❌ Not needed | ❌ Not needed |
| `.gitignore` | ❌ Not needed | ❌ Not needed | ❌ Not needed |
| `requirements.txt` | ❌ Not needed | ❌ Not needed | ❌ Not needed |

Repo-only files (`README.md`, `LICENSE`, `CHANGELOG.md`, `.gitignore`, `requirements.txt`) are project metadata — they are not used by any platform at runtime and should be excluded from skill installation.

#### Claude Code

```bash
# Copy only the essential files:
mkdir -p ~/.claude/skills/rpa-ipa-analyzer
cp SKILL.md ~/.claude/skills/rpa-ipa-analyzer/
cp -r scripts/ ~/.claude/skills/rpa-ipa-analyzer/
cp -r references/ ~/.claude/skills/rpa-ipa-analyzer/
cp -r evals/ ~/.claude/skills/rpa-ipa-analyzer/   # optional
```

Verify installation:
```bash
ls ~/.claude/skills/rpa-ipa-analyzer/SKILL.md
```

#### OpenAI Codex

```bash
mkdir -p ~/.codex/skills/rpa-ipa-analyzer
cp SKILL.md ~/.codex/skills/rpa-ipa-analyzer/
cp -r scripts/ ~/.codex/skills/rpa-ipa-analyzer/
cp -r references/ ~/.codex/skills/rpa-ipa-analyzer/
cp platforms/codex/codex.yaml ~/.codex/skills/rpa-ipa-analyzer/
```

#### OpenClaw

```bash
mkdir -p ~/.openclaw/skills/rpa-ipa-analyzer
cp SKILL.md ~/.openclaw/skills/rpa-ipa-analyzer/
cp -r scripts/ ~/.openclaw/skills/rpa-ipa-analyzer/
cp -r references/ ~/.openclaw/skills/rpa-ipa-analyzer/
cp platforms/openclaw/skill.yaml ~/.openclaw/skills/rpa-ipa-analyzer/
```

---

## Quick Start

```bash
# 1. Navigate to an IPA Studio project
cd /path/to/your-ipa-project

# 2. Run the extraction script to prepare code nodes
python3 /path/to/rpa-ipa-analyzer/scripts/extract_nodes.py . --force

# 3. Trigger the skill in Claude Code (or your platform)
#    In Claude Code, just say:
#    "请分析当前这个 IPA Studio RPA 项目"
```

**Output**: `分析报告_{项目名}.md` is generated in the project directory.

### Example Output Structure

```
分析报告_MyProject.md
├── 一、整体工作流分析
│   ├── 1.1 项目架构概览 (Mermaid flowchart)
│   ├── 1.2 主流程完整路径
│   ├── 1.3 条件分支与路由逻辑
│   └── 1.4 子流程调用关系
├── 二、节点级详细拆解
│   ├── 2.1 阶段划分与概述
│   ├── 2.2 代码节点逐一详解 (per-node analysis)
│   └── 2.3 UI 自动化节点分析
├── 三、全局参数与配置分析
├── 四、业务逻辑深度解读
│   ├── 4.1 整体业务目标
│   ├── 4.2 核心业务概念 (domain glossary)
│   ├── 4.3 数据流转全路径 (ASCII diagram)
│   ├── 4.4 核心业务规则与计算公式
│   └── 4.5 Excel 读写完整映射
├── 五、综合分析
│   ├── 5.1 组件使用统计与洞察
│   ├── 5.2 优缺点分析
│   ├── 5.3 优化建议
│   └── 5.4 潜在风险点
└── 附录
    ├── A. 项目文件清单
    └── B. 节点索引
```

---

## Directory Structure

```
rpa-ipa-analyzer/
├── SKILL.md              # [CORE] Main skill instructions — all platforms need this
├── scripts/
│   └── extract_nodes.py  # [CORE] Code extraction utility — all platforms need this
├── references/
│   ├── ipa_format.md     # [CORE] IPA Studio JSON format reference
│   └── report_template.md # [CORE] Report structure template
├── evals/
│   └── evals.json        # [CLAUDE ONLY] Evaluation test cases (optional)
├── platforms/
│   ├── codex/
│   │   └── codex.yaml    # [CODEX ONLY] Platform adapter
│   └── openclaw/
│       └── skill.yaml    # [OPENCLAW ONLY] Platform adapter
├── README.md             # [REPO ONLY] Project documentation — do NOT install
├── LICENSE               # [REPO ONLY] MIT License — do NOT install
├── CHANGELOG.md           # [REPO ONLY] Version history — do NOT install
├── requirements.txt       # [REPO ONLY] Deps reference — do NOT install (no deps)
└── .gitignore             # [REPO ONLY] Git config — do NOT install
```

**Legend:**
- `[CORE]` — Required by all platforms. Always copy these.
- `[CLAUDE ONLY]` / `[CODEX ONLY]` / `[OPENCLAW ONLY]` — Platform-specific. Only copy for that platform.
- `[REPO ONLY]` — Project metadata. Never copy for any platform installation.

---

## Key Features

### Functional Tagging System
Automatically classifies code nodes as BOILERPLATE, SKELETON, GLUE, or BUSINESS — avoiding redundant re-analysis of infrastructure code.

### JavaScript Injection Classification
Classifies every `browser_inject_js_code` node into one of 7 categories: DOM Navigation, Form Fill, Form Read, State Detection, Data Extraction, Page Cleanup, Button Click.

### Recursive Block Traversal
Extracts code nodes from nested `process_function_block` structures up to 3 levels deep.

### Cross-Project Deduplication
Detects identical code across multiple projects via MD5 hashing, enabling shared infrastructure identification.

### 14 RPA Design Patterns Documented
From template-based Excel generation to CAPTCHA auto-recognition — recognized patterns are noted in the report automatically.

---

## Requirements

- Python 3.8+ (standard library only — `json`, `re`, `hashlib`, `pathlib`, `argparse`)
- IPA Studio project files: `project.json`, flow JSON files, `globalParams.json`, `processResult.json`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `project.json not found` | Ensure you're running from the IPA Studio project root directory |
| `Flow file not found` | Check `process_list` paths in `project.json` — files must exist relative to project root |
| JSON decode error | IPA Studio exports UTF-8 JSON. Check file encoding is not GBK/GB2312 |
| Large file (4MB+) slow | The skill uses parallel Explore agents for large files. Ensure sufficient context window |
| `.extracted_nodes/` stale | Run `extract_nodes.py --force` to regenerate after flow file changes |
| Python version too old | Requires Python 3.8+ for `pathlib` and type hints |
| Skill not triggering | Verify SKILL.md is in the correct platform skills directory |

---

## Compatibility

| Platform | Status | Notes |
|----------|--------|-------|
| **Claude Code** | ✅ Native | YAML frontmatter format supported directly |
| **OpenAI Codex** | ⚠️ Requires adapter | See [Codex setup](#openai-codex) — needs `codex.yaml` |
| **OpenClaw** | ⚠️ Requires adapter | See [OpenClaw setup](#openclaw) — needs `skill.yaml` |

The core analysis logic (`extract_nodes.py` + report templates) is platform-agnostic. Only the skill registration mechanism differs between platforms.

---

## License

MIT License — see [LICENSE](LICENSE)
