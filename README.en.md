# rpa-ipa-analyzer

Analyze, incrementally update, or audit IPA Studio RPA projects. **One installable skill** with three modes.

## Modes

| Mode | Triggers | Output |
|------|----------|--------|
| **analyze** | "analyze this RPA project", `--depth quick\|standard\|deep` | `分析报告_*.md` |
| **update** | "update analysis report", incremental update | Surgical report patches |
| **audit** | "audit", security review | `AUDIT_REPORT.md` |

Do **not** install separate `rpa-ipa-update` / `rpa-ipa-audit` skills (removed in 3.2).

## Highlights

- **skills/ layout** aligned with popular agent-skill repos (`npx skills add`)
- **Platforms**: Claude Code / Cursor / Codex / OpenClaw / DSH
- **Token-optimized**: extract → skeleton → LLM; §2.2 references `.extracted_nodes/` (no full source paste)
- **CLI**: `extract/list/stats/trace/compare/diff/skeleton/patch/apply`
- **`apply` (3.3)**: write edited `N*.py|js` back into flow JSON with header strip, hash skip, and `bak_apply_*` backups
- **Evals**: golden manifest diff + promotion checks

## Install

```bash
git clone https://github.com/xiuerhuahuazi/rpa-ipa-analyzer.git
cp -r skills/rpa-ipa-analyzer/* ~/.claude/skills/rpa-ipa-analyzer/
# or ~/.cursor/skills/rpa-ipa-analyzer/
```

DSH: copy the same directory into a DSH skill root — user-wide `~/.agents/skills/rpa-ipa-analyzer/`,
or a single workspace's `<workspace>/.agents/skills/rpa-ipa-analyzer/` (lower rank, wins over the
user-wide copy). DSH picks it up without a restart. See `skills/rpa-ipa-analyzer/DSH.md`.

Remove any old `rpa-ipa-update` / `rpa-ipa-audit` skill folders after upgrading.

## Running the scripts

Always invoke through the bundled launcher rather than `python3 scripts/...`:

```bash
"$SK/scripts/rpa.sh" extract  . --force      # scripts\rpa.cmd on Windows
"$SK/scripts/rpa.sh" skeleton . --depth standard
```

The launcher resolves a Python 3.8+ interpreter (validating each candidate) and always appends
`-X utf8`. Both matter: on Windows `python` / `python3` are often Microsoft Store App Execution
Alias stubs that exit `9009`, and without `-X utf8` CPython encodes stdout with the ANSI code page
(GBK on zh-CN) while the agent decodes as UTF-8 — Chinese node names reach the model as mojibake
with exit code **0**, silently corrupting every report.

## License

MIT
