# Atlas technology-radar user service (research pilot)

This is a local, **read-only, metadata-only** scheduled companion for the
existing Cite–Refinery headless inbox. It does not install MCP servers,
run AI models, alter research graphs, write PRs, update code, or publish leads.

## Input and execution boundary

- An explicitly authorized local checkout must match **one exact commit SHA**.
  Modified or untracked monitored source paths or a newer HEAD stop the run.
- A private directory (mode 0700) contains sources.json, projects.json,
  feeds.json, and the resulting SQLite/report/health files.
- Exactly one github_public_release feed is permitted. The existing upstream
  source allowlist, 512 KiB-per-request guard, and latest-ten release limit are
  reused unchanged; failure does not produce a partial source snapshot.
- No token is loaded by this runner; GITHUB_TOKEN is ignored even if present
  in the environment. Public API limits therefore apply.
- The runner needs at least 2 GiB available disk space, performs exclusive
  flock locking, uses atomic 0600 local status reports, and leaves old success
  state intact if a new run fails.
- Saturated latest-ten windows without overlap with the previous window
  produce an explicit **possible gap** warning, not a completeness claim.
  Release titles and bodies are excluded from the human-readable daily brief.

## First-run acceptance

Use a private clean checkout, not a dirty active worktree:

    python3 scripts/atlas_release_monitor.py check \
      --workdir /private/atlas-radar \
      --repo /absolute/cite-refinery-checkout \
      --expected-head EXACT_40_CHARACTER_SHA

Then execute once:

    python3 scripts/atlas_release_monitor.py run \
      --workdir /private/atlas-radar \
      --repo /absolute/cite-refinery-checkout \
      --expected-head EXACT_40_CHARACTER_SHA

Inspect last_attempt.json, last_success.json, LATEST_TECH_RADAR.md,
radar.sqlite and github_releases.json. An unchanged second run must produce
zero new source records and zero new candidate associations.

## Systemd user timer

Install only after a successful manual run and owner review of the scope.
Never put personal credentials in unit files. The installed local service
should pass absolute workdir and checkout paths plus exact tested SHA.

    systemctl --user daemon-reload
    systemctl --user enable --now atlas-tech-radar.timer
    systemctl --user start atlas-tech-radar.service
    systemctl --user status atlas-tech-radar.service
    systemctl --user list-timers --all
    journalctl --user -u atlas-tech-radar.service -n 30 --no-pager

The example timer runs once daily in the machine's local timezone with
Persistent=true to catch up after shutdown and a randomized delay to avoid
simultaneous starts. Linger must be enabled for logged-out operation.

**Pause/stop:**

    systemctl --user disable --now atlas-tech-radar.timer

Disabling the timer preserves the private evidence ledger. Do not activate
two timers against the same database. The lock protects against simultaneous
writes, but additional pollers still waste rate-limit capacity.

## Limitations

This does not monitor model quality, source truth, security advisories, or
every commit. Latest-ten release feeds may miss intermediate releases after
extended downtime; saturated disjoint windows are flagged. The report is
local and is **not automatically delivered to chat/email**. No secrets,
model inference, patch installation, autonomous repository changes, or public
publication are part of this service.
