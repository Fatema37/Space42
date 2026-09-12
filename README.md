# Space42 — DummyJSON API Security Tests

A small Python (pytest) project that tests the **security** of the public DummyJSON API
(`https://dummyjson.com`) — authentication, role-based access, resource ownership and data
exposure. It logs in as several roles and runs a data-driven **security matrix**.

**Result of the submitted run: 59 tests — 38 pass, 21 findings.** A *finding* is something a
secure API must refuse but DummyJSON allows. The full report is in `evidence/report.html`.

No credentials are needed and none are stored in the repo — the test users are discovered
from the public `/users` directory at run time.

---

## Install

Requires **Python 3.12** (3.10–3.13 also work).

```bash
make install          # creates .venv, installs pinned deps, copies .env.example -> .env
```

Without `make`:

```bash
python3 -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
make test             # whole suite (~25s) -> reports/report.html, junit.xml, findings.md
make report           # open the HTML report
```

Other targets: `make auth | users | matrix | exposure | findings | contract` run one slice;
`make evidence` snapshots the results into `evidence/`; `make help` lists everything.

**Reading the result:** every check is either **documented behaviour** (`contract`, should
pass) or a **security expectation** (`security_hypothesis`, marked "expected to fail" so a
gap is reported as a **finding**, not a broken test). A fully green report is not the goal —
the 21 findings are the point. Nothing is weakened to make the suite pass.

---

## Test strategy

Four identities act on the API: `anonymous`, `normal_user` (user A), `another_user`
(user B), `admin_user`. Tests ask three questions — *who is calling? are they allowed?
what comes back?* Risks were ranked (admin creation / self-promotion / bulk data leak /
cross-user access are the high ones) and tested first; pure-functional REST features
(pagination, sort, search) are left out on purpose. Findings carry a **severity** and an
**OWASP API Top 10** category.

**Scope — why only the user / auth surface.** That is where DummyJSON's security model
lives, so it is where the risk is.

- **`products` is out of scope.** It is a public catalogue with no owner and no roles —
  there is nothing to *authorise*. Testing it would be functional (does search work?), not
  security, and the brief scopes to the user/auth capabilities.
- **`carts` is in scope, and already covered** — it is the *owned resource* in the
  ownership tests (can user A read user B's cart? → rows R02, R11, R16, R20). It needs no
  separate test file or service wrapper: it has no authorisation logic of its own beyond
  ownership, and the matrix reaches its paths directly. A cart-*write* ownership row would
  only re-prove the same "no ownership enforcement" gap the user rows already show.

Extending to a new resource — if the target grew a real authorisation model — is new rows
in the CSV, not new code.

## Architecture

```
tests/  ->  services/(auth,users).py  ->  endpoints.py  ->  utils/api_client.py  ->  DummyJSON
(intent)    one call per operation      all URL paths     the only HTTP sender
```

| File | Role |
|---|---|
| `config.py` | typed settings from env / `.env` |
| `endpoints.py` | every API path, one class per resource |
| `utils/api_client.py` | HTTP client: token header, retries, redacted logging; returns `(body, status)` |
| `utils/redact.py` | masks secrets before anything is logged |
| `services/auth.py`, `services/users.py` | thin wrappers, no assertions |
| `models.py` | pydantic response schemas |
| `auth_fixtures.py` | the four identities | 
| `data/security_matrix.csv` | the security rules — one row per test |
| `utils/reporting.py` | the tables in the HTML report |

Each layer changes for one reason: an API path → `endpoints.py`; a rule → one CSV row;
HTTP behaviour → `api_client.py`; a setting → `.env`.

## Findings (highlights)

Full list with severity, OWASP category and expected-vs-actual status: `evidence/findings.md`
and `evidence/report.html`. The headline ones:

- Anyone can **create an admin account** with no login (`POST /users/add`, `role=admin` → 201).
- A normal user can **make themselves admin**, and read/change/delete **any** user or their carts.
- `GET /users` and `/auth/me` return **passwords, SSNs and bank details** in plain text.
- The session cookie has no `SameSite`, authorises writes by itself, and CORS is open to any origin.

**Root cause:** the JWT carries no role and the server never checks ownership — it knows
*who* you are, not *what you may do*. Signatures *are* verified (tested), so adding a role
claim plus per-request checks would close every authorisation finding.

## Assumptions & limitations

- The `/auth/` prefix is DummyJSON's only auth check; roles are data with no enforcement.
- Writes are simulated (documented) — tests assert "echoed, not saved".
- Runtime credential discovery relies on DummyJSON's own data leak; a real API would need
  seeded test accounts from a secret store.
- Matrix rows assert status codes only; content checks live in the hand-written tests.
- Single-process (serial) to respect the sandbox's ~100 req/min limit.

## Incomplete areas

- The `moderator` role is not exercised (one identity + rows to add).
- CI runs on Python 3.12 only.
- Token expiry is checked from the token's contents, not by waiting for expiry.

## Actual effort

About 11 hours over 11–12 September 2026: ~2.5 h probing the API by hand, ~1.5 h design and
simplification, ~1.5 h core code, ~3 h tests and the matrix, ~1 h reporting, ~1.5 h docs and
clean-checkout checks.

## AI-assisted development

Claude Code (Anthropic) was used as a pair-programmer: design discussion, probing the API,
drafting the code and tests, and two simplification passes that removed machinery I could
not justify. Every file was read and understood before being kept; every finding was
reproduced by hand in Postman; the suite was run against the live API from clean checkouts
on Python 3.12 and 3.13. Responsibility for the submission is mine.
