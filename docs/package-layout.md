# Package layout and PEP 8 migration

Application modules live under `src/campervan_search/`; tests and shared
fixtures live under `tests/`. Packaging metadata, command entry points and style
configuration are centralized in `pyproject.toml`. The strict review has moved
from the repository root to [strict-review.md](strict-review.md).

The distribution is named `campervan-weekly-search`, and its import package is
`campervan_search`. Install with `python -m pip install .` for operation or
`python -m pip install -e '.[dev]'` for development. The application uses only
the standard library; browser rendering remains an optional extra.

## Resources and commands

Dealer and variant registries, plus the HTML report template, are bundled
package resources. Their paths resolve relative to the installed package,
independently of the working directory. The extracted HTML template preserves
the pre-migration report output exactly; a stored synthetic regression case
checks that contract. The package fingerprint includes Python and resource files.

All previous module commands now use the package namespace, for example:

```bash
python -m campervan_search.discover_listings --output discovered_candidates.json
python -m campervan_search.camper_pipeline --input discovered_candidates.json
```

The equivalent installed commands are `campervan-discover` and
`campervan-screen`. Other entry points cover RSS collection/assessment/upload,
RDW, validation, delivery, history, coverage and retention. Manual candidate
input has moved to `config/candidates.json`. Runtime output paths and the
`data/`, `requests/`, `results/` and `archive/` handoffs stay in the checkout.

Retention defaults to the current working directory and accepts `--root` to
select a different checkout. It no longer derives a repository path from its
installed module location. Applying changes requires a checkout, and dry runs
do not create an archive directory or mutate files.

## Deployment compatibility

Workflows install the project before using package module commands. Scheduled
Thursday delivery, recipient guards, durable outboxes and isolated state branches
keep their existing operational contract. The refactor does not send email on
push or change AutoWereld's optional status.

Existing Pi services can keep invoking the two thin root compatibility launchers
without an immediate service migration. Those launchers add the checkout's `src`
directory only for that legacy command; application code and tests use normal
package imports. New Pi installations create `.venv` and use the installed RSS
command. The installer does not enable a timer or configure credentials.

The artifact download action stays standalone with standard-library helpers,
because it also runs before application state is restored. CI-only inline Python
has moved into scripts so the same style checks cover it.

## Verification

The 315 regression tests include the original 308 cases and seven layout/retention
checks. Black and Ruff check every tracked Python file, including helpers under
`.github/`. CI additionally builds both a source distribution and a wheel,
installs the wheel into a clean virtual environment, then checks resources and
entry points from outside the checkout. Native/container RSS probes and the
post-merge live integration exercise the updated workflow commands.
