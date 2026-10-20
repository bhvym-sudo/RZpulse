# Architecture

`config.py` merges explicit `.env` and environment values into immutable settings.
It selects test/live credentials without fallback to the opposite mode. The app
catches configuration failures and renders instructions without making requests.

`api/registry.py` owns the eight verified operations, documentation, availability,
authentication, method and parameter metadata. Each operation validates input
before constructing a path. Pydantic query models reject unknown parameters and
bound pagination. Identifiers use resource-specific prefixes and alphanumeric
suffixes, preventing traversal, query injection and arbitrary host access.

`api/client.py` owns a long-lived asynchronous httpx client, Basic Auth, TLS,
timeouts, response validation and bounded retry policy. Responses remain original
Python JSON objects. Collections are validated without throwing away additional
fields. Only registered GET operations can execute. Mutation method metadata can
be represented in the registry later, but execution must remain separately gated
until request models and financial safeguards are implemented. POST/PATCH/PUT/
DELETE are intentionally unavailable, rather than exposed as an unsafe generic
escape hatch.

`app.py` contains the shared resource view, dashboard, dynamic explorer, detail
modal, export modal and settings. Shared resource rendering prevents four
nearly-identical screen implementations from diverging. Exclusive cancellable
Textual workers keep HTTP operations asynchronous. Navigating cancels the previous
request group. No background polling or exhaustive downloads occur.

`services/analytics.py` calculates page-scoped metrics without currency mixing.
`services/export.py` writes redacted snapshots only on explicit user action.
`utils/security.py` centralizes masking at presentation boundaries; error messages
never include upstream bodies. `utils/formatting.py` formats timestamps in UTC and
uses Decimal for monetary values, preserving unknown currency subunits.

Tests use httpx MockTransport, synthetic records and Textual's headless pilot.
No automated test needs a merchant credential or performs a financial operation.

Future extraction into screen/widget modules should follow actual complexity.
Future product registries must specify their own host/version/authentication and
account access requirements. Never repurpose Payment Gateway credentials for a
new service merely because its API resembles these resources.
