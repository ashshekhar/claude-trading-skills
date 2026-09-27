---
layout: default
title: Data Handling and Privacy
lang_peer: /ja/privacy-data-handling/
permalink: /en/privacy-data-handling/
---

# Data Handling and Privacy

This guide describes behavior found in the repository source. It is not a claim
that every skill or separately installed provider integration has the same
data path. Review the instructions and configuration for the skill you run.

## Local files and exclusions

The repository uses `.gitignore` to exclude local configuration and generated
or runtime data, including `.env` files (except `.env.example`), `.mcp.json`,
`.cache/`, `logs/`, `reports/`, `reviews/`, `.staging/`, `state/`, `*.log`,
`*.tmp`, and private key/certificate files (`*.pem`, `*.key`, `*.p12`, `*.pfx`,
`id_rsa`, and `id_ed25519`). Two empty state placeholders are tracked:
`state/journal/.gitkeep` and `state/theses/.gitkeep`.

The always-run pre-commit guard reads staged paths from Git's index, checks
them against the checked-out `.gitignore`, and independently rejects the
private/runtime paths above. It also blocks a forced `git add -f`. The guard
only runs when the repository's configured pre-commit hook is installed or is
run manually; `.gitignore` and a client-side hook cannot remove secrets already
committed or enforce policy on a server.

## Local data and external services

| Data or operation | Local handling | External boundary |
| --- | --- | --- |
| Repository source and user-selected files | Read by the skill or script the user runs. Files in ignored folders remain on the local machine unless separately uploaded or transmitted. | A prompt or API request can send the selected content to the configured service; inspect each skill's inputs and provider configuration. |
| Financial Modeling Prep (FMP) | Scripts build requests from the selected endpoint and parameters. | Requests can include symbols, dates, ranges, and an FMP credential. Most current client calls use an API-key header; some legacy endpoints use a query parameter. |
| FINVIZ | Screener code builds filters from the requested scan. | The FINVIZ URL/request can contain screener filters, themes, view, and symbols. |
| Alpaca | Portfolio code requests account, positions, assets, bars, or history through REST or an installed MCP server. | REST requests include API key ID and secret in headers and can reveal holdings, quantities, and account values. The repository source reviewed for this guide contains read requests and order templates, not a direct order-submission call. A separately installed MCP server may have different permissions. |
| Web search | The calling skill assembles a search query from its instructions and the user's task. | Query text is sent to the search provider exposed by the host application. The provider depends on the user's environment. |
| GitHub | Git operations and GitHub CLI use the user's configured account and selected repository content. | When the user pushes or opens a PR, the selected commits, issue text, and PR text go to GitHub. Do not commit private local data. |

Provider behavior, account configuration, and retention are controlled by the
provider and host application. This repository does not independently verify
those settings.

## Session-log miner

`skills/skill-idea-miner/scripts/mine_session_logs.py` has these defaults:

- Reads `*.jsonl` session files below `~/.claude/projects/` whose modification
  time is within the last 7 days, from an allowlist of five project names.
- Parses external user messages, assistant tool names and inputs, selected tool
  error output, and timestamps. It skips sidechain entries.
- Writes `reports/raw_candidates.yaml` relative to the current working
  directory, including aggregate counts, bounded signal samples, project
  labels, generated candidates, and synthetic session labels.
- If the local `claude` CLI is available and `--dry-run` is not set, sends a
  prompt to `claude -p`. The prompt contains aggregate signals, skill names,
  bounded error/automation/pattern samples, the configured project name, and
  up to five user-message samples total (each truncated to 200 characters).
  Signal samples are capped at three items per signal and 100 characters each.

`--project` replaces the default project allowlist with one project name;
`--lookback-days` changes the time window; and `--output-dir` changes the
report directory. These options can expand the read scope or write somewhere
other than `reports/`. Review the command and output path before running it.
`--dry-run` skips the LLM call only: it still reads matching local logs and
writes a local report (including an empty report when no logs match). The CLI's
provider, account, and retention settings are outside this repository's
visibility; check the account configured for `claude` before allowing a prompt
to leave the machine.

### Best-effort masking

Before prompt construction, report serialization, and candidate filtering, the
miner masks common recognizable patterns: credential assignments such as API
keys (including provider-prefixed names such as `FMP_API_KEY`), access tokens,
secrets, and passwords; Bearer/Basic strings; several common provider token
prefixes; email addresses; SSN-shaped values; and values following labeled
account, order, customer, user, portfolio, phone, or tax-ID fields. Structured
credential and identifier fields are masked by key name. Raw provider
stdout/stderr and candidate titles are not written to its logs, and report
session names are replaced with local sequence labels.

This is a limited pattern filter, not complete PII detection or anonymization.
It can miss names, addresses, free-form financial information, encoded or
unlabeled values, new credential formats, and other sensitive content. Review
the report locally before sharing it. If sending session-derived content to an
external model is not acceptable, do not run the miner with LLM abstraction;
`--dry-run` still reads and writes locally but skips that external call.

## Log retention

The daily and weekly skill-generation pipelines and the skill-improvement
pipeline each remove `logs/*.log` files older than 30 days when their run
reaches the log-rotation step. This is not a timer: files can remain longer if
the pipeline does not run or does not reach that step. The rotation does not
prune JSON state/backlog files in `logs/`, reports, or Claude Code session logs
under `~/.claude/projects/`. No retention period for those other data is
established by these scripts.

## Back up and restore `state/theses/`

Keep backups outside the repository and limit their filesystem permissions.
The directory is ignored by Git; its contents are not a repository backup.
From the repository root, this macOS/Linux shell example creates a private
archive with a timestamp:

```sh
umask 077
repo_root="$PWD"
backup_dir="$HOME/private-backups/claude-trading-skills"
mkdir -p "$backup_dir"
backup="$backup_dir/state-theses-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$backup" -C "$repo_root" state/theses
```

Restore first into a separate directory and inspect it before copying anything
over current state:

```sh
backup="/path/to/state-theses-YYYYMMDD-HHMMSS.tar.gz"
restore_dir="$(mktemp -d)"
tar -xzf "$backup" -C "$restore_dir"
find "$restore_dir/state/theses" -type f -print
```

After checking the recovered files, copy only the needed files back to
`state/theses/`. Do not extract an unverified archive directly over current
state. A synthetic-only test exercises archive/restore under a temporary
directory: `python3 -m pytest scripts/tests/test_state_theses_backup.py -q`.

## Security reporting and support status

See the repository's [SECURITY.md](https://github.com/tradermonty/claude-trading-skills/blob/main/SECURITY.md).
This repository does not publish a private contact address or confirm that
GitHub private vulnerability reporting is enabled. It also has no published
supported-version matrix. Include an exact tag or commit SHA when asking about
affected versions; do not infer a support promise for the default branch or
older commits.
