"""The identities tests act as. Built once per session: find a user by role, then log in."""
from dataclasses import dataclass, field

import pytest

from services import auth, users


@dataclass(frozen=True)
class AuthContext:
    """An identity: who it is + a client already carrying its token."""
    role: str
    user_id: int
    username: str
    api_client: object = field(repr=False)
    access_token: str = field(default="", repr=False)
    refresh_token: str = field(default="", repr=False)


def _login_context(user, make_client, role) -> AuthContext:
    body, status = auth.login(make_client(), user["username"], user["password"])
    if status != 200 or "accessToken" not in body:
        pytest.fail(f"login failed for role={role!r} (user {user.get('id')}): status={status}")
    return AuthContext(
        role=role, user_id=user["id"], username=user["username"],
        api_client=make_client(token=body["accessToken"]),
        access_token=body["accessToken"], refresh_token=body.get("refreshToken", ""),
    )


def _discover(make_client, role, want=1):
    """Find `want` users for a role. Fail (not skip) if short — usually means the API is down."""
    found = users.find_users_by_role(make_client(), role, limit=want)
    if len(found) < want:
        pytest.fail(f"could not discover {want} user(s) with role={role!r} "
                    f"(got {len(found)}) — is the API reachable?")
    return found


@pytest.fixture(scope="session")
def anonymous(make_client):
    """A visitor with no token."""
    return AuthContext(role="anon", user_id=0, username="", api_client=make_client())


@pytest.fixture(scope="session")
def normal_user(make_client):
    """A normal user (user A)."""
    return _login_context(_discover(make_client, "user")[0], make_client, "user")


@pytest.fixture(scope="session")
def another_user(make_client, normal_user):
    """A different normal user (user B), guaranteed distinct from user A."""
    other = next((u for u in _discover(make_client, "user", want=5)
                  if u["id"] != normal_user.user_id), None)
    if other is None:
        pytest.fail("could not find a second distinct 'user' account for cross-user tests")
    return _login_context(other, make_client, "user")


@pytest.fixture(scope="session")
def admin_user(make_client):
    """An admin — the high-privilege end of the RBAC ladder."""
    return _login_context(_discover(make_client, "admin")[0], make_client, "admin")
