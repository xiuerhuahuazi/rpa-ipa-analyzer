# IPA Studio RPA Skills

Claude Code / Cursor / OpenAI Codex / OpenClaw 通用的 IPA Studio RPA 分析技能。

## 技能

| 技能 | 用途 |
|------|------|
| [rpa-ipa-analyzer](./skills/rpa-ipa-analyzer/) | **唯一**可安装技能：分析 / 增量更新 / 审计 |

三种模式（同一 skill，不要再装 update/audit 独立技能）：

| 模式 | 触发示例 | 产出 |
|------|----------|------|
| analyze | 「分析这个 RPA 项目」`/rpa-ipa-analyzer --depth standard` | `分析报告_*.md` |
| update | 「更新分析报告」「增量更新」 | 报告局部 patch |
| audit | 「审计」「代码安全检查」 | `AUDIT_REPORT.md` |

## 新特性（3.2）

- **单一技能**：合并原 `rpa-ipa-update` / `rpa-ipa-audit`，仓库改为 `skills/` 布局（对齐热门 skill 仓）
- **Token 优化**：extract → skeleton → LLM；§2.2 代码外置；`diff`/`patch` 增量
- **三级深度**：quick / standard / deep（deep 含审计）
- **edges + trace**、自适应组件 promotion、golden evals

## 安装

```bash
git clone https://github.com/xiuerhuahuazi/rpa-ipa-analyzer.git
cd rpa-ipa-analyzer

# Claude Code / Cursor（只装这一个目录）
mkdir -p ~/.claude/skills/rpa-ipa-analyzer
cp -r skills/rpa-ipa-analyzer/* ~/.claude/skills/rpa-ipa-analyzer/

mkdir -p ~/.cursor/skills/rpa-ipa-analyzer
cp -r skills/rpa-ipa-analyzer/* ~/.cursor/skills/rpa-ipa-analyzer/
```

Codex / OpenClaw：同样只复制 `skills/rpa-ipa-analyzer/*`，再分别加上 `platforms/codex/codex.yaml` 或 `platforms/openclaw/skill.yaml`。

也可：`npx skills add xiuerhuahuazi/rpa-ipa-analyzer --skill rpa-ipa-analyzer`（若 CLI 已索引本仓）。

**迁移**：删除旧的 `~/.claude/skills/rpa-ipa-update` 与 `rpa-ipa-audit` 目录。

## 快速开始

```bash
cd /path/to/your-ipa-project
SK=~/.claude/skills/rpa-ipa-analyzer

python3 $SK/scripts/extract_nodes.py extract . --force
python3 $SK/scripts/extract_nodes.py skeleton . --depth standard

# Agent：
#   "/rpa-ipa-analyzer --depth standard ."     全量分析
#   "/rpa-ipa-analyzer 更新分析报告"            增量（模式 update）
#   "/rpa-ipa-analyzer 审计 ."                 审计（模式 audit）
```

## 目录结构

```
rpa-ipa-analyzer/                 # GitHub 仓库
├── skills/
│   └── rpa-ipa-analyzer/         # 唯一 Agent Skill
│       ├── SKILL.md              # analyze | update | audit
│       ├── VERSION
│       ├── scripts/              # extract/list/stats/trace/compare/diff/skeleton/patch
│       └── references/
├── evals/                        # 回归测试
├── platforms/                    # Codex / OpenClaw 适配
├── README.md
├── CHANGELOG.md
└── LICENSE
```

## 运行要求

- Python 3.8+（标准库）
- IPA Studio 项目（`project.json` + 流程 JSON）

## 许可证

MIT — 见 [LICENSE](LICENSE)
