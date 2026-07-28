# IPA Studio RPA Skills

Claude Code / OpenAI Codex / OpenClaw 通用的 IPA Studio RPA 项目分析与增量更新技能集合。

## 包含技能

| 技能 | 用途 | 触发词 |
|------|------|--------|
| [rpa-ipa-analyzer](./rpa-ipa-analyzer/) | 全量分析 RPA 项目，生成结构化报告 | "分析这个 RPA 项目" |
| [rpa-ipa-update](./rpa-ipa-update/) | 代码变更后增量更新报告（仅重分析变更节点） | "更新分析报告""增量更新" |
| [rpa-ipa-audit](./rpa-ipa-analyzer/SKILL_audit.md) | 6 维并行代码审计（独立命令） | "审计""audit""代码安全检查" |

**典型工作流**：首次用 `rpa-ipa-analyzer` 生成完整报告 → 后续代码修改用 `rpa-ipa-update` 局部更新 → 发布前用 `rpa-ipa-audit` 审计。

## 新特性

- **3.1.0 Token 优化**：extract-first（禁读原始 flow JSON）→ `skeleton` 生成结构 → LLM 只写业务语义；§2.2 代码外置；`diff`/`patch` 增量更新；审计默认按 hash 增量
- **能力分层模型**：4 个能力层（层0自校准→层1项目建模→层2代码与业务分析→层3产物生成）
- **三级分析深度**：quick / standard / deep，自动判定项目规模并推荐深度
- **自适应组件升级**：`component_usage_counts.json` 跨项目累积，触发 promotion
- **edges + 变量血缘**：`trace` 子命令追踪生产者→消费者
- **独立审计** `/rpa-ipa-audit`：按需触发；3.1 起默认增量
- **回归测试**：golden manifest diff + 结构化断言

## 安装

### Claude Code

```bash
git clone https://github.com/xiuerhuahuazi/rpa-ipa-analyzer.git
cd rpa-ipa-analyzer

# 安装 analyzer（必须含 scripts/）
mkdir -p ~/.claude/skills/rpa-ipa-analyzer
cp -r rpa-ipa-analyzer/* ~/.claude/skills/rpa-ipa-analyzer/

# 安装 update
mkdir -p ~/.claude/skills/rpa-ipa-update
cp rpa-ipa-update/SKILL.md ~/.claude/skills/rpa-ipa-update/

# 可选：独立审计 skill
mkdir -p ~/.claude/skills/rpa-ipa-audit
cp rpa-ipa-analyzer/SKILL_audit.md ~/.claude/skills/rpa-ipa-audit/SKILL.md
```

### OpenAI Codex

```bash
mkdir -p ~/.codex/skills/rpa-ipa-analyzer
cp -r rpa-ipa-analyzer/* ~/.codex/skills/rpa-ipa-analyzer/
cp platforms/codex/codex.yaml ~/.codex/skills/rpa-ipa-analyzer/
```

### OpenClaw

```bash
mkdir -p ~/.openclaw/skills/rpa-ipa-analyzer
cp -r rpa-ipa-analyzer/* ~/.openclaw/skills/rpa-ipa-analyzer/
cp platforms/openclaw/skill.yaml ~/.openclaw/skills/rpa-ipa-analyzer/
```

### Cursor

```bash
mkdir -p ~/.cursor/skills/rpa-ipa-analyzer
cp -r rpa-ipa-analyzer/* ~/.cursor/skills/rpa-ipa-analyzer/
mkdir -p ~/.cursor/skills/rpa-ipa-update
cp rpa-ipa-update/SKILL.md ~/.cursor/skills/rpa-ipa-update/
```

## 快速开始

```bash
cd /path/to/your-ipa-project
SK=~/.claude/skills/rpa-ipa-analyzer   # 或 ~/.cursor/skills/rpa-ipa-analyzer

# 确定性抽取 + 报告骨架（零 LLM token）
python3 $SK/scripts/extract_nodes.py extract . --force
python3 $SK/scripts/extract_nodes.py skeleton . --depth standard

# 再在 Agent 中说：
#   "/rpa-ipa-analyzer --depth standard ."
#   "/rpa-ipa-analyzer --depth quick ."
#   "/rpa-ipa-update 更新分析报告"
#   "/rpa-ipa-audit ."                 # 默认增量；全量加 --full
```

## 目录结构

```
rpa-ipa-analyzer/
├── README.md                    # 本文件
├── README.en.md                 # English version
├── CHANGELOG.md                 # 版本历史
├── LICENSE                      # MIT
├── .gitignore
├── rpa-ipa-analyzer/            # 全量分析技能
│   ├── SKILL.md                 # 技能主文件（ 4 层模型）
│   ├── SKILL_audit.md           # 独立审计命令
│   ├── VERSION                   # 版本号
│   ├── component_usage_counts.json  # 跨项目组件使用量统计
│   ├── promotion_config.json    # 自适应升级策略配置
│   ├── scripts/
│   │   ├── extract_nodes.py     # CLI：extract/list/stats/trace/compare/diff/skeleton/patch
│   │   ├── diff_nodes.py        # 增量 hash/变量对比
│   │   ├── patch_report.py      # 按 #### 节点 N{n} 补丁报告
│   │   ├── generate_skeleton.py # 无 LLM 生成报告骨架
│   │   ├── component_promotion.py
│   │   ├── version_check.py
│   │   └── _extract/            # 提取核心库（含 snapshot.py）
│   ├── references/
│   │   ├── ipa_format.md        # IPA Studio JSON 格式参考（40+ 组件字段定义）
│   │   ├── report_template.md   # 报告结构模板（含 quick/deep 模式标注）
│   │   ├── audit_swarm.md       # 6 维并行审计 agent prompt
│   │   ├── patterns_universal.md   # 5 个通用设计模式（Checklist 格式）
│   │   └── patterns_domain.md      # 领域参考案例（仅供人类阅读）
│   └── evals/
│       ├── evals.json           # 评估测试用例
│       ├── assertions.py        # 断言库（manifest diff + promotion 检查）
│       ├── evals_runner.py      # 运行器（--all / --regenerate-golden）
│       └── golden/baseline_project/  # 黄金基准项目（6 个 JSON）
├── rpa-ipa-update/              # 增量更新技能
│   └── SKILL.md                 # 技能主文件（同步，含变量变化检测）
└── platforms/                   # 平台适配器
    ├── codex/codex.yaml
    └── openclaw/skill.yaml
```

## 运行要求

- Python 3.8+（仅标准库，零外部依赖）
- IPA Studio 项目文件（`project.json` + 流程 JSON）

## 许可证

MIT License — 详见 [LICENSE](LICENSE)
