---
name: rpa-ipa-audit
description: 对 IPA Studio RPA 项目进行代码审计（安全/性能/API契约/错误处理/测试缺口/文档漂移），生成 AUDIT_REPORT.md。要求已有 .extracted_nodes/。默认按 code_hash 增量审计。触发词："审计""audit""代码安全检查""代码质量审计"。
---

# IPA Studio RPA 代码审计器

对已提取节点做最多 6 维审计。详细 agent prompt：`references/audit_swarm.md`。

`{SKILL_ROOT}` = `rpa-ipa-analyzer` 安装目录。

## 前置

```bash
python {SKILL_ROOT}/scripts/extract_nodes.py extract {project_path}
```

`total_nodes==0` → 退出：「无可审计代码节点」。

## 范围

| 参数 | 行为 |
|------|------|
| 默认 | **增量**：只审计相对 `hash_snapshot.txt` / `previous_manifest.json` 有 hash 变化（或新增）的节点；无快照则全量 |
| `--full` | 强制全量 6 维 |
| `--scope security` | 仅 Security（可逗号组合） |

```bash
python {SKILL_ROOT}/scripts/extract_nodes.py diff {project_path} --json --out {project_path}/.extracted_nodes/changed.json
```

- 增量：agent 只读 `changed`/`added` 中的 `file`
- 全量：可读全部 `N*.py|js`（仍经 manifest，不读原始 flow JSON）

## 流程

1. `diff`（或 `--full` 跳过过滤）确定文件集合  
2. 按 scope 启动 Explore agent（默认最多 6；增量且变更很少时可串行 1–2 个以省 token）  
3. 写入 `audit_findings/*.json` → Merge → `AUDIT_REPORT.md`  
4. 若存在 `分析报告_*.md`，可用 `patch` 追加 §6 摘要（勿整文件重写）

## 输出

| 文件 | 路径 |
|------|------|
| 分维 JSON | `{project}/audit_findings/*.json` |
| 合并报告 | `{project}/AUDIT_REPORT.md` |

## 异常

| 场景 | 处理 |
|------|------|
| 无 `.extracted_nodes/` | 先 extract |
| 某维失败 | 继续其他，标 INCOMPLETE |
| 全失败 | 不写 AUDIT_REPORT.md |
| findings 已存在 | 覆盖 |
