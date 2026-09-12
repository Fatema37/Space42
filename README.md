# Space42 — DummyJSON API Security Tests

**What this is.** A small Python (pytest) project that checks the security of a web API.
The API is DummyJSON (`https://dummyjson.com`), a free public practice API with users,
logins and shopping carts. The tests log in as different users, try things a user should
**not** be allowed to do, look at what the API returns, and produce a report.

**Result of the submitted run:** 59 tests — **38 pass**, **21 findings**.
A *finding* is something a secure API must refuse but DummyJSON allows.

**No credentials are needed to run it, and none are stored in its configuration or code.**

---

## 1. Quick start

### You need

- **Python 3.12** (3.10–3.13 also work; 3.14 does not) — check with `python3 --version`
- **git** to clone — or just download the zip
- **make** — optional; already on macOS and Linux
- **internet access** — the tests call the live API

No account, API key or credentials are needed.

### Steps

**1. Get the code**

```bash
git clone <repo-url>
cd space42
```

**2. Install**

```bash
make install
```

This creates a private Python environment in `.venv/`, installs the packages listed in
`requirements.txt`, and copies `.env.example` to `.env` (the settings file; defaults work).

Without `make` (for example on Windows):

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Run the tests** — about 25 seconds

```bash
make test        # or:  pytest
```

**4. Read the results**

The console ends with a short summary:

```
=============================== security summary ===============================
contract checks passed: 38    findings: 21
  [medium][auth     ] a refresh token is accepted as an access token
  [high  ][exposure ] public user list exposes password/ssn/ein/bank/crypto
  [high  ][rbac     ] a user must not escalate their own role
  ...
======================= 38 passed, 21 xfailed in 22s =======================
```

Then open the full report:

```bash
make report      # opens reports/report.html
```

In the report: **green** = the API behaved as documented; **orange, marked FINDING** =
the API allowed something a secure API must refuse. Each finding shows the exact request,
the expected status and the actual status.

The results of the submitted run are already in **`evidence/`** (`report.html`,
`junit.xml`, `findings.md`, `console.txt`), so you can read them without running anything.

### Why 21 tests are "expected to fail"

DummyJSON is a practice API, not a secure product. The tests still check what a secure
API *must* do. Those checks are marked "expected to fail" (pytest calls this `xfail`), so a
gap is reported as a **finding** instead of a broken test — and if DummyJSON ever fixes
one, that test turns red so the finding gets updated. No expectation was weakened to make
the run pass.

### If something goes wrong

| Problem | Fix |
|---|---|
| `python3.12: command not found` | install Python 3.12 (macOS: `brew install python@3.12`; otherwise python.org). `make install` uses any 3.10–3.13 it finds |
| `Python 3.10-3.13 is required` | you have 3.14 or older — install 3.12 |
| `make: command not found` | use the three "without make" commands above, then `pytest` |
| `No module named 'pytest'` | the environment isn't active: `source .venv/bin/activate` (or use `make test`) |
| a few tests fail with connection or timeout messages | the public API was slow; run again. Network problems are retried and never counted as security results |
| `make report` only prints a path | open `reports/report.html` in your browser by hand |
| PyCharm shows `import pytest` in red | Settings → Project → Python Interpreter → choose `.venv/bin/python` |

---

## 2. How it works

Every security test asks one of three questions:

1. **Who is calling?** — nobody, a normal user, a *different* normal user, or an admin.
2. **Are they allowed to do this?** — for example, can a normal user delete another user?
3. **What comes back?** — for example, does the response contain someone's password?

### The four identities

At the start of a run the project picks real accounts from the API's public user list and
logs them in. Tests then act as one of these four people:

| Name in the code | Who | Used to check |
|---|---|---|
| `anonymous` | nobody logged in (no token) | does this need a login at all? |
| `normal_user` | an ordinary user (**user A**) | what can a normal user do? |
| `another_user` | a different ordinary user (**user B**) | can user A touch user B's data? |
| `admin_user` | an admin | does an admin get more than a user? |

### The two kinds of test

| Kind | Checks | Expected |
|---|---|---|
| **Documented behaviour** (label: `contract`) | what DummyJSON's own docs promise | pass |
| **Security expectation** (label: `security_hypothesis`) | what a secure, real-world API must do | expected to fail on DummyJSON → reported as a **finding** |

### The conclusion in one sentence

