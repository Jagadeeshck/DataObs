# GitHub Issue Actions Required

This environment could not mutate GitHub issues because no `origin` remote is configured and `gh` is not installed. Do not claim these issues are closed until an authenticated maintainer runs equivalent commands.

For #46-#51, post a comment: `This Phase 0 PR preserves the product-scale requirements in docs/product/roadmap-v1.md and docs/product/feature-matrix.md, with target pillar, milestone, collection mechanism, storage model, API/UI destination, and security/licensing notes. The issue is superseded by the versioned product roadmap rather than completed in Phase 0.` Then close with reason `not planned`.

For #24-#32, re-query the full issue text, compare against docs/development/open-issue-closure-report.md, run the full required CI including integration containers, then close only genuinely complete issues with reason `completed`; otherwise keep open and update the report.

Suggested commands after installing/authenticating `gh`:

```bash
gh issue list --state open --limit 100
for n in 46 47 48 49 50 51; do
  gh issue comment "$n" --body-file /tmp/dataobs-superseded-comment.md
  gh issue close "$n" --reason "not planned"
done
```
