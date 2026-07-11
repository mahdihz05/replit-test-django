---
name: Replit git push via callback
description: Use the gitPush callback instead of shell git push when working in Replit.
---

In this Replit environment, shell-based `git push` to GitHub fails with authentication errors even when the user has connected their GitHub account to Replit.

**Rule:** Use the `gitPush` callback (from the git-remote skill) to push commits to GitHub.

**Why:** Replit manages the GitHub token internally; the `gitPush` callback uses that managed credential, whereas the shell does not have access to it.

**How to apply:**
- After committing, call `gitPush({})` in CodeExecution instead of `git push origin main` in the shell.
- The same applies to pull requests: use `createPullRequest` from the skill rather than `gh` CLI.
