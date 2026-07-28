---
name: rpa-ipa-update
description: IPA Studio RPA 增量更新——修改代码后最小化更新分析报告。比对 code_hash 定位变更节点，仅重分析变更部分。触发词："更新分析报告""增量更新""代码变更后更新报告""只更新变更部分"。
---

# IPA Studio RPA 增量更新器

只更新报告中**受影响章节**。依赖 `rpa-ipa-analyzer` 的 `scripts/`（`extract` / `diff` / `patch` / `trace`）。

`{SKILL_ROOT}` = `rpa-ipa-analyzer` 安装目录。

## Token 铁律

1. **禁止**把整份 `分析报告_*.md` 读进上下文再重写。
2. 只读：`diff` 输出的变更列表 + 变更节点的 `N*.py|js` + 报告中对应 `#### 节点 N{n}` 片段（可用 grep）。
3. 用 `patch` 按锚点写入；业务描述写短文，**不贴完整源码**。

## 前置

- 已有 `分析报告_{project_name}.md`
- 已有 `.extracted_nodes/manifest.json`（首次请先 `/rpa-ipa-analyzer`）

## 工作流

```bash
# 1) --force 提取（自动保存 previous_manifest + hash_snapshot）
python {SKILL_ROOT}/scripts/extract_nodes.py extract {project_path} --force

# 2) 对比
python {SKILL_ROOT}/scripts/extract_nodes.py diff {project_path} --json --out {project_path}/.extracted_nodes/changed.json

# 3) 对每个变更节点：读 N*.py → 写短 Markdown（含 #### 节点 N{n}: 标题）→ patch
python {SKILL_ROOT}/scripts/extract_nodes.py patch {report} --node {n} --from-file /tmp/node_N{n}.md

# 4) 更新元信息
python {SKILL_ROOT}/scripts/extract_nodes.py patch {report} --meta "分析日期：{date}（增量更新） | 变更节点：N{n1}, N{n2}"

# 5) 刷新快照为当前（便于下次 diff）
python -c "from pathlib import Path; import json,sys; sys.path.insert(0,r'{SKILL_ROOT}/scripts'); from _extract.snapshot import write_hash_snapshot; m=json.loads(Path('{project_path}/.extracted_nodes/manifest.json').read_text(encoding='utf-8')); write_hash_snapshot(m, Path('{project_path}/.extracted_nodes/hash_snapshot.txt'))"
```

若已改代码但无旧快照：`extract --force` 后若 `diff` 报无快照，先全量分析或用 `previous_manifest.json`。

## 变更 → 章节

| 变更 | 更新 |
|------|------|
| 代码 hash 变 | §2.2 该节点（patch）；I/O 变则 §4 + `trace` |
| 新增/删除节点 | §1.2 + §2.2 patch/delete + 附录 B；结构大变 → 全量 analyzer |
| 仅变量映射变 | §2.2 上下游 + §4；`trace --direction up/down` |
| globalParams 变 | §3 |

## 增量 vs 全量

| 条件 | 决策 |
|------|------|
| `changed.json` 的 `recommend=incremental`（delta≤5） | 增量 patch |
| delta>5 或子流程增删 | 建议 `/rpa-ipa-analyzer` |
| patch 后章节断裂 | 回退全量 |

## 异常

| 场景 | 处理 |
|------|------|
| 无 snapshot | 提示先全量或检查 `previous_manifest.json` |
| extract 失败 | 确认 CLI 子命令语法（v3+） |
| diff=0 但用户坚称改了 | 查流程 JSON mtime，必要时再 `--force` |