**DummyJSON checks *that* you are logged in, but never checks *what you are allowed to
do*.** Any valid login token can read, change, delete or promote any user.

---

## 3. The files

```
space42/
├── README.md                 this file
├── requirements.txt          Python packages (pinned versions)
├── Makefile                  short commands: make install / test / report / ...
├── pytest.ini                test-runner settings
├── .github/workflows/tests.yml   GitHub Actions: runs the suite on every push
├── .env.example              settings template (copied to .env; contains no secrets)
│
├── config.py                 reads the settings (API address, timeout, retries)
├── endpoints.py              every API URL path, in one place
├── utils/
│   ├── api_client.py         the ONE file that sends HTTP requests (adds the token, logs safely)
│   ├── redact.py             hides passwords, tokens and personal data before anything is logged
│   └── reporting.py          builds the tables in the HTML report
├── services/
│   ├── auth.py               login / me / refresh  → returns (response body, status code)
│   └── users.py              list / get / filter / search / update / delete users
├── models.py                 the fields a login response and a user record must have
├── auth_fixtures.py          creates the four identities
├── conftest.py               shared test setup (settings + a way to build API clients)
│
├── data/security_matrix.csv  THE SECURITY RULES — one row = one test (section 5)
└── tests/
    ├── test_auth.py          login, tokens, refresh — every combination
    ├── test_users.py         the users API works as documented
    ├── test_rbac_matrix.py   runs every row of the CSV
    └── test_data_exposure.py does any response leak sensitive data?
```

**How one test runs:** a test in `tests/` calls a function in `services/` → that uses a
path from `endpoints.py` → `utils/api_client.py` sends it → the answer comes back as
`(body, status)` → the test checks it.

Created when you run (not stored in git): `reports/report.html`, `reports/junit.xml`,
`reports/findings.md`, `logs/pytest.log`.

---

## 4. Commands

| Command | Runs |
|---|---|
| `make test` | everything |
| `make auth` | login and token tests |
| `make users` | users API tests |
| `make matrix` | the security matrix |
| `make exposure` | data-leak tests |
| `make findings` | only the 21 security-expectation tests |
| `make contract` | only the documented-behaviour tests |
| `make report` | open the last HTML report |
| `make evidence` | run everything and copy the results into `evidence/` |
| `make package` | build `../space42-submission.zip` (no `.venv`, caches, logs or `.env`) |
| `make clean` | delete caches, logs and reports |
| `pytest -o log_cli=true` | any run, printing every request and response as it happens |

**On GitHub** the same suite runs automatically on every push and pull request
(`.github/workflows/tests.yml`): it executes `make install` and `make test`, shows the
findings table on the run's summary page, and attaches the report and log as a
downloadable artifact. The run is green when every finding is still a finding, and turns
red if a test really fails — or if DummyJSON quietly fixes something and an expected
failure starts passing.

**To run it by hand:** GitHub → *Actions* tab → *API security tests* → **Run workflow**.
Pick which part to run (`test` = everything, or `auth`, `users`, `matrix`, `exposure`,
`findings`, `contract`) and, optionally, tick *verbose* to see every request
and response in the log. When it finishes, the findings are on the run's summary page and
the report is under *Artifacts*.

---

## 5. The security matrix (`data/security_matrix.csv`)

A spreadsheet-style file. **Each row is one security rule.**

| Column | Meaning | Example |
|---|---|---|
| `actor` | who makes the call | `normal_user` |
| `method`, `path` | the request (`{id}` is filled in when it runs) | `PUT /auth/users/{id}` |
| `target` | whose record: `self` (the actor's own) or `other` (user B's) | `self` |
| `payload` | request body as `key=value` pairs; `{admin_username}` fills in at run time | `role=admin` |
| `expected` | the status a secure API would return | `403` |
| `classification` | `contract` or `security_hypothesis` | `security_hypothesis` |
| `severity`, `owasp` | how serious the gap is, and its OWASP API Top 10 category (finding rows) | `high`, `API3` |
| `observed` | the status seen when the row was written; the report flags it if it ever changes | `200` |
| `rule` | the rule in plain English | a user must not escalate their own role |

That row (R12) means: *a normal user tries to change their own role to admin → a secure
API must answer 403 Forbidden.* DummyJSON answers 200 → finding. The `observed` column lets
the suite say more than "this is a gap": if DummyJSON's answer ever changes (say it starts
returning 500), the report marks that row **⚠ CHANGED**, so the suite detects when a gap
changes shape, not just that it exists.

