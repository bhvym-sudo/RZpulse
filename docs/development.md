# Development and milestone status

Use Python 3.12+. Install with `pip install -e '.[dev]'`, then run `pytest`,
`ruff check .` and `ruff format --check .`. Tests use mocks, not `.env` secrets.

## Milestone 1: foundation implemented, runtime validation pending

Created pyproject, entry point, configuration, error types, API registry,
transport, initial Textual shell, help, settings, footer and navigation.
Core validation covers environment selection, auth, URL/query construction,
retry rules, error mapping and registry input validation.

Limitations: editable installation and launch are not yet certified. The shell
cannot resolve PyPI and there are no cached Textual/Rich/build-backend wheels.
No real account credentials were read or used. Next: install dependencies and
run the headless and manual UI checks.

## Milestone 2: four resources implemented

Shared resource view in `app.py` supports Payments first, then Orders, Refunds,
Settlements using the same verified registry. Features: one-page GET listing,
UTC range filtering, previous/next navigation, local search and ID sorting,
detail GET, masked JSON inspection, explicit JSON/CSV exports.

Core tests cover page offsets and request validation. TUI integration tests cover
navigation, details, pagination and explorer execution, but are skipped when
Textual is absent. Next: execute those tests and check terminal layouts.

## Milestone 3: payment-page dashboard implemented

`services/analytics.py` and the app show payment counts, captured/failed counts,
captured monetary totals per currency, recent rows, date bounds and freshness.
Tests verify empty data and prevent currency mixing.

Added independent refund and settlement page samples with separate access errors.
Refund amounts include only processed refunds and stay separated by currency.
Settlement status counts do not assume a currency when absent.
Limitations: no full-period account totals. Next: validate runtime presentation.

## Milestone 4: registry explorer implemented

Dynamic forms show required/optional parameters, description, method, path,
authentication, product availability and official documentation reference.
Requests are validated and limited to registered GET operations. Inspection
shows status, safe query information and masked authorization. Responses use
formatted masked JSON; HTTP errors use local safe descriptions.

Limitations: detailed upstream error bodies are not shown because they can echo
sensitive input. No explorer response export, mutation form or arbitrary URL field.
Next: runtime verification and richer safe diagnostics.

## Milestone 5: intentionally deferred

Future products are disabled. Extend only after reviewing official endpoints,
authentication, access requirements and error/pagination semantics. No financial
mutations are part of the initial implementation.

## Validation record

Initial core run: 31 passed, one export test failed (Path.open does not accept
an opener). Fixed exclusive export using built-in open with mode 0600.
Subsequent run: **35 passed, one TUI module skipped**. Both test runs used Python
3.14 and cached core dependencies. Compileall passed for source code.
Textual/Rich/Ruff installation failed due to terminal DNS restrictions. Linting,
headless TUI, editable packaging and interactive launch remain unverified. This
is a pre-release implementation, not a completed Definition of Done.

## Manual acceptance checklist after dependencies are available

- Launch without .env, verify Settings and help, tab navigation and clean quit.
- Type shortcut letters in every text input; ensure they do not trigger app actions.
- Run mocked TUI tests and inspect 100x32 and 160x50 layouts.
- With separately authorized test credentials, inspect all four resources and
  confirm 403 product-access handling where relevant.
- Check failed requests, empty pages, filters, refresh and rapid navigation.
- Inspect a record and export a masked page to JSON and CSV; check 0600 mode.
- Never use live mutation endpoints for validation.

A GitHub Actions workflow (`.github/workflows/tests.yml`) is included for
Python 3.12–3.14 packaging, Ruff checks, tests and the version command. It has
not been executed here. The actual local launch attempt confirmed missing Rich;
the CLI now reports missing dependencies with an installation instruction.
