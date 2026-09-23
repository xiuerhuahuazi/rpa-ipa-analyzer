# IPA Studio RPA Skills

Claude Code / Cursor / OpenAI Codex / OpenClaw / DSH 通用的 IPA Studio RPA 分析技能。

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

## 新特性（3.3）

- **`apply` 写回**：编辑 `.extracted_nodes/N*.py|js` 后，用 `extract_nodes.py apply` 精准写回 flow JSON（剥离 `@node` 头、hash 跳过未变更、`bak_apply_*` 备份）
- 改代码优先走 apply，避免 Agent 整读/手改巨型流程 JSON

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

DSH：复制 `skills/rpa-ipa-analyzer/*` 到 DSH 的技能根 —— 全用户 `~/.agents/skills/rpa-ipa-analyzer/`，或仅单个工作区 `<workspace>/.agents/skills/rpa-ipa-analyzer/`（rank 更小，覆盖用户级）。DSH 会自动发现，无需重启。细节见 `skills/rpa-ipa-analyzer/DSH.md` 与 `platforms/dsh/dsh.yaml`。

也可：`npx skills add xiuerhuahuazi/rpa-ipa-analyzer --skill rpa-ipa-analyzer`（若 CLI 已索引本仓）。

**迁移**：删除旧的 `~/.claude/skills/rpa-ipa-update` 与 `rpa-ipa-audit` 目录。

## 快速开始

```bash
cd /path/to/your-ipa-project
SK=~/.claude/skills/rpa-ipa-analyzer

# 统一走启动器：自动解析 Python 3.8+ 并附加 -X utf8（Windows 用 scripts\rpa.cmd）
$SK/scripts/rpa.sh extract  . --force
$SK/scripts/rpa.sh skeleton . --depth standard

# 编辑 .extracted_nodes/N*.py 后写回流程 JSON
$SK/scripts/rpa.sh apply . --dry-run          # 预览
$SK/scripts/rpa.sh apply . --node 55          # 指定节点
# $SK/scripts/rpa.sh apply .                  # 只写 hash 有变更的节点

# Agent：
#   "/rpa-ipa-analyzer --depth standard ."     全量分析
#   "/rpa-ipa-analyzer 更新分析报告"            增量（模式 update）
#   "/rpa-ipa-analyzer 审计 ."                 审计（模式 audit）
```

> **不要**直接写 `python3 $SK/scripts/extract_nodes.py`。一是机器上可能没有可用的系统
> Python（Windows 上 `python` / `python3` 常是 Microsoft Store 桩，执行即 `exit 9009`）；
> 二是不加 `-X utf8` 时 Windows 会用 GBK 写 stdout，中文节点名会以乱码进入 Agent 上下文，
> **且退出码仍为 0**，报告会静默错乱。启动器同时解决这两点。

## 目录结构

```
rpa-ipa-analyzer/                 # GitHub 仓库
├── skills/
│   └── rpa-ipa-analyzer/         # 唯一 Agent Skill
│       ├── SKILL.md              # analyze | update | audit
│       ├── DSH.md                # DSH 适配说明
│       ├── VERSION
│       ├── scripts/              # extract/list/stats/trace/compare/diff/skeleton/patch/apply
│       │   ├── rpa.cmd           # 跨平台启动器（Windows）
│       │   └── rpa.sh            # 跨平台启动器（POSIX）
│       └── references/
├── docs/superpowers/specs/       # 设计规格（含 apply）
├── evals/                        # 回归测试
├── platforms/                    # Codex / OpenClaw / DSH 适配
├── README.md
├── CHANGELOG.md
└── LICENSE
```

## 运行要求

- Python 3.8+（标准库）
- IPA Studio 项目（`project.json` + 流程 JSON）

## 许可证

MIT — 见 [LICENSE](LICENSE)