`tests/test_rbac_matrix.py` reads the file and runs every row.
**To add a test, add a row. To add a role, add one small identity in `auth_fixtures.py`
and use its name in the `actor` column. The test file never changes.**

---

## 6. Findings

All 21 can be reproduced by hand; the report shows the exact request, expected and actual
status for each. Writes on DummyJSON are *simulated* (nothing is saved) — the problem is
that the API **accepts** the request at all.

### 6.1 No permission checks (matrix rows)

| Row | Who | What they did | Should be | Was |
|---|---|---|---|---|
| R03 / R04 | nobody | update / delete a user via `/users/{id}` | 401 | **200** — the public path accepts writes without a login (the `/auth/` path correctly says 401: R17 / R18) |
| R06 / R08 / R09 | normal user | read / update / delete **another** user via `/auth/users/{id}` | 403 | **200** — any login can act on anyone |
| R11 / R20 | normal user / nobody | read another user's carts | 403 / 401 | **200** |
| R12 | normal user | set their own `role` to `admin` | 403 | **200** — self-promotion to admin |
| R19 | nobody | create a user with `role=admin` (`POST /users/add`) | 401 | **201** — anyone can create an admin account |
| R21 / R22 | normal user | set their own `id` to 1 / their `username` to an existing one | 400 / 409 | **200** — identity fields can be changed |

### 6.2 Tokens, cookies and error handling (`test_auth.py`)

| What was tried | Should be | Was |
|---|---|---|
| use the *refresh* token where the *access* token belongs | 401 | **200** |
| use the *access* token to refresh | 401 / 403 | **200** — the API doesn't check which kind of token it got |
| a made-up token | 401 | **500** `invalid token` |
| login with `expiresInMins=-1` | 400 | **500**, with a misleading message |
| the login cookie should carry `SameSite` | present | **missing** — the cookie relies on browser defaults for cross-site requests |
| change data using **only the session cookie** (no header, as a cross-site page could) | 401 / 403 | **200** — no CSRF protection |
| ask, from another website, whether credentialed requests are allowed (CORS) | refused | **allowed** — the API reflects any origin with `Access-Control-Allow-Credentials: true` |

The cookie itself is set correctly with `HttpOnly` and `Secure` (a pass), and "cookie alone
authenticates `/auth/me`" is documented behaviour (a pass). The three findings are what
makes that cookie dangerous: no `SameSite`, cookie-only writes, and permissive CORS.

### 6.3 Data leaks (`test_data_exposure.py`)

`GET /users`, `GET /users/{id}` (no login needed) and `GET /auth/me` return each user's
`password`, `ssn`, `ein`, bank card number / IBAN and crypto wallet in plain text.
The login response correctly leaves the password out, and error messages leak nothing.

### 6.4 Why this happens

The login token (a JWT) only contains who you are — `id, username, email, name, gender,
image` and two timestamps. It has **no role and no permissions**, and the server never
looks your role up. So the server knows *who* is calling and nothing about *what they may
do*. The token's signature *is* checked — `test_auth.py` proves it by editing a token's
payload to add `role: admin` (keeping the original signature) and by trying an unsigned
`alg: none` token; both are rejected. So adding a role to the token plus a check on each
request would fix every permission finding — **without changing a single test here.**

Also seen, not automated: the token is accepted without the word `Bearer`; a user can
promote *another* user (same cause as R08 + R12).

### 6.5 OWASP API Security Top 10 (2023)

Every finding maps to a category. The matrix rows carry `severity` and `owasp` columns, and
the report and `findings.md` show both; the hand-written tests carry the same as markers.

| Category | Findings |
|---|---|
| **API1** Broken Object Level Authorization | R06, R08, R09 (another user's record); R11, R20 (another user's carts) |
| **API2** Broken Authentication | refresh ↔ access token confusion; session cookie has no `SameSite` and authorizes writes on its own (no CSRF) |
| **API3** Broken Object Property Level Authorization | data exposure (list, single user, `/auth/me`); mass assignment (R12 `role`, R21 `id`, R22 `username`) |
| **API5** Broken Function Level Authorization | R19 (anyone creates an admin); R03 / R04 (anonymous writes and deletes on the public path) |
| **API8** Security Misconfiguration | 500 returned for client errors; CORS reflects any origin with `Access-Control-Allow-Credentials: true` |
| **API9** Improper Inventory Management | two versions of the same operation — `/users/{id}` unprotected vs `/auth/users/{id}` protected |

