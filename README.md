# RZPulse

A keyboard-driven, read-only terminal workspace for Razorpay. Built with Python
3.12+, Textual, Rich, httpx and Pydantic. This is a TUI application that connects
directly to official Razorpay HTTPS APIs; it has no backend service.

**RZPulse is an independent, unofficial open-source project and is not affiliated with or endorsed by Razorpay.**

Initial implementation / pre-release: core tests pass locally; full TUI runtime
validation remains pending because required UI packages could not be installed
in the development environment. See [development status](docs/development.md).

## Features

- Payments, Orders, Refunds and Settlements: lazy pagination and detail requests.
- UTC date filtering, current-page search and identifier sorting.
- Dashboard with explicitly scoped payment, refund and settlement page samples.
- Registry-driven API Explorer with parameter forms for eight verified GET operations.
- Masked JSON inspection and explicit current-page JSON/CSV exports.
- Visible TEST/LIVE mode, configuration guidance without credentials, and keyboard help.
- Distinct authentication, permissions, missing resource, throttling and server errors.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
rzpulse
```

Requires Python 3.12 or later and access to PyPI (or an offline wheelhouse).
Run `rzpulse --version` or `python -m rzpulse` as alternatives. A terminal of
at least 100 columns and 32 rows is recommended. Smaller terminals can scroll,
but compact layout validation is pending.

## Configuration

Edit `.env` in the directory from which you launch the app:

```dotenv
RZP_MODE=test
RZP_TEST_KEY_ID=rzp_test_your_key_id
RZP_TEST_KEY_SECRET=your_key_secret
```

For live access, explicitly set `RZP_MODE=live` and provide
`RZP_LIVE_KEY_ID` / `RZP_LIVE_KEY_SECRET`. Generic `RZP_KEY_ID` and
`RZP_KEY_SECRET` are accepted when the corresponding mode-specific value is
absent. Environment variables override `.env` for the same name. Mode-specific
names take priority over generic names. The application never discovers or
loads other credential files automatically. Restart after configuration changes.

Without valid local configuration, the app opens Settings and makes no requests.
Local validation checks presence, placeholders, whitespace and mode/key prefix;
it cannot verify permissions before contacting Razorpay.

## Usage and keys

Use Tab to focus the sidebar, choose a resource and press Enter. Focus a table
row and press Enter to fetch its detail JSON. Previous/Next retrieves one page
at a time. Search and Sort ID apply only to the loaded page. Press `f` to enter
UTC date bounds; leave both blank to clear the range. Explorer exposes all
implemented parameters, including Order authorized/receipt filters.

| Key | Action |
| --- | --- |
| Tab / Shift+Tab | Move focus |
| j / k, arrows | Move selected table row |
| Enter | Activate control or inspect row |
| Esc | Close modal / leave input |
| / | Search visible page |
| r | Refresh resource or dashboard |
| f | Date filters |
| e | Export visible page |
| ? | Help |
| Ctrl+P | Textual command palette |
| q | Quit outside text input |

Exports require an explicit destination ending in `.csv` or `.json`, never
overwrite files, and use owner-only file permissions on POSIX. CSV cells are
protected against spreadsheet formula interpretation. Parent directories must
already exist. Explorer results are inspected on screen; resource pages support
export.

## Supported APIs and data scope

Only list and fetch-by-ID GET operations for Payments, Orders, Refunds and
Settlements are enabled. See [verified coverage and official references](docs/api-coverage.md).
Customers, Subscriptions, Payment Links and Invoices are marked future/unavailable.
No mutation endpoints are enabled.

Dashboard metrics describe **one loaded payment page**, never an account-wide
total. Captured and failed are counted by payment status. Captured amounts are
grouped by currency and never converted or combined. Refund counts and processed refund amounts come from a separate refund page;
settlement counts and processed counts come from a separate settlement page.
Each sample uses the same filters and offset and can fail independently. A full page does
not prove another record exists. Filters and freshness are displayed explicitly.

## Screenshots

No screenshot is included yet. Capture a redacted terminal screenshot only after
runtime verification; do not include credentials or customer data. No fabricated
screenshots or normal-mode payment fixtures are shipped.

## Security

Keep `.env` private (`chmod 600 .env`); it and `*.env` are ignored by Git.
Secrets are represented with Pydantic SecretStr. Requests use verified TLS,
Basic Auth, a fixed official host, no redirects and no environment proxies.
No telemetry or response persistence is enabled. API errors use safe local text
rather than echoing upstream messages. Details and exports mask known sensitive
fields, nested free-form notes, and exact credential values. Original responses
remain in process memory for inspection through the integration layer.

Masking is conservative, not a guarantee that arbitrary future API fields are
non-sensitive. Review exports before sharing. Only use keys and account resources
you are authorized to access. No financial mutations or permission bypasses exist.

## Development and contributing

```bash
pip install -e '.[dev]'
pytest
ruff check .
ruff format --check .
```

See [architecture](docs/architecture.md) and [development](docs/development.md).
Contributions should include official endpoint references, safe parameter
validation, mocked tests and documentation. Never commit secrets or real customer
responses. Report security problems privately to the repository maintainer;
public issues should contain only redacted diagnostics.

## Roadmap

1. Verify packaging and TUI headless/manual behavior in a network-enabled environment.
2. Improve compact-terminal layouts, sorting and richer detail presentation.
3. Add structured safe API diagnostics and richer detail panels.
4. Expand read-only products after per-product authentication/access research.
5. Consider mutations only with explicit confirmation, permission checks and
   documented idempotency guarantees; they are outside this release.

MIT licensed.
