"""Data exposure: sensitive fields must not leak through responses, errors, logs or reports.

contract            = DummyJSON's documented behaviour (expected PASS)
security_hypothesis = what a production service should do; strict xfail = documented finding"""
import pytest

from services import auth, users
from utils.redact import redact

pytestmark = pytest.mark.exposure

# Fields that must never appear in any API response, whoever asks.
SENSITIVE = {"password", "ssn", "ein", "bank", "crypto"}


class TestUserResponses:

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("high")
    @pytest.mark.owasp("API3")
    @pytest.mark.xfail(reason="FINDING: public user list exposes password/ssn/ein/bank/crypto")
    def test_public_user_list_has_no_sensitive_fields(self, anonymous):
        body, status = users.list_users(anonymous.api_client, limit=5)
        assert status == 200
        leaked = {f for u in body["users"] for f in SENSITIVE & set(u)}
        assert not leaked, f"sensitive fields exposed in GET /users: {sorted(leaked)}"

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("high")
    @pytest.mark.owasp("API3")
    @pytest.mark.xfail(reason="FINDING: public single-user record exposes password/ssn/ein/bank/crypto")
    def test_public_single_user_has_no_sensitive_fields(self, anonymous, another_user):
        body, status = users.get_user(anonymous.api_client, another_user.user_id)
        assert status == 200
        leaked = SENSITIVE & set(body)
        assert not leaked, f"sensitive fields exposed in GET /users/{{id}}: {sorted(leaked)}"

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("high")
    @pytest.mark.owasp("API3")
    @pytest.mark.xfail(reason="FINDING: /auth/me returns the caller's own password")
    def test_me_has_no_password_even_for_owner(self, normal_user):
        body, status = auth.me(normal_user.api_client)
        assert status == 200
        assert "password" not in body, "a password must never be returned, not even to its owner"

    @pytest.mark.contract
    def test_login_response_has_no_password(self, anonymous):
        user = users.find_users_by_role(anonymous.api_client, "user")[0]
        body, status = auth.login(anonymous.api_client, user["username"], user["password"])
        assert status == 200
        assert "password" not in body


class TestErrorResponses:

    @pytest.mark.contract
    def test_errors_reveal_nothing_internal(self, anonymous, make_client):
        unauthorised = auth.me(anonymous.api_client)[0]                     # 401
        server_error = auth.me(make_client(token="garbage.token.here"))[0]  # 500
        for body in (unauthorised, server_error):
            assert set(body) == {"message"}, f"error body has extra fields: {sorted(body)}"
            assert not any(w in body["message"].lower() for w in ("traceback", "stack", "exception"))


class TestLogRedaction:

    @pytest.mark.contract
    def test_redaction_masks_sensitive_values(self):
        record = {"id": 1, "password": "secret", "accessToken": "eyJ", "ssn": "123",
                  "bank": {"cardNumber": "4111", "iban": "DE00"}, "crypto": {"wallet": "0xabc"},
                  "address": {"city": "Phoenix"}}
        safe = redact(record)
        assert safe["password"] == safe["accessToken"] == safe["ssn"] == safe["bank"] == safe["crypto"] == "***"
        assert safe["id"] == 1 and safe["address"] == {"city": "Phoenix"}   # non-sensitive untouched
