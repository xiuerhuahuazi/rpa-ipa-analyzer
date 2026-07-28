# Parallel Code Audit Swarm — Agent Prompts

> **触发方式**: 由本技能 **模式 C — audit**（或 analyze `--depth deep`）调用。
> **前置条件**: `.extracted_nodes/manifest.json` 及对应 `.py`/`.js` 文件必须存在。
> **输入约定**: 每个 agent 首先读取 `{project_path}/.extracted_nodes/manifest.json` 获取节点索引，然后通过 manifest 中的 `file` 字段定位读取脚本文件。

Detailed agent prompts for the parallel audit swarm. Launch all 6 agents simultaneously, then run the merge agent.

## Agent 1: Security Auditor

**Target**: All extracted `.py` and `.js` files in `.extracted_nodes/`

**Scan for**:
- Hardcoded secrets: passwords, tokens, API keys, connection strings, bearer tokens in plaintext
- Unsafe `eval()` / `exec()` / `compile()` calls that process external input
- Command injection vectors: `os.system()`, `subprocess` with `shell=True`, unsanitized shell args
- Path traversal risks: file paths constructed from globalParams without validation (e.g., `../../etc/passwd`)
- Missing input sanitization on global parameter values before use in file operations
- Hardcoded internal IPs, usernames, hostnames, or domain credentials
- In `.js` files: `innerHTML` assignment with unescaped data, `eval()` usage

**Output**: `{project_path}/audit_findings/security.json`
```json
{
  "agent": "security",
  "summary": "N critical, M high, P medium, Q low",
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "file": "N1_xxx.py",
      "line_range": "10-15",
      "category": "hardcoded_secret|unsafe_eval|command_injection|path_traversal|missing_sanitization",
      "description": "具体问题描述",
      "recommendation": "修复建议"
    }
  ]
}
```

## Agent 2: Performance Auditor

**Target**: All extracted `.py` files in `.extracted_nodes/`

**Scan for**:
- Blocking I/O patterns: synchronous file reads inside loops, missing batch processing
- Excessive memory: loading entire Excel files when only specific columns needed (missing `usecols` parameter)
- Unbatched operations: row-by-row Excel writes via win32com instead of bulk DataFrame operations
- Repeated file reads: same Excel file read multiple times by different nodes without caching
- Inefficient pandas: `iterrows()` instead of vectorized operations, `pd.concat()` in loops, `DataFrame.append()` (deprecated)
- Missing `dtype` specification when reading large CSV/Excel files
- win32com overhead: nodes using COM automation when openpyxl/pandas would suffice
- Unnecessary columns loaded: `usecols` not specified when only 2-3 of 22 columns are actually used

**Output**: `{project_path}/audit_findings/performance.json`

## Agent 3: API Contract Auditor (RPA-adapted)

**Target**: All extracted `.py` and `.js` files + `manifest.json`

**Verify**:
- Function signature matches its `@node` docstring: parameter names, count, return values
- `@input:` docstring lists variables that exist in actual function parameters and code usage
- `@output:` docstring lists variables that are actually assigned/returned
- Cross-node variable contracts: output variable names from upstream nodes match input variable names expected by downstream consumers (use `manifest.json` for I/O mappings)
- Breaking changes: compare function signatures against any `_旧` (old) variant nodes — same `show_name` with `_旧` suffix
- Variable type consistency: same variable name used as different types across nodes (e.g., string in N1, DataFrame in N3)

**Output**: `{project_path}/audit_findings/api_contracts.json`

## Agent 4: Error Handling Auditor

**Target**: All extracted `.py` and `.js` files in `.extracted_nodes/`

