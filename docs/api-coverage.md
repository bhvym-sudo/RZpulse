# API research and coverage

Research date: 2026-10-20. Official documentation is the source of truth;
SDK/CLI source was reviewed for integration patterns, not treated as proof of
account entitlement. No authenticated requests were made during development.

## Implemented registry (all GET, read only)

| Resource | List | Detail | Implemented query parameters |
| --- | --- | --- | --- |
| Payments | `/v1/payments` | `/v1/payments/{id}` | count, skip, from, to |
| Orders | `/v1/orders` | `/v1/orders/{id}` | count, skip, from, to, authorized, receipt |
| Refunds | `/v1/refunds` | `/v1/refunds/{id}` | count, skip, from, to |
| Settlements | `/v1/settlements` | `/v1/settlements/{id}` | count, skip, from, to |

Sources for each resource:

- [Payment listing](https://razorpay.com/docs/api/payments/fetch-all-payments/)
  and [detail](https://razorpay.com/docs/api/payments/fetch-with-id/).
- [Order listing](https://razorpay.com/docs/api/orders/fetch-all/)
  and [detail](https://razorpay.com/docs/api/orders/fetch-with-id/).
- [Refund listing](https://razorpay.com/docs/api/refunds/fetch-all/)
  and [detail](https://razorpay.com/docs/api/refunds/fetch-with-id/).
- [Settlement listing](https://razorpay.com/docs/api/settlements/fetch-all/)
  and [detail](https://razorpay.com/docs/api/settlements/fetch-with-id/).

All four listings document count/skip pagination, with up to 100 records per
request and default count 10. RZPulse requests 25. Collection `count` describes
the returned collection, not the account-wide total. A full page only means
another page *may* exist. Pages are fetched on demand, and concurrent account
activity can shift offset pagination. Date parameters are UNIX seconds.
The UI converts UTC dates into inclusive day boundaries. Orders additionally
support authorized (0/1) and receipt through the Explorer. Documented order
expansions are intentionally excluded from this release.

## Authentication, hosts and errors

[API introduction](https://razorpay.com/docs/api/) identifies
`https://api.razorpay.com/v1` as the usual gateway, while Route account APIs use
v2. This release fixes the host and uses only the four v1 resources above.
[Authentication](https://razorpay.com/docs/api/authentication/) specifies Basic
Auth using a key ID/secret pair, with separate test/live keys. The selected key
prefix must match the configured mode. Local validation cannot establish key
validity or merchant authorization; only API responses can do that.

[Errors](https://razorpay.com/docs/errors) describe the error object;
resource pages include examples with code, description, source, step, reason,
and metadata. RZPulse maps HTTP status into structured exceptions and deliberately
does not echo upstream descriptions, which may contain sensitive values.
401 means check credentials; 403 can mean missing product access or permissions;
404 means unavailable record in this account/mode; 429 means throttling;
5xx means server failure. Some resource docs show invalid keys as HTTP 400,
so status alone cannot identify every authentication failure.

No stable universal requests-per-second quota was established from the reviewed
pages. No fixed quota is claimed. RZPulse respects Retry-After seconds and HTTP
dates when present, otherwise uses exponential delay with jitter, at most three
GET attempts. Cooldowns over 60 seconds are surfaced without an early retry.
No mutations are registered, executed, or retried. This is not a financial
idempotency implementation.

## Other documented products: unavailable in this release

The [official documentation index](https://razorpay.com/docs/llms.txt) inventories
customers, subscriptions/plans, payment links, invoices, disputes, QR codes,
Route/accounts/transfers, Smart Collect/virtual accounts, documents, recurring
payments, partner APIs, RazorpayX contacts/fund accounts/payouts and transactions.
This inventory is not a claim that all endpoints were reviewed or implemented.
The sidebar explicitly disables the four planned expansion sections.

[Authentication documentation](https://razorpay.com/docs/api/authentication/)
separately describes generating RazorpayX credentials. Do not infer that the
Payment Gateway pair authorizes RazorpayX or partner products.
[Fetch payouts](https://razorpay.com/docs/api/x/payouts/fetch-all/)
requires an account identifier in addition to authentication; its test/live
identifiers differ. Partner onboarding requires participation in the
[Partner Program](https://razorpay.com/partners/onboarding-apis/).
Product activation, region, API versions, OAuth scopes and IP restrictions
must be researched per product before expansion. Their full authentication
matrices and numeric rate limits remain documentation gaps here. No guessed
endpoints, additional credentials, or product bypasses are implemented.

## Official CLI and SDK review

- [CLI repository](https://github.com/razorpay/razorpay-cli) is a Go command-line
  tool covering a broader resource set. Its
  [HTTP client](https://github.com/razorpay/razorpay-cli/blob/master/api/client.go)
  uses Basic Auth, a timeout, query encoding and generic HTTP methods. Its
  configurable base host is deliberately not adopted here to protect keys.
- [Python SDK](https://github.com/razorpay/razorpay-python) uses resource objects
  injected with a shared client. Its
  [client source](https://github.com/razorpay/razorpay-python/blob/master/razorpay/client.py)
  uses a synchronous requests session and configurable retry options. RZPulse
  uses an independent async httpx implementation so requests do not block the TUI.
- [Best practices](https://razorpay.com/docs/api/best-practices/) discusses secret
  protection and zero/three-decimal currencies. Unknown currencies are shown in
  original subunits; absent settlement currency is never guessed.

## Verification limits

Official pages were reachable through the research browser. The shell could
not resolve PyPI, so Textual/Rich/Ruff and the build backend could not be
installed. Core dependencies were recovered from local pip cache. Mocked core
checks run locally; headless TUI tests require dependency installation. No
live/test account integration certification or full product audit is claimed.
