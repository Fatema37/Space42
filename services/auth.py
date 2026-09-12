"""Auth service. Each function returns (body, status) and never asserts."""
from endpoints import AuthAPI

TOKEN_TTL_MINS = 30   # longer than a full run, so each identity logs in once


def login(api_client, username, password, expires_in_mins=TOKEN_TTL_MINS):
    payload = {"username": username, "password": password, "expiresInMins": expires_in_mins}
    return api_client.post(AuthAPI.login(), json=payload)


def me(api_client):
    return api_client.get(AuthAPI.me())


def refresh(api_client, refresh_token=None):
    payload = {"refreshToken": refresh_token} if refresh_token else {}
    return api_client.post(AuthAPI.refresh(), json=payload)