---

## 7. How the work was planned

### 7.1 What the API offers, and what it checks

| Part of the API | Login needed? | What is missing |
|---|---|---|
| Login, "who am I", refresh (`/auth/login`, `/auth/me`, `/auth/refresh`) | — / token | token carries no role; tokens are also set as `HttpOnly; Secure` cookies with no `SameSite`; the cookie alone authorizes writes; CORS allows credentialed calls from any origin |
| Public user directory (`/users`, `/users/{id}`, filter, search) | no | returns passwords and financial data to anyone |
| Public writes (`POST /users/add`, `PUT` / `DELETE /users/{id}`) | no | accepts changes from anyone |
| Protected user routes (`/auth/users/{id}`) | any valid token | no check of *whose* record it is, *what role* you have, or *which fields* you may change |
| Carts (`/users/{id}/carts`, `/auth/carts/user/{id}`) | no / any token | anyone can read anyone's carts |

In short: login is checked only on `/auth/…` paths; ownership, roles and protected
fields are never checked; error responses are clean but use 500 for bad input.

### 7.2 Risks, ranked — this order decided what was tested first

| Priority | Risk | Tested by |
|---|---|---|
| **High** | anyone can create an admin account without logging in | R19 |
| **High** | a normal user can make themselves admin | R12 |
| **High** | passwords and financial data for all users, no login needed | `test_data_exposure.py` |
| **High** | any user can read / change / delete any other user and their carts | R06 R08 R09 R11 R20 |
| Medium | writes accepted without a login on the public path | R03 R04 (compare R17 R18) |
| Medium | the wrong kind of token is accepted (a leaked access token could mint tokens forever) | `test_auth.py` |
| Medium | identity fields (`id`, `username`) can be changed | R21 R22 |
| Medium | the session cookie alone can change data, with no `SameSite` and CORS open to any origin (cross-site attacks) | `test_auth.py` (`TestCookieSession`) |
| Low | bad input answered with 500 instead of 400 | `test_auth.py` |
| Low | login reveals whether a username exists — checked, **not** the case | `test_auth.py` |

Every High risk has a *pair* of matrix rows (the same call as a user and as an admin)
plus checks on the response content. Rows that would only repeat a proven problem were
left out on purpose — the brief scores the choice of risks, not the number of tests.

### 7.3 What each test area covers

| Area in the brief | Where | What is checked |
|---|---|---|
| Authentication and identity | `test_auth.py` | login with valid, wrong, unknown and missing credentials; `/auth/me` returns *you*; wrong password and unknown user get the same answer |
| Token and session handling | `test_auth.py` | the requested expiry is honoured; invalid tokens; wrong kind of token; a payload-tampered token and an `alg:none` token are both rejected (signatures are verified); refresh works and is rejected when invalid; the login cookie is `HttpOnly`/`Secure` but lacks `SameSite`, authorizes writes by itself, and CORS is open to any origin |
| Role-based authorization | matrix (`rbac` rows) | self-promotion; identity fields; admin vs user |
| Resource ownership / cross-user access | matrix (`ownership` rows) | user A on user B's record and carts |
| Data exposure / field-level security | `test_data_exposure.py` | sensitive fields in list, single-user and `/auth/me` responses; error bodies; our own logs |
| API contract / schema | `test_users.py` + `models.py` | the directory lists users; a single user validates against the required-fields schema; filter by role; unknown / invalid id give 404 / 400; simulated writes are echoed but not saved. (Pure-functional REST features — pagination, sort, field-select, search — are left out on purpose: this is a security assessment, not an API conformance suite.) |
| Negative, boundary and error cases | tests marked `negative` | 400 / 401 / 403 / 404 paths, invalid ids, invalid expiry |
| Test state, isolation, concurrency | `test_auth.py` + design | a login's cookie never leaks into anonymous calls (identity comes only from the `Authorization` header — tested); simulated writes are asserted as simulated (`test_users.py`); identities are built once per run; tests run one at a time |
| Resilience / operational | `utils/api_client.py` (design) | retries happen only for safe-to-repeat requests (GET / PUT / DELETE, never POST) on timeouts, `429`, and `502` / `503` / `504` — **never 500**, because a 500 is itself a finding here; about 70 requests per run, one at a time, under the API's 100-per-minute limit |

