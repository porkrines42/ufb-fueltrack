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
request. If authenticated GitHub access permits it, inspect repository permissions,
auto-merge support, and the main branch's effective protection/rulesets. Require
the `static-checks` status check on main. Once the policy is verified, request
GitHub native auto-merge with `gh pr merge --auto --squash --match-head-commit SHA`.
Use the actual reviewed/tested PR head SHA. Respect required reviews and every
other required check. Never force merge, use admin bypass, disable checks, or
remove protection. If native auto-merge is unsupported or settings cannot be
verified, report the exact blocker; do not fall back to an unconditional merge.

After merge, monitor Checks and Deploy Pages for that commit. Report deployment
success only after GitHub confirms it. Do not claim a local test or Git push
proves deployment. Do not enable paid services or increase paid usage budgets.

See AUTOMATION.md for the one-time GitHub settings and access requirements.
