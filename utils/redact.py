"""Mask secrets before logging."""
import re

# matched against dict keys, substring + case-insensitive ("token" covers accessToken)
SENSITIVE_KEYS = (
    "authorization", "password", "token", "secret", "cookie",
    "ssn", "ein", "bank", "card", "iban", "crypto", "wallet",
)

# tokens sitting inside a plain string (e.g. a non-JSON error body), no key to match on
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{4,}(?:\.[A-Za-z0-9_-]+){1,2}")
_BEARER_RE = re.compile(r"(Bearer\s+)\S+", re.IGNORECASE)


def redact(value):
    """Mask sensitive dict/list values by key name; also scrub tokens out of any string."""
    if isinstance(value, dict):
        return {k: ("***" if _sensitive(k) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return scrub_text(value)
    return value


def scrub_text(text):
    """Mask JWTs and Bearer tokens inside a plain string (values, not keys)."""
    if not isinstance(text, str):
        return text
    return _JWT_RE.sub("***", _BEARER_RE.sub(r"\1***", text))


def _sensitive(key) -> bool:
    return isinstance(key, str) and any(s in key.lower() for s in SENSITIVE_KEYS)