Beyond status codes, tests also check: response fields, that login returns the right user,
the token's expiry time, that two responses are identical (no username guessing), that
sensitive fields are absent, and that "updated" data was not actually saved.

### 7.4 Left out on purpose

- **Brute-force / lockout tests** — the brief forbids credential stuffing on the shared API.
- **Logout** — DummyJSON has no logout endpoint.
- **Waiting for a token to expire** — the expiry time inside the token is checked instead.
- **The `moderator` role** — user and admin are the two ends of the ladder; adding
  moderator is one identity plus matrix rows.
- **A row for "user promotes another user"** — same cause as R08 + R12.

### 7.5 Risks found beyond the brief's list

- Anyone can create an **admin** account (R19).
- The **wrong kind of token** is accepted in both directions.
- **Identity fields** can be changed; an existing username can be taken over (R21, R22).
- **Cookie replay** made "anonymous" tests pass falsely — fixed in the client, guarded by a test.
- **Cookie session exposure** — the same cookie has no `SameSite`, can change data on its own, and the API's CORS answers any origin with credentials allowed; together that is a cross-site request forgery risk.

---

## 8. Design choices

| Choice | Instead of | Why |
|---|---|---|
| pytest + `requests` | Playwright / TypeScript, RestAssured, `httpx` | pytest's parameter and expected-failure features fit a rules-in-a-file approach; nothing needs async |
| plain functions returning `(body, status)` | classes per service | less to read; the identity is passed in, so functions hold no state |
| rules in a CSV | rules written in Python | a reviewer can read or edit a spreadsheet; the brief asks for an external, data-driven matrix |
| "expected to fail" for security expectations | only asserting what DummyJSON does | keeps the secure expectation in code and alerts if the API ever changes |
| accounts discovered from `/users` at run time | secrets in `.env` | no secrets in the framework's config or code; that discovery *works* is finding #1 |
| identity comes only from the `Authorization` header; cookies are ignored | letting the HTTP session keep cookies | login also sets a cookie; a session would replay it and make "anonymous" tests pass falsely (the cookie-session tests opt back in on purpose) |
| retries only for GET / PUT / DELETE, on `429` / `502` / `503` / `504` — never 500 | retrying everything, or retrying all 5xx | a timed-out POST may have succeeded (retrying could duplicate); and a 500 here is a finding, not a blip, so retrying it would hide the finding |
| tests run one at a time | parallel workers | about 70 requests per run, well under the API's rate limit |
| pytest's own logging and pytest-html | a custom logger or reporter | less code to own; redaction happens once, in the client |
| a single self-contained HTML report | Allure | opens from a clean checkout with no extra tools |

Kept deliberately small: no BDD layer, no async, no custom plugins — about 950 lines of
Python. **When something changes, only one file changes:** an API path → `endpoints.py`;
a request shape → `services/`; a security rule → one CSV row; HTTP behaviour →
`api_client.py`; a setting → `.env`.

---

## 9. Evidence, and keeping information safe

**What a run produces**

| File | Contains |
|---|---|
| `reports/report.html` | totals; the matrix with expected vs actual status, colour-coded; every other test with the exact API calls it made (bodies redacted); the findings; per-test detail |
| `reports/findings.md` | the findings as a table, regenerated each run |
| `reports/junit.xml` | machine-readable results |
| `logs/pytest.log` | every request and response of the run, secrets replaced by `***` |
| `evidence/` | a copy of the four files above from the submitted run |

**How secrets are kept out**

- No credentials are stored in the framework's config or code: accounts are discovered at
  run time; `.env.example` holds only a URL, a timeout and a retry count; `.env` is git-ignored.
- Tokens are hidden from printing (`AuthContext` excludes them from `repr`), so they can't
  appear in tracebacks.
- `utils/redact.py` replaces `password`, anything containing `token`, `ssn`, `ein`, `bank`,
  `card`, `iban`, `crypto` and `wallet` with `***` **inside the client**, before any log
  line or report cell is written. The `Authorization` header is never logged at all.
- This is tested (`test_data_exposure.py`), and the report, log and evidence files were
  searched for a real password after a full run — zero matches.
- Cookies are ignored by the client, so one identity can never leak into another request
  (a test in `test_auth.py` proves it).
- The report shows request bodies (redacted) and status codes — never full user records.

---

## 10. Assumptions

- The `/auth/` prefix is DummyJSON's only documented login check; roles are plain data
  fields with no documented enforcement.
