# Validation

Last verified: 2026-07-06

## Environment

- Python 3.13.14
- pytest 9.0.3
- ruff 0.15.15
- Source-tree validation used the local Python environment.

## Commands

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q -p no:cacheprovider
python scripts\validate_skill.py --run-evals
ruff check .
```

## Observed Results

- `python -m pytest -q -p no:cacheprovider`: `169 passed, 2 skipped`
- `python scripts\validate_skill.py --run-evals`: `OK: briefprint skill repository validated (24 test files, 9 eval cases, 10 trigger cases, 5 model benchmark cases)`
- `ruff check .`: `All checks passed!`

Latest fetched `origin/main` CI status was checked separately: GitHub Actions `CI` run `28761659503` completed successfully for `344f05d` on 2026-07-06T01:14:27Z. This confirms the base branch status; the commands above remain the source-tree validation for the current checkout.

`tests/test_distribution_smoke.py` remains opt-in and skips unless `DBC_RUN_INSTALLED_SMOKE=1` is set. CI or release validation should still build wheel and sdist artifacts, install each into a fresh virtual environment, and run the installed smoke test outside the repository root.

Example artifact smoke flow:

```bash
python -m build
python -m venv /tmp/dbc-wheel-venv
/tmp/dbc-wheel-venv/bin/python -m pip install dist/*.whl
/tmp/dbc-wheel-venv/bin/python -m pip install pytest
(cd /tmp && DBC_RUN_INSTALLED_SMOKE=1 /tmp/dbc-wheel-venv/bin/python -m pytest /path/to/repo/tests/test_distribution_smoke.py -q)

python -m venv /tmp/dbc-sdist-venv
/tmp/dbc-sdist-venv/bin/python -m pip install dist/*.tar.gz
/tmp/dbc-sdist-venv/bin/python -m pip install pytest
(cd /tmp && DBC_RUN_INSTALLED_SMOKE=1 /tmp/dbc-sdist-venv/bin/python -m pytest /path/to/repo/tests/test_distribution_smoke.py -q)
```

## Validation Scope

The current validation covers:

- installable `skills/briefprint/` bundle shape and metadata,
- trigger fixtures and near-miss boundaries,
- document normalization and fingerprinting,
- document cache and output cache behavior,
- cache explanation events,
- incident record splitting,
- privacy redaction and HMAC tamper-detection behavior,
- rendering and evidence preservation,
- local deterministic benchmark/eval fixtures,
- CLI and packaging smoke coverage available from the source tree.

Trigger evals are static boundary fixtures. They validate intended trigger coverage and near-miss cases, but they do not measure actual model-side invocation behavior.

Model invocation benchmark cases are manual worksheets for hosts that expose real invocation telemetry.

Production validation should continue adding real samples from the target domain and compare:

- factual preservation,
- missing-value behavior,
- action item extraction,
- risk extraction,
- structured-state assertions for actions, risks, metrics, evidence, and unknowns,
- LLM call count,
- cache hit rate,
- output readability,
- privacy and retention expectations.
