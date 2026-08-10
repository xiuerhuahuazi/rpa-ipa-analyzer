# Changelog

## [Unreleased]

## [3.3.1] - 2026-08-10

### Added
- `SKILL.md` / `references/ipa_format.md`：**变量/参数铁律** — 流程域 `global_vars`、项目级 `globalParams.json`、节点入出参映射、子流程交换；出参 value 必须先登记否则运行失败。
- 明确 `apply` 不修改 `global_vars` / 映射字段；禁止把 Python 类写作出参。

## [3.3.0] - 2026-08-10

### Added

- `extract_nodes.py apply`：将 `.extracted_nodes` 中编辑后的 `N*.py|js` 精准写回对应 flow JSON 节点（`python_script` / `js_code`）。
- `_extract/apply.py`：剥离 `@node` 头、hash 比对、`--dry-run` / `--node` / `--file` / `--force`、写前 `bak_apply_*` 备份。
- Spec：`docs/superpowers/specs/2026-08-10-extract-nodes-apply.md`。

### Changed

- `SKILL.md`：Token 铁律增加「改代码走 apply」；版本 3.3.0。
