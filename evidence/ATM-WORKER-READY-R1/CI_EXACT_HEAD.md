# CI_EXACT_HEAD

Workflow: `.github/workflows/atm-worker-ready-r1.yml`.

The authoritative run URL and exact candidate SHA are recorded in the project PR/Issue audit comment after the run completes. They are deliberately not embedded into this committed file because doing so would create a new HEAD after the run and invalidate exact-head identity.

Acceptance requires the workflow to report the same `GITHUB_SHA` as the audited PR head and all gates to pass. The workflow uploads its identity/test/evidence bundle as an Actions artifact.
