# rpa-ipa-analyzer

分析 IPA Studio RPA 项目，生成包含 Mermaid 流程图的综合性业务与代码分析报告。

## 概述

本技能可分析 IPA Studio RPA 项目并生成专业分析报告，涵盖：

- 项目架构与工作流可视化（Mermaid 图表）
- 从 Python（`script_python_execute`）和 JavaScript（`browser_inject_js_code`）节点中提取代码
- 业务逻辑解读与领域术语表
- 端到端数据流向映射
- 风险评估与优化建议
- 跨项目代码去重

## 支持的项目类型

| 类型 | 说明 | 关键组件 |
|------|------|----------|
| **数据处理型** | Excel/CSV 操作、pandas 工作流 | `script_python_execute`、`log_task` |
| **Web 自动化型** | 浏览器交互、JS 注入 | `browser_inject_js_code`、`mouse_single_click` |
| **混合型** | 同时包含以上两种模式 | 多种组件类型 |

---

## 安装

### 前置条件

- **Python 3.8+**（仅使用标准库，无需 pip 安装）
- IPA Studio 项目文件（`project.json`、流程 JSON 文件）
- 至少一个受支持的 AI 编程平台（参见[平台配置](#平台配置)）

### 第一步：克隆仓库

```bash
git clone https://github.com/xiuerhuahuazi/rpa-ipa-analyzer.git
```

### 第二步：平台配置

> **注意：** 本仓库包含面向多平台的文件及仓库元数据。请仅复制你所用平台实际需要的文件。下表列出了各平台所需的文件。

#### 各平台文件对照表

| 文件 | Claude Code | OpenAI Codex | OpenClaw |
|------|:-----------:|:------------:|:--------:|
| `SKILL.md` | ✅ 必需 | ✅ 必需 | ✅ 必需 |
| `scripts/` | ✅ 必需 | ✅ 必需 | ✅ 必需 |
| `references/` | ✅ 必需 | ✅ 必需 | ✅ 必需 |
| `evals/` | ✅ 可选 | ❌ 不需要 | ❌ 不需要 |
| `platforms/codex/` | ❌ 不需要 | ✅ 必需 | ❌ 不需要 |
| `platforms/openclaw/` | ❌ 不需要 | ❌ 不需要 | ✅ 必需 |
| `README.md` | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |
| `LICENSE` | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |
| `CHANGELOG.md` | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |
| `.gitignore` | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |
| `requirements.txt` | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |

仓库专属文件（`README.md`、`LICENSE`、`CHANGELOG.md`、`.gitignore`、`requirements.txt`）属于项目元数据——任何平台运行时均不会使用，安装技能时应排除。

#### Claude Code

```bash
# 仅复制必要文件：
mkdir -p ~/.claude/skills/rpa-ipa-analyzer
cp SKILL.md ~/.claude/skills/rpa-ipa-analyzer/
cp -r scripts/ ~/.claude/skills/rpa-ipa-analyzer/
cp -r references/ ~/.claude/skills/rpa-ipa-analyzer/
cp -r evals/ ~/.claude/skills/rpa-ipa-analyzer/   # 可选
```

验证安装：
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

## 快速开始

```bash
# 1. 进入 IPA Studio 项目目录
cd /path/to/your-ipa-project

# 2. 运行提取脚本，准备代码节点
python3 /path/to/rpa-ipa-analyzer/scripts/extract_nodes.py . --force

# 3. 在 Claude Code（或其他平台）中触发技能
#    在 Claude Code 中，只需说：
#    "请分析当前这个 IPA Studio RPA 项目"
```

**输出**：在项目目录中生成 `分析报告_{项目名}.md`。

### 报告输出结构示例

```
分析报告_MyProject.md
├── 一、整体工作流分析
│   ├── 1.1 项目架构概览 (Mermaid 流程图)
│   ├── 1.2 主流程完整路径
│   ├── 1.3 条件分支与路由逻辑
│   └── 1.4 子流程调用关系
├── 二、节点级详细拆解
│   ├── 2.1 阶段划分与概述
│   ├── 2.2 代码节点逐一详解（逐节点分析）
│   └── 2.3 UI 自动化节点分析
├── 三、全局参数与配置分析
├── 四、业务逻辑深度解读
│   ├── 4.1 整体业务目标
│   ├── 4.2 核心业务概念（领域术语表）
│   ├── 4.3 数据流转全路径（ASCII 图表）
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

## 目录结构

```
rpa-ipa-analyzer/
├── SKILL.md              # [核心] 技能主文件——所有平台必需
├── scripts/
│   └── extract_nodes.py  # [核心] 代码提取工具——所有平台必需
├── references/
│   ├── ipa_format.md     # [核心] IPA Studio JSON 格式参考
│   └── report_template.md # [核心] 报告结构模板
├── evals/
│   └── evals.json        # [仅 Claude Code] 评估测试用例（可选）
├── platforms/
│   ├── codex/
│   │   └── codex.yaml    # [仅 Codex] 平台适配器
│   └── openclaw/
│       └── skill.yaml    # [仅 OpenClaw] 平台适配器
├── README.md             # [仓库专用] 项目文档（中文）——不安装
├── README.en.md          # [仓库专用] 项目文档（英文）——不安装
├── LICENSE               # [仓库专用] MIT 许可证——不安装
├── CHANGELOG.md          # [仓库专用] 版本记录——不安装
├── requirements.txt      # [仓库专用] 依赖声明——不安装（无外部依赖）
└── .gitignore            # [仓库专用] Git 配置——不安装
```

**图例说明：**
- `[核心]` — 所有平台必需，始终复制这些文件。
- `[仅 Claude Code]` / `[仅 Codex]` / `[仅 OpenClaw]` — 平台专属，仅对应平台复制。
- `[仓库专用]` — 项目元数据，任何平台安装时均不复制。

---

## 核心特性

### 功能标签系统
自动将代码节点分类为 BOILERPLATE（样板代码）、SKELETON（骨架代码）、GLUE（胶水代码）或 BUSINESS（业务代码），避免对基础设施代码进行重复分析。

### JavaScript 注入分类
将每个 `browser_inject_js_code` 节点归入 7 个类别之一：DOM 导航、表单填充、表单读取、状态检测、数据提取、页面清理、按钮点击。

### 递归代码块遍历
从嵌套的 `process_function_block` 结构中提取代码节点，支持最多 3 层深度。

### 跨项目去重
通过 MD5 哈希检测跨项目的相同代码，实现共享基础设施识别。

### 14 种 RPA 设计模式
从基于模板的 Excel 生成到验证码自动识别——识别到的设计模式将自动标注在报告中。

---

## 运行要求

- Python 3.8+（仅标准库——`json`、`re`、`hashlib`、`pathlib`、`argparse`）
- IPA Studio 项目文件：`project.json`、流程 JSON 文件、`globalParams.json`、`processResult.json`

---

## 常见问题

| 问题 | 解决方法 |
|------|----------|
| 找不到 `project.json` | 确保在 IPA Studio 项目根目录下运行 |
| 找不到流程文件 | 检查 `project.json` 中的 `process_list` 路径——文件必须相对于项目根目录存在 |
| JSON 解码错误 | IPA Studio 导出 UTF-8 编码的 JSON。检查文件编码是否为 GBK/GB2312 |
| 大文件（4MB+）处理缓慢 | 技能对大型文件使用并行 Explore 代理，请确保有足够的上下文窗口 |
| `.extracted_nodes/` 内容过时 | 流程文件变更后，运行 `extract_nodes.py --force` 重新生成 |
| Python 版本过旧 | 需要 Python 3.8+ 以支持 `pathlib` 和类型提示 |
| 技能未触发 | 确认 SKILL.md 位于正确的平台技能目录中 |

---

## 平台兼容性

| 平台 | 状态 | 备注 |
|------|------|------|
| **Claude Code** | ✅ 原生支持 | YAML frontmatter 格式直接支持 |
| **OpenAI Codex** | ⚠️ 需要适配器 | 参见 [Codex 配置](#openai-codex)——需要 `codex.yaml` |
| **OpenClaw** | ⚠️ 需要适配器 | 参见 [OpenClaw 配置](#openclaw)——需要 `skill.yaml` |

核心分析逻辑（`extract_nodes.py` + 报告模板）与平台无关，仅技能注册机制因平台而异。

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)