**Scan for**:
- Bare `except:` clauses (no exception type specified, catches KeyboardInterrupt/SystemExit)
- Swallowed exceptions: `except: pass`, `except: print()` without re-raise, `except: return None` without logging
- Missing retry logic on transient-failable operations: `pd.read_excel()`, network file paths
- Missing input file existence checks before `pd.read_excel()` / file open calls
- Missing column validation after reading Excel files (column renamed upstream → silent failure)
- `exit()` or `sys.exit()` calls that would terminate entire RPA flow instead of raising
- Missing `finally` cleanup for win32com Excel COM resources (zombie EXCEL.EXE processes)
- Unhandled edge cases: empty DataFrames, missing sheets, NaN propagation through calculations
- Division by zero risks: disk usage calculations where denominator could be 0

**Output**: `{project_path}/audit_findings/error_handling.json`

## Agent 5: Testing Gap Auditor

**Target**: All extracted `.py` files in `.extracted_nodes/` + project structure

**Analyze**:
- Zero test coverage: check if any test files exist in project (most RPA projects have none — note this)
- Flag functions with estimated cyclomatic complexity > 10 that lack tests
  - Count branches: if/else, for/while loops, except blocks, nested conditionals
- Identify most critical untested functions ranked by: data mutation risk × business logic concentration × file I/O operations
- Dead code candidates:
  - `_旧` (old version) nodes still referenced in main flow
  - Duplicate code nodes (same `code_hash` in manifest) — keep one, test one
  - Variables written but never read downstream (check manifest I/O chains)
- Report: test coverage per sub-process (0% expected), top-10 most complex untested functions, dead code list

**Output**: `{project_path}/audit_findings/testing_gaps.json`

## Agent 6: Documentation Drift Auditor

**Target**: All extracted `.py` and `.js` files in `.extracted_nodes/`

**Compare** `@node` header docstring against actual code:
- `@desc` field still says `[待补充]` → flag as undocumented
- `@input` lists variables not actually used in code → flag as ghost parameters
- Variables used in code but not listed in `@input` → flag as undocumented inputs
- `@output` lists variables never assigned in code → flag as phantom outputs
- `@tag` classification (BOILERPLATE/SKELETON/GLUE/BUSINESS) — verify against actual code complexity:
  - BUSINESS tag but code is < 10 lines → likely misclassified
  - BOILERPLATE tag but contains business logic → false positive
- `show_name` in node metadata vs actual code purpose → flag misleading names
- For `.js` files: verify `@js_category` matches actual code patterns (DOM navigation vs form fill vs data extraction)

**Output**: `{project_path}/audit_findings/documentation_drift.json`

---

## Merge Agent (run after all 6 complete)

**Input**: All 6 JSON files from `audit_findings/`

**Process**:
1. Load all findings into a unified list
2. Deduplicate: same issue in same file+line found by multiple agents → keep most detailed version, add `cross_reference: ["security", "error_handling"]`
3. Resolve severity conflicts: when two agents rate same issue differently, use higher severity, note disagreement
4. Sort: critical → high → medium → low

**Output**: `{project_path}/AUDIT_REPORT.md` with 5 mandatory sections:

### Section 1: Executive Summary
- Top 5 most critical findings (one line each)
- Total count by severity: critical=N, high=M, medium=P, low=Q
- Overall health assessment (1-paragraph)

### Section 2: Heatmap of Issues by File
Table format:
| File | Security | Performance | API Contracts | Error Handling | Testing | Documentation | Total |
|------|----------|-------------|---------------|----------------|---------|---------------|-------|
| N1_xxx.py | 1 | 2 | 0 | 3 | 1 | 1 | 8 |

### Section 3: Prioritized Finding List
Each finding: file, line range, category, severity, description, recommendation, cross-references

### Section 4: Estimated Remediation Effort
| Severity | Count | Est. hours each | Total hours |
|----------|-------|-----------------|-------------|
| critical | N | 2-4 | X |
| high | M | 1-2 | Y |
| medium | P | 0.5-1 | Z |
| low | Q | 0.25 | W |
| **Total** | | | **sum** |

### Section 5: Cross-Reference Index
Group related findings: "bare except pattern: N1(L12), N5(L34), N12(L8), N22(L45)"
