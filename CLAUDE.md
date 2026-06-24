## 项目约定

### 分支策略
- `main` — 默认分支，受保护，通过 PR 合并
- `dev` — 开发分支
- `feat/*` / `fix/*` / `chore/*` — 功能/修复/杂务分支，合并后删除

### 版本管理
- 遵循 Keep a Changelog 格式（Breaking → Added → Changed → Fixed → Removed）
- Release Drafter 自动生成 GitHub Release 草稿（仅 main 分支 push 时触发）
- 版本号解析：`breaking` label → major，`feature`/`enhancement` → minor，其余 → patch

### CI
- 触发：push/PR 到 main/dev，md/doc 变更不触发
- 矩阵：Python 3.8–3.12
- 流程：find 自发现 → golden baseline 检测 → evals_runner.py --all
- 语法检查：find . -name *.py | while python -m py_compile

### 发布流程
1. PR 合并到 main → Release Drafter 更新草稿
2. 手动检查草稿 → 编辑 CHANGELOG.md 确认 → 发布
3. 发布后更新 VERSION 文件

### 安装路径
- Claude Code: ~/.claude/skills/rpa-ipa-analyzer/
- rpa-ipa-update: ~/.claude/skills/rpa-ipa-update/
- 零外部依赖（Python 3.8+ 标准库）

### 跨平台
- 支持 Claude Code / OpenAI Codex / OpenClaw
- CI 使用 sys.executable 而非 python.exe（兼容 Linux）
- 代码兼容 Python 3.8–3.12（避免 3.9+ 特性如 str.removesuffix）
