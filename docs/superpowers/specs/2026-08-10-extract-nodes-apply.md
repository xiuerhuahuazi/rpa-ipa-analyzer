# Spec: `extract_nodes.py apply`

**Date:** 2026-08-10  
**Status:** Approved (方案 1)  
**Repo:** rpa-ipa-analyzer

## Goal

Write edited `.extracted_nodes/N*.py|.js` files **back** into the matching IPA flow JSON node code fields, so agents edit small files instead of huge flow JSON.

## CLI

```bash
python extract_nodes.py apply <project_path> [--dry-run] [--node N] [--file PATH] [--force]
```

| Flag | Behavior |
|------|----------|
| (default) | All structured code nodes; **skip** when file body hash == live flow code hash |
| `--node N` | Only listed seq (repeatable) |
| `--file` | Filename or glob under `.extracted_nodes` (repeatable) |
| `--dry-run` | Plan only; no backup, no write |
| `--force` | Write even if hash matches |

## Locate target

1. Prefer header meta: `@id`, `@flow`, optional `@node: N{n}`
2. Fall back to `manifest.json` (`node_id`, `flow_file`, `file`)
3. Skip heuristic extraction nodes unless explicitly selected and resolvable

## Transform before write

- **Strip** extract-generated header (`"""@node…"""` / `/** @node… */`)
- Preserve **code** newline style of the live flow value (`\n` vs `\r\n`)
- Write into `python_script` or `js_code` on `input_params`
- Do **not** apply to heuristic / non-code components

## Safety

- Before first write to a flow file: copy  
  `{flow}.bak_apply_YYYYMMDD_HHMMSS`
- After in-memory set: re-read param and verify `code_hash`
- Aggregate errors; exit code `2` if any error
- Prefer compact JSON separators matching IPA exports; keep trailing newline if present

## Out of scope

- Report patch (`patch` command remains separate)
- Rewriting non-code node properties
- Auto `extract` before apply (caller must ensure `.extracted_nodes` exists)