- A secure API would: require a login for every write; let users touch only their own
  records; treat `id`, `username` and `role` as protected fields; answer bad input with 4xx,
  not 500; never return passwords or financial identifiers.
- DummyJSON's writes are simulated (documented) — tests assert "echoed back, not saved".
- Network slowness is not a defect: transient failures are retried and never asserted on.

## 11. Limitations

- Discovering accounts at run time **relies on DummyJSON's own data leak**. A real API
  would need test accounts provided from a secret store.
- Runs in one process; parallel runs would need changes.
- Matrix rows check status codes only; content checks live in the hand-written tests.
- Paths appear both in `endpoints.py` and in the CSV — accepted, so the matrix can be
  read without opening code.
- DummyJSON publishes no API specification, so automatic contract fuzzing is not included.

## 12. Incomplete areas

- The `moderator` role is not exercised (one identity + rows to add).
- CI runs on Python 3.12 only; 3.10–3.13 were verified by hand, not in CI (each CI run
  makes ~70 calls to the shared API, so a version matrix was left out deliberately).
- Token expiry is checked from the token's contents, not by waiting for it to expire.

## 13. Effort and where it went

Total: **about 11 hours** across 11–12 September 2026 (the three-day window was not fully used).

| Phase | Hours | Why it got this share |
|---|---|---|
| Reading the brief; trying the API by hand (curl / Postman) | ~2.5 | everything else depends on knowing what the API *really* does; this is where "no permission checks at all" and "the token has no role" came from |
| Design, then two rounds of simplification | ~1.5 | the first design was over-built (custom logger, retry loop, failure hooks); it was cut back to what I can explain line by line |
| Core code — client, settings, endpoints, identities | ~1.5 | small on purpose; the cookie bug was found and fixed here |
| Tests and the security matrix | ~3 | matrix rows written in user/admin pairs from the ranked risks; hand-written tests cover what a status code can't |
| Readable reporting | ~1 | expected-vs-actual tables so a reviewer needs no Python to read the findings |
| README, evidence, clean-checkout checks | ~1.5 | verified from fresh copies on two Python versions and from the zip |

**Most valuable work, in order** — with one hour I would keep only the first two:
1. Trying the live API to learn what it actually does (every finding traces to this).
2. The two kinds of test plus the CSV matrix (turns the gap into evidence, not a red run).
3. The "identity comes only from the header" fix (without it the anonymous results are wrong).
4. Expected-vs-actual reporting.
5. Documentation and packaging.

## 14. What is in the submission (the brief's Table 4)

| Deliverable | Where |
|---|---|
| Source repository / zip — code, dependencies, config example | this repository (`make package` builds the zip); `requirements.txt`; `.env.example` |
| README — installation, execution, strategy, architecture, assumptions, limitations, effort, incomplete areas, AI disclosure | sections 1, 1, 2 + 7, 3 + 8, 10, 11, 13, 12, 15 |
| Security matrix — external, data-driven, used by the framework | `data/security_matrix.csv`, run by `tests/test_rbac_matrix.py` |
| Test results — a generated report showing scenarios and failures | `evidence/report.html` (+ `junit.xml`, `findings.md`, `console.txt`); regenerate with `make evidence` |
| Runs from a clean checkout / extracted archive | verified with `make install && make test` and with the manual commands, from fresh copies on Python 3.12 and 3.13, and from the zip |

## 15. AI-assisted development

**Tool used:** Claude Code (Anthropic), as a pair-programmer throughout.

**How it helped:** discussing the design and trade-offs; probing DummyJSON to establish its
real behaviour; drafting the framework files, the test cases and the reporting; and two
rounds of simplification that removed machinery I could not justify (a custom logger, a
hand-written retry loop, a failure-attachment hook) in favour of built-ins.

**How the output was reviewed and validated:** I read and understood every file before
keeping it, and cut anything I could not explain line by line. Every finding was reproduced
by hand in Postman. The full suite was run against the live API (`make test`) from a clean
checkout on Python 3.12 and 3.13 and from the extracted zip, and the report, log and
evidence files were searched for real tokens and passwords (zero matches). The framework
also surfaced a bug in itself — a login cookie was being replayed, so an "anonymous" test
passed for the wrong reason — which I had to understand to fix and now guard with a test.

Responsibility for the correctness, security, maintainability and explainability of the
submission is mine.
