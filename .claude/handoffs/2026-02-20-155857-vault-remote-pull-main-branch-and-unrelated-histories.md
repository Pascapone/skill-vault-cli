# Handoff: Vault Repo Pull Fails on User Machine (master/main + unrelated histories + config.yaml dirty state)

## Session Metadata
- Created: 2026-02-20 15:58:57
- Project: C:\Users\pasca\Coding\skill-vault
- Branch: main
- Session duration: ~2-3 hours (across multiple iterative fixes and user repro logs)

### Recent Commits (for context)
  - f467129 branching
  - df18352 repo problems
  - 2150ca2 added documentation
  - 0c38850 new commands for repo
  - dc4b539 remote repo

## Handoff Chain

- **Continues from**: `.docs/handoffs/2026-02-20-142004-vault-github-quickstart-and-handoff.md`
- **Supersedes**: None

> This handoff continues the same vault-remote integration thread, now focused on real-user failure cases.

## Current State Summary

Remote/GitHub support was expanded (SSH normalization, `vault repo` commands, disconnect/pull workflow, branch handling).  
However, the user still reproduces pull failures on a real machine (`C:\Users\Pasko\Documents\projects\skill-vault-cli`): first `master` mismatch, then `unrelated histories`, and finally our guard reports "local uncommitted changes" because `~/.skill-vault/config.yaml` is untracked and marks repo dirty. The next agent should debug directly with live git/network access in the user's environment and finalize behavior.

## Codebase Understanding

## Architecture Overview

- `src/skill_vault/cli.py` orchestrates commands and persists global vault settings at `~/.skill-vault/config.yaml`.
- `src/skill_vault/vault.py` encapsulates Git operations (`initialize`, remote management, branch resolution, push/pull).
- Pull behavior is now centralized in `pull_vault_remote()` in CLI.
- `vault init` creates local repo structure and initial commit, then optional remote configuration.

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `src/skill_vault/cli.py` | CLI command handlers and settings flow | Main location of branch defaults, `vault repo pull`, fallback/error handling |
| `src/skill_vault/vault.py` | Git abstraction for vault repo | Contains clean/dirty checks, init branch naming, remote branch helpers |
| `README.md` | User-facing command docs | Updated for SSH, disconnect, repo pull, main default |
| `.docs/project/guides/vault-github-quickstart.md` | Internal quickstart guide | Mirrors CLI flow used by user |
| `.docs/handoffs/2026-02-20-142004-vault-github-quickstart-and-handoff.md` | Previous context | Original implementation notes and design intent |

### Key Patterns Discovered

- Global config is intentionally stored in `~/.skill-vault/config.yaml`, i.e. **inside** the vault git repo path.
- `Vault.is_clean()` uses `repo.is_dirty(untracked_files=True)`, so untracked files (like `config.yaml`) make repo "dirty".
- Pull fallback for unrelated histories currently requires `vault.is_clean()` and `vault.is_bootstrap_history()`.
- Command naming can be confusing for users: there is `skill-vault pull` and `skill-vault vault repo pull`, but no `skill-vault vault pull`.

## Work Completed

### Tasks Finished

- [x] Added SSH URL normalization for GitHub remotes in CLI paths (`init`, `repo connect`, `repo create`).
- [x] Added `vault repo disconnect`.
- [x] Added `vault repo pull` and shared pull helper.
- [x] Set branch default behavior toward `main` in config loading and init flow.
- [x] Added branch existence/default-branch fallback logic (`master` -> remote default branch).
- [x] Added unrelated-histories handling path that can re-align bootstrap local history to remote branch.
- [x] Updated README and quickstart docs for SSH + new repo commands.

## Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| `src/skill_vault/cli.py` | Added repo subcommands, branch defaults, pull orchestration, unrelated-histories fallback handling | Improve remote UX and robustness across machines |
| `src/skill_vault/vault.py` | Added remote removal, local/remote branch checks, bootstrap history helper, branch main rename on init | Support safe disconnect and better branch/history handling |
| `README.md` | Added SSH-first examples, `vault repo pull`, `vault repo disconnect`, main default note | Align docs with new CLI behavior |
| `.docs/project/guides/vault-github-quickstart.md` | Updated setup/pull/disconnect instructions | Keep internal guide consistent with CLI |

## Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Prefer SSH for GitHub remotes | Keep HTTPS support as-is vs normalize | User requested SSH-first; normalization reduces user error |
| Add explicit `vault repo pull` command | Only keep global `pull` command | Clearer remote-focused workflow and discoverability |
| Keep branch configurable but default to `main` | Default to current branch/master | Modern default expected by users and GitHub repos |
| Add unrelated-histories fallback path | Hard fail only | Needed for first-sync scenario after local bootstrap init |

## Pending Work

## Immediate Next Steps

1. Reproduce on user machine with real repo state and confirm why `config.yaml` keeps fallback blocked (most likely due `is_clean(untracked=True)`).
2. Implement final fix for dirty-check behavior during unrelated-histories recovery:
   - likely ignore untracked files for this specific check, and/or
   - ignore `config.yaml`, and/or
   - add `config.yaml` to generated `.gitignore`.
3. Verify full flow end-to-end:
   - `vault init -r ...`
   - `vault repo pull`
   - skills visible in vault/project flows.

### Blockers/Open Questions

- [ ] Should `~/.skill-vault/config.yaml` be tracked, ignored, or moved outside the vault git repo?
- [ ] Should unrelated-histories fallback run even when untracked files exist (safe for untracked only)?
- [ ] Should `vault init --repo` optionally skip creating a bootstrap commit to avoid unrelated histories entirely?
- [ ] Do we want an alias/redirect for user typo pattern `skill-vault vault pull`?

### Deferred Items

- Local sandbox could not perform reliable bare-remote E2E git simulation due environment restrictions; reproduction should be done directly on user machine.
- A local inaccessible temp directory (`tmp5pbvq7zi`) appeared in this workspace during ad-hoc repro and may cause noisy `git status` warnings here; unrelated to user issue but worth cleaning separately.

## Context for Resuming Agent

## Important Context

User repro (real machine) is the source of truth:

1) After reinstall and init:
- `skill-vault vault init -r git@github.com:Pascapone/skill-vault.git`
- Output says initialized, remote configured, no global skills found.

2) Pull behavior:
- `skill-vault vault repo pull`
- previously: `fatal: couldn't find remote ref master`
- then after patching: `Pull failed due to unrelated histories and local uncommitted changes. Commit/stash first, then retry.`

3) Direct git state in `C:\Users\Pasko\.skill-vault`:
- branch is `main`
- untracked file exists: `config.yaml`
- `git stash` says no local changes (because only untracked), but our code still treats repo as dirty.

Most likely root cause now: fallback guard rejects due `untracked_files=True` even for benign untracked `config.yaml`.

## Assumptions Made

- User wants SSH-only practical behavior; HTTPS support is not required operationally.
- GitHub default branch is `main` in target repos.
- The failing runtime is user clone `skill-vault-cli`, not necessarily this local workspace state.

## Potential Gotchas

- `vault repo pull` and global `pull` share helper logic; fix must not break both paths.
- Branch value is persisted in `~/.skill-vault/config.yaml`; old `master` values can survive upgrades.
- No command `skill-vault vault pull`; user-facing docs/help should call out `skill-vault pull` or `skill-vault vault repo pull`.
- If you change cleanliness checks, protect truly unsafe cases (tracked modifications) while allowing safe bootstrap realignment.

## Environment State

### Tools/Services Used

- PowerShell
- Python editable install (`pip install -e . --force-reinstall --no-deps`)
- GitPython + git CLI via application commands
- Session-handoff scripts from `C:\Users\pasca\.skill-vault\skills\global\session-handoff\scripts`

### Active Processes

- None intentionally left running.

### Environment Variables

- No new env vars were added in this session.

## Related Resources

- `src/skill_vault/cli.py`
- `src/skill_vault/vault.py`
- `README.md`
- `.docs/project/guides/vault-github-quickstart.md`
- `.docs/handoffs/2026-02-20-142004-vault-github-quickstart-and-handoff.md`

---

**Security Reminder**: Before finalizing, run `validate_handoff.py` to check for accidental secret exposure.
