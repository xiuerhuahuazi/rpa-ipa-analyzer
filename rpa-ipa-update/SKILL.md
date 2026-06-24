---
name: rpa-ipa-update
description: IPA Studio RPA 增量更新——修改代码后最小化更新分析报告。比对 code_hash 定位变更节点，仅重分析变更部分。触发词："更新分析报告""增量更新""代码变更后更新报告""只更新变更部分"。
---

# IPA Studio RPA 增量更新器

修改 Python/JS 代码后，只更新分析报告中**受影响的部分**。复用 `.extracted_nodes/` 的 `code_hash` 机制。

## 前置条件
- `分析报告_{project_name}.md` 已存在（由 `rpa-ipa-analyzer` 生成）
- `.extracted_nodes/manifest.json` 存在
- `rpa-ipa-analyzer` 已安装（本技能依赖其 `scripts/extract_nodes.py`）

## 工作流

### Step 1: 快照（如尚未改代码）

```bash
cd {project_path}
python3 -c "
import json
m = json.load(open('.extracted_nodes/manifest.json', encoding='utf-8'))
for n in m['nodes']:
    print(f\"{n['seq']}|{n['show_name']}|{n['code_hash']}|{n['flow_file']}|{json.dumps(n.get('input_vars',{}), ensure_ascii=False)}|{json.dumps(n.get('output_vars',{}), ensure_ascii=False)}\")
" > .extracted_nodes/hash_snapshot.txt
```

已改代码则跳过。

### Step 2: 重新提取节点

```bash
python3 ~/.claude/skills/rpa-ipa-analyzer/scripts/extract_nodes.py extract {project_path} --force
```

### Step 3: 对比哈希 + 变量变化检测

内联 Python 对比新旧 manifest 的 code_hash + 全局变量 + 节点级 I/O 变量变化：

```python
import json

m = json.load(open('.extracted_nodes/manifest.json', encoding='utf-8'))
new_nodes = {n['seq']: n for n in m['nodes']}
old = {}
try:
    for l in open('.extracted_nodes/hash_snapshot.txt', encoding='utf-8'):
        p = l.strip().split('|', 5)
        old[int(p[0])] = {'name': p[1], 'hash': p[2], 'flow': p[3],
                           'input_vars': p[4] if len(p) > 4 else '',
                           'output_vars': p[5] if len(p) > 5 else ''}
except FileNotFoundError:
    print('无旧快照，建议先运行 rpa-ipa-analyzer 全量分析')
    exit(1)

# 1) 代码变更（code_hash 差异）
changed = [(s, i['name'], i['flow']) for s, i in old.items()
           if s in new_nodes and new_nodes[s]['code_hash'] != i['hash']]
added = [(s, n['show_name'], n['flow_file']) for s, n in new_nodes.items()
         if s not in old]
removed = [(s, i['name'], i['flow']) for s, i in old.items()
           if s not in new_nodes]

# 2) 变量映射变化（input_vars / output_vars 差异）
var_changed = []
for s, i in old.items():
    if s not in new_nodes:
        continue
    nn = new_nodes[s]
    new_in = json.dumps(nn.get('input_vars', {}), sort_keys=True, ensure_ascii=False)
    new_out = json.dumps(nn.get('output_vars', {}), sort_keys=True, ensure_ascii=False)
    old_in = i.get('input_vars', '') or '{}'
    old_out = i.get('output_vars', '') or '{}'
    if new_in != old_in or new_out != old_out:
        var_changed.append((s, i['name'], i['flow'],
                           'in' if new_in != old_in else '',
                           'out' if new_out != old_out else ''))

# 3) 全局变量变化（manifest 顶层的 global_vars 与旧快照对比）
#    从 flow JSON 的 global_vars[] 重新读取并与 snapshot 中记录的对比
#    这里检测 manifest 中是否有新增/变更的全局变量引用

# 4) 输出
for label, lst in [('代码变更', changed), ('新增', added),
                    ('删除', removed), ('变量映射变化', var_changed)]:
    print(f'{label}: {len(lst)} 个')
    if label == '变量映射变化':
        for s, n, f, in_chg, out_chg in lst:
            change_desc = []
            if in_chg:
                change_desc.append('输入变量变')
            if out_chg:
                change_desc.append('输出变量变')
            print(f'  N{s} [{f}] {n} — {\"/\".join(change_desc)}')
    else:
        for item in lst[:5]:
            print(f'  N{item[0]} [{item[2]}] {item[1]}')
        if len(lst) > 5:
            print(f'  ... 共 {len(lst)} 个')
```

### Step 4: 变更→报告映射

| 变更类型 | 更新章节 |
|---------|----------|
| Python节点代码变 | §2.2 该节点 + §4 数据血缘(若I/O变) + Appendix B |
| 新增/删除节点 | §1.2 流程图 + §2.2 + §4 + Appendix B |
| globalParams变 | §3 + 引用该参数的节点 |
| 变量映射变(含input/output vars) | §2.2 上下游 + §4 数据血缘 |
| 全局变量(`global_vars[]`)变更 | §3 + §1.2 流程路径中引用该变量的节点 |
| 流程结构变 | §1.2 + §1.3 |
| 新增/删除子流程 | §1 全量 + 建议走 `/rpa-ipa-analyzer` |

纯代码逻辑变更(最常见)：只改 §2.2 代码块+分析描述+§4 数据血缘。
代码描述(`@desc`)变：§2.2 节点分析描述。

### Step 5: 局部更新

读取 `.extracted_nodes/N{n}_*.py`，对比旧代码理解意图，重写 §2.2：
- 更新代码块、功能概述、数据结构、I/O 映射
- 检查连锁影响：
  - **输出变量变了**：用 `extract_nodes.py trace <project> <var> --direction down` 追踪下游消费者，更新所有受影响的节点输入映射
  - **输入变量变了**：用 `--direction up` 追踪上游生产者
  - **新增 Excel**：更新 §4.5
  - **全局变量引用变**：更新 §3 参数-流程映射

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
| `scripts/extract_nodes.py extract` 失败 | 检查 JSON 格式；确认 extract_nodes.py 已升级至 v3.0.0（使用子命令语法） |
| 识别为 0 变更但用户确认改了 | 对比 mtime，必要时整体重提取 |
| 章节断裂 | 回退全量 `/rpa-ipa-analyzer` |
