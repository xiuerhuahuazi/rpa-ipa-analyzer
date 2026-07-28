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
- **Token-optimized**: extract → skeleton → LLM; §2.2 references `.extracted_nodes/` (no full source paste)
- **CLI**: `extract/list/stats/trace/compare/diff/skeleton/patch`
- **Evals**: golden manifest diff + promotion checks

## Install

```bash
git clone https://github.com/xiuerhuahuazi/rpa-ipa-analyzer.git
cp -r skills/rpa-ipa-analyzer/* ~/.claude/skills/rpa-ipa-analyzer/
# or ~/.cursor/skills/rpa-ipa-analyzer/
```

Remove any old `rpa-ipa-update` / `rpa-ipa-audit` skill folders after upgrading.

## License

MIT
