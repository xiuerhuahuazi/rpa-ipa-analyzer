---
name: rpa-ipa-update
description: IPA Studio RPA 增量更新——修改代码后最小化更新分析报告。比对 code_hash 定位变更节点，仅重分析变更部分。触发词："更新分析报告""增量更新""代码变更后更新报告""只更新变更部分"。
---

# IPA Studio RPA 增量更新器

修改 Python/JS 代码后，只更新分析报告中**受影响的部分**。复用 `.extracted_nodes/` 的 `code_hash` 机制。

## 前置条件
- `分析报告_{project_name}.md` 已存在（由 `rpa-ipa-analyzer` 生成）
- `.extracted_nodes/manifest.json` 存在

## 工作流

### Step 1: 快照（如尚未改代码）

```bash
cd {project_path}
python3 -c "
import json; m=json.load(open('.extracted_nodes/manifest.json'))
for n in m['nodes']: print(f\"{n['seq']}|{n['show_name']}|{n['code_hash']}|{n['flow_file']}\")
" > .extracted_nodes/hash_snapshot.txt
```

已改代码则跳过。

### Step 2: 重新提取节点

```bash
python3 ~/.claude/skills/rpa-ipa-update/scripts/extract_nodes.py {project_path} --force
```

### Step 3: 对比哈希

```bash
python3 ~/.claude/skills/rpa-ipa-update/scripts/diff_hashes.py {project_path}
```

输出变更/新增/删除节点列表。若 `diff_hashes.py` 不存在，用内联 Python：
```python
import json
m=json.load(open('.extracted_nodes/manifest.json'))
new={n['seq']:n for n in m['nodes']}
old={}
try:
    for l in open('.extracted_nodes/hash_snapshot.txt'):
        p=l.strip().split('|',3); old[int(p[0])]={'name':p[1],'hash':p[2],'flow':p[3]}
except FileNotFoundError: print('无旧快照'); exit(1)
changed=[(s,i['name'],i['flow']) for s,i in old.items() if s in new and new[s]['code_hash']!=i['hash']]
added=[(s,n['show_name'],n['flow_file']) for s,n in new.items() if s not in old]
removed=[(s,i['name'],i['flow']) for s,i in old.items() if s not in new]
for label,lst in [('变更',changed),('新增',added),('删除',removed)]:
    print(f'{label}: {len(lst)}个'); [print(f'  N{s} [{f}] {n}') for s,n,f in lst]
```

### Step 4: 变更→报告映射

| 变更类型 | 更新章节 |
|---------|----------|
| Python节点代码变 | §2.2 该节点 + §4 数据血缘(若I/O变) + Appendix B |
| 新增/删除节点 | §1.2 流程图 + §2.2 + §4 + Appendix B |
| globalParams变 | §3 + 引用该参数的节点 |
| 变量映射变 | §2.2 上下游 + §4 |
| 流程结构变 | §1.2 + §1.3 |
| 新增/删除子流程 | §1 全量 + 建议走 `/rpa-ipa-analyzer` |

纯代码逻辑变更(最常见)：只改 §2.2 代码块+分析描述+§4 数据血缘。

### Step 5: 局部更新

读取 `.extracted_nodes/N{n}_*.py`，对比旧代码理解意图，重写 §2.2：
- 更新代码块、功能概述、数据结构、I/O 映射
- 检查连锁影响：输出变量变了→更新下游节点输入映射；新增 Excel→更新 §4.5

### Step 6: 更新元信息

```markdown
> 分析日期：{date}（增量更新） | 变更节点：N{n1}, N{n2} ...
```

### Step 7: 保存快照

同 Step 1 命令。

## 增量 vs 全量判断

| 条件 | 决策 |
|------|------|
| ≤5 节点变更，无流程结构变化 | **增量** |
| >5 节点变更 | 建议走 `/rpa-ipa-analyzer` 全量 |
| 新增/删除节点 | 增量 §1+§2.2，结构变化大则全量 |
| globalParams 变 | 增量 §3 |

## 异常处理

| 场景 | 处理 |
|------|------|
| 无旧快照 | 对比 manifest `extracted_at` 与 JSON mtime |
| extract_nodes.py 失败 | 检查 JSON 格式 |
| 识别为 0 变更但用户确认改了 | 对比 mtime，必要时整体重提取 |
| 章节断裂 | 回退全量 `/rpa-ipa-analyzer` |
