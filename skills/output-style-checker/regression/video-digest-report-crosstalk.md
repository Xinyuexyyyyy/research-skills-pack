# Regression: video-digest report crosstalk

Source:

- `<workspace>/output/video-digest/runs/<run_id>/report.md`

Why this file exists:

- repeated paragraph spinning
- crosstalk from a different topic (`Theo / CMUX`)
- weak ending that does not land

Expected:

- should fail lint
- should hit duplicate/repetition-related checks
- should hit weak ending checks

