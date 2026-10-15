# Static application delivery

The application remains the existing index.html. Checks runs a headless Chromium
smoke test on pull requests and main. It exercises the embedded logo, employee
and admin dashboards, receipt form, receipts table, mobile viewport, and JavaScript
errors. Tests use temporary browser data. This is representative smoke coverage,
not a complete reimbursement or receipt submission regression suite.

Deploy Pages runs only after a successful Checks push run for main, deploying
that exact tested commit. It uploads only index.html, so automation documentation
and scripts are not published. Failed checks do not trigger deployment. Changes
to workflow files require the same review as executable code.

## One-time repository settings

An administrator must verify these settings, using the GitHub API when authorized
or GitHub settings if API access is unavailable:

1. Enable GitHub Actions and permit the official actions used in these workflows.
2. Under Pages, select **GitHub Actions** as the build/deployment source. Preserve
   any existing custom domain and HTTPS configuration. If the existing site uses
   a CNAME file or other assets, preserve/stage those before switching sources.
3. Run Checks at least once so `static-checks` is selectable. Protect main with a
   required pull request and required `static-checks` check. Require the branch
   to be up to date, apply enforcement to administrators, and prevent bypasses.
   Retain any existing reviews/checks. Required reviews will still need approval;
   automation does not approve its own changes.
4. Enable **Allow auto-merge** and **Allow squash merging**. Codex can then request
   native auto-merge for its PR, pinned to the tested head commit. GitHub waits for
   all required conditions. No privileged PR-code execution workflow is needed.
5. Verify the github-pages environment permits deployments from main. Required
   deployment reviewers must approve before a deploy can proceed; remove that
   gate only if you intentionally want unattended deployment.

Availability depends on repository visibility, plan, organization policy, and
permissions. Public repositories support the free Pages/Actions workflow. Private
repositories may have plan restrictions and Actions quotas. Do not upgrade plans
or enable paid overages; stop and report any unavailable feature or exhausted quota.

## Access and verification

Codex needs scoped GitHub access to read settings/checks, push branches and workflow
files, create PRs, and request native auto-merge. Changing protection, Pages, or
repository merge settings requires repository administration permission. Git read
access alone does not prove any of these permissions. Permit api.github.com in
the cloud environment network settings; enter credentials only through secure
settings, never in chat or committed files.

The first activation should be a PR containing this automation. If protection is
not yet configured, an administrator must finish the one-time setup and merge it
without claiming automated protection was verified. Subsequent Codex changes can
follow AGENTS.md. Confirm both Checks and Deploy Pages succeed for the merged SHA
and verify the deployed site's demo login. No deployment has been proven merely
by adding these files.
