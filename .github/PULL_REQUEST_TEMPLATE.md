## PR 类型

- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 重构 (refactor)
- [ ] 文档 (docs)
- [ ] CI/构建 (build/ci)
- [ ] 破坏性变更 (breaking)

## 变更摘要

<!-- 简要描述此 PR 做了什么 -->

## 破坏性变更检查

本仓库 CHANGELOG 格式要求对破坏性变更明确标注。如有破坏性变更，请逐项列出：

- [ ] 无破坏性变更
- [ ] 有破坏性变更（请在下方说明）：

> 破坏性变更包括但不限于：
> - `manifest.json` schema 变更
> - `extract_nodes.py` CLI 命令语法变更
> - `SKILL.md` 指令层模型变更
> - `references/` 文件重命名/删除
> - 安装路径变更

## 测试

- [ ] `python evals/evals_runner.py --all` 全部通过
- [ ] `find . -name '*.py' -exec python -m py_compile {} \;` 语法检查通过
- [ ] 在真实 IPA 项目中手动验证（如有）

## 影响范围

- [ ] `skills/rpa-ipa-analyzer/SKILL.md`（技能指令：analyze/update/audit）
- [ ] `scripts/extract_nodes.py` / `scripts/_extract/`（提取引擎）
- [ ] `references/`（参考文件）
- [ ] `evals/`（测试框架）
- [ ] 仅文档

## Checklist

- [ ] 遵循现有代码风格
- [ ] 公共 API 变更反映在 `CHANGELOG.md`
- [ ] `code_hash` 逻辑未受影响（或已说明影响）
- [ ] 向后兼容旧 `manifest.json` schema（或已升级 schema version）
