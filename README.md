# IPA Studio RPA Skills

Claude Code / OpenAI Codex / OpenClaw 通用的 IPA Studio RPA 项目分析与增量更新技能集合。

## 包含技能

| 技能 | 用途 | 触发词 |
|------|------|--------|
| [rpa-ipa-analyzer](./rpa-ipa-analyzer/) | 全量分析 RPA 项目，生成结构化报告 | "分析这个 RPA 项目" |
| [rpa-ipa-update](./rpa-ipa-update/) | 代码变更后增量更新报告（仅重分析变更节点） | "更新分析报告""增量更新" |

**典型工作流**：首次用 `rpa-ipa-analyzer` 生成完整报告 → 后续代码修改用 `rpa-ipa-update` 局部更新。

## 安装

### Claude Code

```bash
git clone https://github.com/xiuerhuahuazi/rpa-ipa-analyzer.git
cd rpa-ipa-analyzer

# 安装 analyzer
mkdir -p ~/.claude/skills/rpa-ipa-analyzer
cp rpa-ipa-analyzer/SKILL.md ~/.claude/skills/rpa-ipa-analyzer/
cp -r rpa-ipa-analyzer/scripts/ ~/.claude/skills/rpa-ipa-analyzer/
cp -r rpa-ipa-analyzer/references/ ~/.claude/skills/rpa-ipa-analyzer/

# 安装 update
mkdir -p ~/.claude/skills/rpa-ipa-update
cp rpa-ipa-update/SKILL.md ~/.claude/skills/rpa-ipa-update/
cp -r rpa-ipa-update/scripts/ ~/.claude/skills/rpa-ipa-update/
```

### OpenAI Codex

```bash
# analyzer
mkdir -p ~/.codex/skills/rpa-ipa-analyzer
cp rpa-ipa-analyzer/SKILL.md rpa-ipa-analyzer/scripts/ rpa-ipa-analyzer/references/ ~/.codex/skills/rpa-ipa-analyzer/
cp rpa-ipa-analyzer/platforms/codex/codex.yaml ~/.codex/skills/rpa-ipa-analyzer/

# update
mkdir -p ~/.codex/skills/rpa-ipa-update
cp rpa-ipa-update/SKILL.md rpa-ipa-update/scripts/ ~/.codex/skills/rpa-ipa-update/
```

### OpenClaw

```bash
# analyzer
mkdir -p ~/.openclaw/skills/rpa-ipa-analyzer
cp rpa-ipa-analyzer/SKILL.md rpa-ipa-analyzer/scripts/ rpa-ipa-analyzer/references/ ~/.openclaw/skills/rpa-ipa-analyzer/
cp rpa-ipa-analyzer/platforms/openclaw/skill.yaml ~/.openclaw/skills/rpa-ipa-analyzer/

# update
mkdir -p ~/.openclaw/skills/rpa-ipa-update
cp rpa-ipa-update/SKILL.md rpa-ipa-update/scripts/ ~/.openclaw/skills/rpa-ipa-update/
```

## 快速开始

```bash
# 1. 进入 IPA Studio 项目目录
cd /path/to/your-ipa-project

# 2. 全量分析（首次）
#    在 Claude Code 中说："分析这个 RPA 项目"
#    输出：分析报告_{项目名}.md

# 3. 增量更新（代码修改后）
#    在 Claude Code 中说："更新分析报告"
#    仅重分析变更节点，局部更新报告
```

## 目录结构

```
rpa-ipa-analyzer/
├── README.md                    # 本文件
├── LICENSE
├── rpa-ipa-analyzer/            # 全量分析技能
│   ├── SKILL.md                 # 技能主文件
│   ├── scripts/
│   │   └── extract_nodes.py     # 代码节点提取工具
│   ├── references/
│   │   ├── ipa_format.md        # IPA Studio JSON 格式参考
│   │   ├── report_template.md   # 报告结构模板
│   │   ├── audit_swarm.md       # 并行审计 agent prompt
│   │   └── design_patterns.md   # RPA 设计模式库
│   └── evals/
│       └── evals.json           # 评估测试用例
├── rpa-ipa-update/              # 增量更新技能
│   ├── SKILL.md                 # 技能主文件
│   └── scripts/
│       └── extract_nodes.py     # 代码节点提取工具（共享）
└── platforms/                   # 平台适配器（仅 Codex/OpenClaw）
```

## 运行要求

- Python 3.8+（仅标准库，无外部依赖）
- IPA Studio 项目文件（`project.json` + 流程 JSON）

## 许可证

MIT License — 详见 [LICENSE](LICENSE)
