"""All combinations for the 3 auth operations: login, me, refresh.

contract            = DummyJSON's documented behaviour (expected PASS)
security_hypothesis = what a production service should do; strict xfail = documented finding"""
import base64
import json

import pytest

from endpoints import UsersAPI
from models import LoginResponse
from services import auth, users

pytestmark = pytest.mark.auth


class TestLogin:

    @pytest.mark.contract
    def test_valid_credentials_return_tokens(self, anonymous):
        user = users.find_users_by_role(anonymous.api_client, "user")[0]      # real creds from /users
        body, status = auth.login(anonymous.api_client, user["username"], user["password"])
        assert status == 200
        parsed = LoginResponse(**body)                                  # schema oracle
        assert parsed.id == user["id"] and parsed.username == user["username"]
        assert parsed.accessToken and parsed.refreshToken

    @pytest.mark.contract
    def test_requested_expiry_is_honoured(self, normal_user):
        # Read the JWT payload: its lifetime (exp - iat) must equal the expiresInMins we asked for.
        payload = normal_user.access_token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        assert claims["exp"] - claims["iat"] == auth.TOKEN_TTL_MINS * 60

    @pytest.mark.contract
    @pytest.mark.negative
    def test_wrong_password_rejected(self, anonymous, normal_user):
        body, status = auth.login(anonymous.api_client, normal_user.username, "wrong-password")
        assert status == 400 and "message" in body

    @pytest.mark.contract
    @pytest.mark.negative
    def test_wrong_password_and_unknown_user_look_identical(self, anonymous, normal_user):
        """No user enumeration: the API must not reveal whether the username exists."""
        wrong_pw_body, wrong_pw_status = auth.login(anonymous.api_client, normal_user.username, "wrong-password")
        no_user_body, no_user_status = auth.login(anonymous.api_client, "no-such-user-xyz", "wrong-password")
        assert wrong_pw_status == no_user_status
        assert wrong_pw_body["message"] == no_user_body["message"]

    @pytest.mark.contract
    @pytest.mark.negative
    def test_missing_credentials_rejected(self, anonymous):
        body, status = auth.login(anonymous.api_client, "", "")
        assert status == 400 and "message" in body

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("low")
    @pytest.mark.owasp("API8")
    @pytest.mark.xfail(reason="FINDING: invalid expiresInMins returns 500 instead of a 400 validation error")
    def test_invalid_expiry_rejected_with_400(self, anonymous):
        user = users.find_users_by_role(anonymous.api_client, "user")[0]
        body, status = auth.login(anonymous.api_client, user["username"], user["password"], expires_in_mins=-1)
        assert status == 400, f"expected 400 for expiresInMins=-1, got {status}"


class TestMe:

    @pytest.mark.contract
    def test_valid_token_returns_own_user(self, normal_user):
        body, status = auth.me(normal_user.api_client)
        assert status == 200
        assert body["id"] == normal_user.user_id and body["username"] == normal_user.username

    @pytest.mark.contract
    @pytest.mark.negative
    def test_no_token_rejected(self, anonymous):
        body, status = auth.me(anonymous.api_client)
        assert status == 401 and "message" in body

    @pytest.mark.contract
    @pytest.mark.negative
    def test_anonymous_stays_anonymous_after_a_login_on_the_same_client(self, anonymous):
        """Login sets a cookie; the client must not replay it as authentication."""
        user = users.find_users_by_role(anonymous.api_client, "user")[0]
        assert auth.login(anonymous.api_client, user["username"], user["password"])[1] == 200
        body, status = auth.me(anonymous.api_client)          # same client, still no Authorization header
        assert status == 401, "a cookie from the login leaked into an anonymous request"

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("low")
    @pytest.mark.owasp("API8")
    @pytest.mark.xfail(reason="FINDING: invalid token returns 500 'invalid token' instead of 401")
    def test_invalid_token_rejected_with_401(self, make_client):
        body, status = auth.me(make_client(token="garbage.token.here"))
        assert status == 401, f"expected 401 for an invalid token, got {status}"

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("medium")
    @pytest.mark.owasp("API2")
    @pytest.mark.xfail(reason="FINDING: a refresh token is accepted as an access token")
    def test_refresh_token_not_accepted_as_access_token(self, normal_user, make_client):
        body, status = auth.me(make_client(token=normal_user.refresh_token))
        assert status == 401, f"expected 401 when a refresh token is used as Bearer, got {status}"

    @pytest.mark.contract
    def test_tampered_token_is_rejected(self, normal_user, make_client):
        """Signatures ARE verified: editing the payload (role=admin) but keeping the original
        signature must be rejected. This is why adding a role claim would be trustworthy."""
        header, payload, sig = normal_user.access_token.split(".")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        claims["role"] = "admin"
        forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        body, status = auth.me(make_client(token=f"{header}.{forged}.{sig}"))
        assert status != 200, "a token with an edited payload was accepted — signatures are not verified"

    @pytest.mark.contract
    def test_alg_none_token_is_rejected(self, normal_user, make_client):
        """The classic 'alg: none' bypass (an unsigned token) must be rejected."""
        payload = normal_user.access_token.split(".")[1]
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        body, status = auth.me(make_client(token=f"{header}.{payload}."))
        assert status != 200, "an unsigned (alg:none) token was accepted"


