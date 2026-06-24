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

- **能力分层模型**：分析流程从 7 个 Phase 升级为 4 个能力层（层0自校准→层1项目建模→层2代码与业务分析→层3产物生成），依赖语义更清晰
- **三级分析深度**：quick（宏观架构）/ standard（完整分析）/ deep（含 6 维并行审计），自动判定项目规模并推荐深度
- **自适应组件升级**：`component_usage_counts.json` 跨项目累积组件使用量，自动触发 promotion 更新 `ipa_format.md`
- **edges 收集 + 变量血缘追踪**：`extract_nodes.py` 新增 edges 提取和 `trace` 子命令，可追踪变量从生产者到消费者的完整链路
- **通用设计模式库**：14 个模式拆为 5 个通用 Checklist 模式 + 5 个领域参考案例，分析时自动匹配标注
- **独立审计命令 `/rpa-ipa-audit`**：6 维并行代码审计按需触发，零默认成本
- **`@desc` 自动填充**：提取的代码文件不再使用 `[待补充]` 占位符，自动生成有意义的描述
- **回归测试框架**：golden manifest diff + 结构化断言，Evals 50/50 PASS

## 安装

### Claude Code

```bash
git clone https://github.com/xiuerhuahuazi/rpa-ipa-analyzer.git
cd rpa-ipa-analyzer

# 安装 analyzer
mkdir -p ~/.claude/skills/rpa-ipa-analyzer
cp -r rpa-ipa-analyzer/* ~/.claude/skills/rpa-ipa-analyzer/

# 安装 update
mkdir -p ~/.claude/skills/rpa-ipa-update
cp rpa-ipa-update/SKILL.md ~/.claude/skills/rpa-ipa-update/
```

### OpenAI Codex

```bash
mkdir -p ~/.codex/skills/rpa-ipa-analyzer
cp -r rpa-ipa-analyzer/* ~/.codex/skills/rpa-ipa-analyzer/
cp rpa-ipa-analyzer/platforms/codex/codex.yaml ~/.codex/skills/rpa-ipa-analyzer/
```

### OpenClaw

```bash
mkdir -p ~/.openclaw/skills/rpa-ipa-analyzer
cp -r rpa-ipa-analyzer/* ~/.openclaw/skills/rpa-ipa-analyzer/
cp rpa-ipa-analyzer/platforms/openclaw/skill.yaml ~/.openclaw/skills/rpa-ipa-analyzer/
```

## 快速开始

```bash
# 1. 进入 IPA Studio 项目目录
cd /path/to/your-ipa-project

# 2. 提取代码节点
python3 ~/.claude/skills/rpa-ipa-analyzer/scripts/extract_nodes.py extract . --force

# 3. 在 Claude Code 中说：
#    "/rpa-ipa-analyzer --depth standard ."  （完整分析）
#    "/rpa-ipa-analyzer --depth quick ."     （快速概览，大项目推荐）
#    "/rpa-ipa-analyzer --depth deep ."      （含 6 维审计，发布前审查）

# 4. 独立审计（可选）：
#    "/rpa-ipa-audit ."

# 5. 增量更新（代码修改后）：
#    "/rpa-ipa-update 更新分析报告"
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
│   ├── SKILL.md                 # 技能主文件（v3.0.0 4 层模型）
│   ├── SKILL_audit.md           # 独立审计命令
│   ├── VERSION                   # 版本号
│   ├── component_usage_counts.json  # 跨项目组件使用量统计
│   ├── promotion_config.json    # 自适应升级策略配置
│   ├── scripts/
│   │   ├── extract_nodes.py     # CLI 入口（extract/list/stats/trace/compare 子命令）
│   │   ├── component_promotion.py  # 组件升级工具
│   │   ├── version_check.py     # GitHub 版本检查
│   │   └── _extract/            # 提取核心库（10 个模块）
│   │       ├── __init__.py       # 导出 extract_project, ExtractResult
│   │       ├── result_types.py  # NodeMeta, FlowEdge, ExtractResult 数据类
│   │       ├── core.py          # safe_name, code_hash, find_param 等工具函数
│   │       ├── extractors.py    # Python/JS 节点提取器
│   │       ├── edges.py         # edges 收集与邻接表构建
│   │       ├── flows.py         # 流程文件递归提取（含嵌套块）
│   │       ├── headers.py       # @node 头生成（含 @desc 自动填充）
│   │       ├── duplicates.py    # 重复代码检测 + 跨项目共享检测
│   │       ├── counts.py        # 组件使用量统计（含 confidence 计算）
│   │       └── manifest.py      # extract_project 主编排
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
│   └── SKILL.md                 # 技能主文件（v3.0.0 同步，含变量变化检测）
└── platforms/                   # 平台适配器
    ├── codex/codex.yaml
    └── openclaw/skill.yaml
```

## 运行要求

- Python 3.8+（仅标准库，零外部依赖）
- IPA Studio 项目文件（`project.json` + 流程 JSON）

## 许可证

MIT License — 详见 [LICENSE](LICENSE)
