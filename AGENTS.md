# Development and delivery

Use the existing checkout; do not create a worktree unless requested. Preserve the
application's branding and existing functionality. This static demo has no backend.

Before submitting a change, run:

```sh
python -m pip install playwright==1.58.0
python -m playwright install --with-deps chromium
python scripts/smoke.py
```

For an installed system Chromium, set `CHROMIUM_PATH=/usr/bin/chromium` instead
of downloading a browser. Tests use a fresh browser context and local server.

When the user requests implementation and delivery, create a branch and pull
request. Run the automated tests and inspect available PR check results. Request
GitHub native auto-merge through the GitHub connector. Administrative read access
to branch protection or rulesets is not a prerequisite: if those reads return
403, let GitHub enforce the effective policy when accepting and executing the
native auto-merge request. Use the CLI when available if an explicit squash method
and head pin are needed:
`gh pr merge --auto --squash --match-head-commit SHA`.
Use the actual reviewed/tested PR head SHA; if it changes, inspect the changes and
check the new head's test results. The connector may infer the merge method from
repository settings and may not support head pinning; verify the PR head before
and after requesting auto-merge.

Keep `static-checks` required on main and respect all GitHub-enforced required
checks, branch protections, and approvals. Native auto-merge must wait for those
requirements; never force merge, use admin bypass, disable checks, remove
protection, or substitute an unconditional merge. If the native auto-merge request
fails, report the exact API or permission error. Missing administrative read
access alone must not prevent attempting native auto-merge.

After merge, monitor Checks and Deploy Pages for that commit. Report deployment
success only after GitHub confirms it. Do not claim a local test or Git push
proves deployment. Do not enable paid services or increase paid usage budgets.

See AUTOMATION.md for the one-time GitHub settings and access requirements.