class TestRefresh:

    @pytest.mark.contract
    def test_valid_refresh_token_issues_usable_access_token(self, anonymous, normal_user, make_client):
        body, status = auth.refresh(anonymous.api_client, normal_user.refresh_token)
        assert status == 200 and body.get("accessToken")
        me_body, me_status = auth.me(make_client(token=body["accessToken"]))
        assert me_status == 200 and me_body["id"] == normal_user.user_id

    @pytest.mark.contract
    @pytest.mark.negative
    def test_missing_refresh_token_rejected(self, anonymous):
        body, status = auth.refresh(anonymous.api_client)
        assert status == 401 and "message" in body

    @pytest.mark.contract
    @pytest.mark.negative
    def test_invalid_refresh_token_rejected(self, anonymous):
        body, status = auth.refresh(anonymous.api_client, "not-a-real-token")
        assert status in (401, 403) and "message" in body

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("medium")
    @pytest.mark.owasp("API2")
    @pytest.mark.xfail(reason="FINDING: an access token is accepted as a refresh token")
    def test_access_token_not_accepted_as_refresh_token(self, anonymous, normal_user):
        body, status = auth.refresh(anonymous.api_client, normal_user.access_token)
        assert status in (401, 403), f"expected rejection when an access token is used to refresh, got {status}"


def _cookie_flags(set_cookie: str) -> set:
    """Attribute NAMES from a Set-Cookie header, lower-cased. Values (the tokens) are
    dropped on purpose so they can never appear in an assertion message or the report."""
    return {part.split("=", 1)[0].strip().lower() for part in set_cookie.replace(",", ";").split(";")}


class TestCookieSession:
    """Login also sets the tokens as cookies (documented). These tests use a client that
    KEEPS cookies and sends no Authorization header, so the cookie is the only credential."""

    @pytest.fixture
    def cookie_client(self, make_client, anonymous):
        client = make_client(keep_cookies=True)
        user = users.find_users_by_role(anonymous.api_client, "user")[0]
        assert auth.login(client, user["username"], user["password"])[1] == 200
        client.user_id = user["id"]
        client.cookie_flags = _cookie_flags(client.last_headers.get("Set-Cookie", ""))
        return client

    @pytest.mark.contract
    def test_login_sets_httponly_secure_cookies(self, cookie_client):
        assert {"accesstoken", "httponly", "secure"} <= cookie_client.cookie_flags

    @pytest.mark.contract
    def test_cookie_alone_authenticates_me(self, cookie_client):
        body, status = auth.me(cookie_client)                      # no Authorization header
        assert status == 200 and body["id"] == cookie_client.user_id

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("medium")
    @pytest.mark.owasp("API2")
    @pytest.mark.xfail(reason="FINDING: session cookies have no SameSite attribute")
    def test_cookie_has_samesite_attribute(self, cookie_client):
        assert "samesite" in cookie_client.cookie_flags, "cookie relies on browser defaults for cross-site requests"

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("medium")
    @pytest.mark.owasp("API2")
    @pytest.mark.xfail(reason="FINDING: the session cookie alone authorizes state-changing requests (no CSRF protection)")
    def test_cookie_alone_cannot_change_data(self, cookie_client):
        body, status = users.update_user(cookie_client, cookie_client.user_id, {"lastName": "Test"})
        assert status in (401, 403), f"expected a cookie-only write to be refused, got {status}"

    @pytest.mark.security_hypothesis
    @pytest.mark.severity("medium")
    @pytest.mark.owasp("API8")
    @pytest.mark.xfail(reason="FINDING: CORS reflects any origin with Access-Control-Allow-Credentials: true")
    def test_cors_does_not_allow_credentials_from_any_origin(self, anonymous, normal_user):
        anonymous.api_client.request("OPTIONS", UsersAPI.get_protected(normal_user.user_id),
                                     headers={"Origin": "https://evil.example",
                                              "Access-Control-Request-Method": "PUT"})
        h = anonymous.api_client.last_headers
        reflected = h.get("Access-Control-Allow-Origin") == "https://evil.example"
        credentials = h.get("Access-Control-Allow-Credentials", "").lower() == "true"
        assert not (reflected and credentials), "any website may make credentialed requests to this API"
