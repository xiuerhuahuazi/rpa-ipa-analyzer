---
name: rpa-ipa-audit
description: 对 IPA Studio RPA 项目进行 6 维并行代码审计（安全/性能/API契约/错误处理/测试缺口/文档漂移），生成独立审计报告 AUDIT_REPORT.md。要求项目已通过 rpa-ipa-analyzer 分析过（.extracted_nodes/ 存在）。触发词："审计""audit""代码安全检查""代码质量审计"。
---

# IPA Studio RPA 代码审计器

对已分析的 RPA 项目执行 6 维度并行自动化代码审计。

## 前置条件

- `.extracted_nodes/` 目录存在（由 `rpa-ipa-analyzer` 分析或 `extract_nodes.py extract` 生成）
- 如不存在，先运行：
  ```bash
  python.exe scripts/extract_nodes.py extract {project_path}
  ```

## 审计流程

### Step 1: 项目发现

读取 `.extracted_nodes/manifest.json`，获取节点索引。如果 `total_nodes` 为 0，直接退出："项目无可审计的代码节点"。

### Step 2: 并行审计

6 个 Explore agent 同时启动，每个 agent 的完整 prompt 见 `references/audit_swarm.md`。

**公共输入约定**：每个 agent 首先读取 `{project_path}/.extracted_nodes/manifest.json` 了解节点列表，然后通过 manifest 中的 `file` 字段定位并选择性读取自身审计范围内的 `.py` / `.js` 文件。

**审计维度选择**：

| 参数 | 审计范围 |
|------|---------|
| 默认（无参数） | 全部 6 维 |
| `--scope security` | 仅 Security |
| `--scope security,error` | Security + Error |

### Step 3: 合并与报告生成

所有 agent 完成后，启动 Merge Agent。完整 prompt 见 `references/audit_swarm.md`。

核心逻辑：
1. 加载 `audit_findings/` 下所有 JSON
2. 去重：同一文件+相同行范围的发现合并
3. 排序：critical → high → medium → low
4. 生成 `AUDIT_REPORT.md`（5 节：Executive Summary, Heatmap, Prioritized List, Remediation Effort, Cross-Reference）

### Step 4: 更新分析报告（可选）

如果存在 `分析报告_{project_name}.md`，在附录前追加 §6 审计摘要。

## 输出

| 文件 | 路径 |
|------|------|
| Security 审计 | `{project_path}/audit_findings/security.json` |
| Performance 审计 | `{project_path}/audit_findings/performance.json` |
| API 契约审计 | `{project_path}/audit_findings/api_contracts.json` |
| 错误处理审计 | `{project_path}/audit_findings/error_handling.json` |
| 测试缺口审计 | `{project_path}/audit_findings/testing_gaps.json` |
| 文档漂移审计 | `{project_path}/audit_findings/documentation_drift.json` |
| 合并审计报告 | `{project_path}/AUDIT_REPORT.md` |

## 异常处理

| 场景 | 处理 |
|------|------|
| `.extracted_nodes/` 不存在 | 自动运行 `extract_nodes.py extract` |
| 某个 agent 超时/失败 | 继续其他 agent，标注 "INCOMPLETE" |
| 全部 agent 失败 | 不生成 AUDIT_REPORT.md |
| `audit_findings/` 已存在 | 覆盖写入 |
