# Changelog

## [Unreleased]

### Added
- DSH 平台适配：`DSH.md` 说明加载契约、安装位置与三个环境坑；`scripts/rpa.cmd` / `scripts/rpa.sh` 跨平台启动器（自动解析 Python 3.8+，固定 `-X utf8`）。
- `extract_nodes.py mapping`：补丁节点入/出参映射与流程 `global_vars`（`apply` 不改这些字段）。出参 value 必须是本流程已登记的 `global_vars` key，否则直接失败，`--ensure-global-var` 可顺手补登记。
- `extract_nodes.py remove-node`：删除孤立死节点；默认拒绝删除仍被引用的节点并列出引用来源。

### Fixed
- `_extract/manifest.py`：抽取文件在 Windows 上被写成 CRCRLF，导致「extract → 编辑 → apply」把成倍空行写回流程 JSON。改为 `newline=""` 写入。
- `diff_nodes.py`：按 `seq` 比对导致增删节点后大面积误报；改为优先用 `previous_manifest.json` 按 `node_id` 比对。
- `generate_skeleton.py`：支持 `globalParams.json` 为**顶层数组**的形态（原先只处理 dict，导致 §3.1 恒为空）。
- `SKILL.md`：`description` 中的 ASCII 冒号+空格（`Modes: `）在严格 YAML 解析器下非法，技能会静默不加载；改为全角写法。
- `extract_nodes.py trace`：按流程变量名与脚本内变量名双命名空间匹配；不再把途经祖先误标为生产者；跨流程时给出桥接提示。

### Changed
- `SKILL.md`：新增「第 0 步：解释器与调用」，脚本一律经启动器调用；新增 DSH 子代理映射表；新增 `mapping` / `remove-node` 用法与 `diff` 比对基准说明。
- `apply` / `mapping` / `remove-node` 写盘统一 `newline=""`，行尾风格跨平台一致。

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
