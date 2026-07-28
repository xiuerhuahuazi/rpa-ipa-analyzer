# rpa-ipa-analyzer

Analyze IPA Studio RPA projects to produce comprehensive business and code analysis reports with Mermaid flowcharts. Supports three depth levels (quick/standard/deep) with auto-detection.

## Overview

This skill analyzes IPA Studio RPA projects and generates professional analysis reports covering:

- Project architecture and workflow visualization (Mermaid diagrams)
- Code extraction from Python (`script_python_execute`) and JavaScript (`browser_inject_js_code`) nodes
- Business logic interpretation with domain glossary
- End-to-end data lineage mapping
- **Variable lineage tracing**: `extract_nodes.py trace` subcommand with BFS on edges graph
- **Design pattern matching**: 5 universal patterns with checklist-based detection
- Risk assessment and optimization suggestions
- Cross-project code deduplication
- **6-Lens Parallel Code Audit** (security, performance, API contracts, error handling, testing gaps, documentation drift) as independent `/rpa-ipa-audit` command
- **Auto-generated `@desc`**: extracted code files include meaningful descriptions instead of `[待补充]` placeholders
- **Adaptive component promotion**: cross-project usage tracking auto-upgrades heuristic components in `ipa_format.md`

## Highlights

- **4-Layer Capability Model**: Phase 0 (self-calibration) -> Layer 1 (project modeling) -> Layer 2 (code & business analysis) -> Layer 3 (artifact generation). Cleaner than the old 7-Phase linear model.
- **Three Depth Levels**: quick / standard / deep with auto-scale detection. **v3.1**: always run extract+skeleton first (LLM never reads raw multi-MB flow JSON); §2.2 references `.extracted_nodes/` instead of pasting source.
- **Token-optimized incremental update**: `diff` + `patch` CLI; audit defaults to hash-changed nodes only (`--full` for full audit).
- **Edges Collection**: `extract_nodes.py` extracts `graphData.edges[]` into `manifest.json`, enabling the `trace` subcommand.
- **Modular Extractor**: CLI subcommands `extract/list/stats/trace/compare/diff/skeleton/patch`.
- **Independent Audit Command**: `/rpa-ipa-audit` as opt-in heavy operation.
- **Regression Test Framework**: golden manifest diff + structured assertions, 50/50 evals pass.

## Supported Project Types

| Type | Description | Key Components |
|------|-------------|----------------|
| **Data Processing** | Excel/CSV manipulation, pandas workflows | `script_python_execute`, `log_task` |
| **Web Automation** | Browser interaction, JS injection | `browser_inject_js_code`, `mouse_single_click` |
| **Mixed** | Combines both patterns | Multiple component types |

## Installation

### Prerequisites

- **Python 3.8+** (standard library only, no pip install required)
- IPA Studio project files (`project.json`, flow JSON files)
- One of the supported AI coding platforms

### Claude Code

```bash
git clone https://github.com/xiuerhuahuazi/rpa-ipa-analyzer.git
cd rpa-ipa-analyzer
mkdir -p ~/.claude/skills/rpa-ipa-analyzer
cp -r rpa-ipa-analyzer/* ~/.claude/skills/rpa-ipa-analyzer/
mkdir -p ~/.claude/skills/rpa-ipa-update
cp rpa-ipa-update/SKILL.md ~/.claude/skills/rpa-ipa-update/
```

### Quick Start

```bash
# 1. Navigate to an IPA Studio project
cd /path/to/your-ipa-project

# 2. Extract code nodes
python3 path/to/extract_nodes.py extract . --force

# 3. Trigger skill in Claude Code:
#    "/rpa-ipa-analyzer --depth standard ."  (full analysis)
#    "/rpa-ipa-analyzer --depth quick ."     (architecture overview)
#    "/rpa-ipa-analyzer --depth deep ."      (with 6-lens audit)
#    "/rpa-ipa-audit ."                      (audit only)
```

## Directory Structure

```
rpa-ipa-analyzer/
├── README.md / README.en.md    # Documentation
├── CHANGELOG.md                 # Version history
├── LICENSE                      # MIT
├── rpa-ipa-analyzer/            # Full analysis skill
│   ├── SKILL.md                 # Main instructions ( 4-layer model)
│   ├── SKILL_audit.md           # Independent audit command
│   ├── VERSION                   
│   ├── component_usage_counts.json  # Cross-project component stats
│   ├── promotion_config.json    # Promotion strategy config
│   ├── scripts/
│   │   ├── extract_nodes.py     # CLI entry (extract/list/stats/trace/compare)
│   │   ├── component_promotion.py
│   │   ├── version_check.py
│   │   └── _extract/            # 10-module extraction library
│   ├── references/
│   │   ├── ipa_format.md        # 40+ component field definitions
│   │   ├── report_template.md   # Report template (quick/deep annotated)
│   │   ├── audit_swarm.md       # 6-agent parallel audit prompts
│   │   ├── patterns_universal.md  # 5 universal design patterns (checklist format)
│   │   └── patterns_domain.md     # Domain reference cases
│   └── evals/
│       ├── evals.json
│       ├── assertions.py
│       ├── evals_runner.py
│       └── golden/baseline_project/
├── rpa-ipa-update/              # Incremental update skill
│   └── SKILL.md                 # synced (variable change detection)
└── platforms/                   # Platform adapters
    ├── codex/codex.yaml
    └── openclaw/skill.yaml
```

## Requirements

- Python 3.8+ (stdlib only: `json`, `re`, `hashlib`, `pathlib`, `argparse`, `dataclasses`, `collections.deque`)
- IPA Studio project files (`project.json`, flow JSON, `globalParams.json`, `processResult.json`)

## License

MIT License — see [LICENSE](LICENSE)
