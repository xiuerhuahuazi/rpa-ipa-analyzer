# Changelog

## [Unreleased]

_暂无_

## [3.3.4] - 2026-11-17

### Added

- `extract_nodes.py check-mermaid`：报告图表的静态检查器（纯标准库，Python 3.8 可用，不联网）。边标签里的 `( ) [ ] { } ;`、节点/子图标签未加引号、`-.文字.->` 形式的虚线边、围栏未闭合等判 ERROR；`--strict` 让 WARN 也失败；`--self-test` 内置 12 条回归用例（两次真实渲染事故的写法都锁死）。
- `references/mermaid_check.md`：两次渲染事故复盘、E1–E11 / W1–W7 规则表、图尺寸经验（宽度 ≤ ~1300px，节点 >20 或 `LR` >12 就拆图）、可选的「同版本 mermaid + 无头浏览器真渲染」配方。
- DSH 平台适配：`DSH.md`（加载契约、安装位置、三个环境坑）、`scripts/rpa.cmd` / `scripts/rpa.sh` 跨平台启动器（自动解析 Python 3.8+ 解释器并固定附加 `-X utf8`）。
- `extract_nodes.py mapping` / `remove-node`：补丁节点入/出参映射与流程 `global_vars`（`apply` 明确不改这些字段；出参 value 必须是本流程已登记的 key，否则直接失败，`--ensure-global-var` 可顺手补登记）；删除孤立死节点，默认拒绝删除仍被引用的节点并列出引用来源。

### Fixed

- `_extract/flows.py`：嵌套 `process_function_block` 只展开一层——`block_data["blocks"]` 读出来却从未递归，二级及更深块内的节点**整块漏抽**。改为按 `blocks[]` 递归整棵块树（`visited` 防环），块名解析走「节点首个 property → 块 `name` → 块 id」兜底链（原先直接下标 `properties[0].params[0]`，参数为空会抛异常）。实测某真实项目由 98 个节点变为 214 个。
- `_extract/manifest.py`：落盘文件名里的所属块按 12 字符截断**整条层级路径**，二级块会得到 `_流` 这类不可读后缀；改为只取最内层块名（`parent_block` / `flow_file` 仍保留 `::` 全层级）。
- `_extract/manifest.py`：抽取出的 `N*.py|js` 在 Windows 上被写成 CRCRLF，导致「extract → 编辑 → apply」把成倍空行写回流程 JSON；改为 `newline=""` 写入。
- `generate_skeleton.py`：`§1.1` 的 mermaid 节点标签原先不加引号，流程名含括号/斜杠时整图解析失败；改为一律 `xxx["流程名"]`，并在写盘后跑一次静态自检。
- `generate_skeleton.py`：`globalParams.json` 为**顶层数组**时 §3.1 参数表恒为空；数组与 dict 两种形态都支持。
- `diff_nodes.py`：按 `seq` 比对导致增删节点后大面积误报；改为优先用 `previous_manifest.json` 按 `node_id` 比对（旧快照缺 id 时退回原逻辑并打印提示）。
- `SKILL.md`：`description` 里的 ASCII 冒号+空格（`Modes: `）在严格 YAML 解析器下是非法标量，会导致技能**静默不加载**；改为全角写法。
- `extract_nodes.py trace`：按流程变量名与脚本内变量名双命名空间匹配；不再把途经祖先误标为生产者；跨流程时给出桥接提示。

### Changed

- `SKILL.md`：新增「Mermaid 铁律」章节——边标签禁 `( ) [ ] { } ;` 且不要用引号包裹、节点/子图标签一律加引号、虚线边带文字只允许 `-. 文字 .->` 或 `-.->|文字|`、单图宽度 ≤ ~1300px 与拆图阈值、`stateDiagram` 用 `state "文案" as s0` 别名、定稿前 `check-mermaid` 必须 exit 0；「质量自检」同步。
- `SKILL.md`：Token 铁律新增「块可多层嵌套，级数不设限」，写明 `parent_block` 用 `::` 拼层级、落盘文件名只取最内层块名，并强调**重抽会重排序号**——`apply --node N` 与报告里的 N 号一律以当前 `manifest.json` 为准。
- `SKILL.md`：新增「第 0 步：解释器与调用」，脚本一律经启动器调用；新增 DSH 子代理映射表与 `mapping` / `remove-node` 用法。
- `references/report_template.md`：模板头部加 Mermaid 硬约束清单与校验命令。
- `DSH.md`：补「DSH 会渲染 markdown 里的图 → 语法错就是用户可见报错」与渲染器版本查法。
- 版本 **3.3.1 → 3.3.4**（`VERSION` / `SKILL.md` / `platforms/dsh/dsh.yaml`）。

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
