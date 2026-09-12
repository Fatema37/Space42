"""HTTP client: returns (body, status), retries transient failures, and logs every
request/response with secrets redacted. No assertions here."""
import http.cookiejar
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.redact import redact, scrub_text

log = logging.getLogger("space42")

# Every request made in this process (redacted). conftest slices it per test for the report.
CALLS: list[dict] = []


class APIClient:
    """One instance == one identity (its Authorization header, or none)."""

    def __init__(self, base_url, *, token=None, timeout=30, max_retries=3, keep_cookies=False):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.last_headers = {}     # response headers of the most recent call (never logged)

        self.session = requests.Session()
        # Login returns the token as a Set-Cookie; a persisted cookie would make later
        # "anonymous" calls authenticated. Identity = the header only — except for the
        # cookie-session tests, which opt in with keep_cookies=True.
        if not keep_cookies:
            self.session.cookies.set_policy(http.cookiejar.DefaultCookiePolicy(allowed_domains=[]))
        # Retry transient failures on idempotent methods only (a timed-out POST may have succeeded).
        retry = Retry(
            total=max_retries, backoff_factor=1, status_forcelist=(429, 502, 503, 504),
            allowed_methods=frozenset({"GET", "PUT", "DELETE"}), raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    def request(self, method, path, *, params=None, json=None, headers=None):
        url = f"{self.base_url}/{path.lstrip('/')}"
        merged = {**self.headers, **(headers or {})}
        merged = {k: v for k, v in merged.items() if v is not None}   # None removes a header
        log.info("%s %s params=%s body=%s", method, url, redact(params), redact(json))
        CALLS.append({"method": method, "path": path, "params": redact(params), "json": redact(json)})

        resp = self.session.request(method, url, params=params, json=json,
                                    headers=merged, timeout=self.timeout)
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": scrub_text(resp.text[:500])}   # non-JSON body: scrub tokens out
        self.last_headers = resp.headers
        log.info("%s %s -> %s body=%.400s", method, url, resp.status_code, redact(body))
        return body, resp.status_code

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)
