# Branch Protection Configuration

Apply via GitHub UI (Settings -> Branches -> Add rule for `main`) or via the
`gh` CLI / Terraform snippet below. This repo's CI job names must match
exactly for required-status-check wiring to work.

## Required settings for `main`
- Require a pull request before merging (1+ approving review)
- Dismiss stale approvals when new commits are pushed
- Require status checks to pass before merging:
  - `Lint (ruff)`
  - `Type check (mypy --strict)`
  - `Test (100% coverage gate)`
  - `Build package`
  - `Build container image`
- Require branches to be up to date before merging
- Require conversation resolution before merging
- Require signed commits (recommended)
- Do not allow bypassing the above settings (include administrators)
- Restrict force pushes and deletions

## Via GitHub CLI
```bash
gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  -f required_status_checks[strict]=true \
  -f "required_status_checks[contexts][]=Lint (ruff)" \
  -f "required_status_checks[contexts][]=Type check (mypy --strict)" \
  -f "required_status_checks[contexts][]=Test (100% coverage gate)" \
  -f enforce_admins=true \
  -f required_pull_request_reviews[required_approving_review_count]=1 \
  -f required_pull_request_reviews[dismiss_stale_reviews]=true \
  -f restrictions=null
```
