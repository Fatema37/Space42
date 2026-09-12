"""Users service. `protected=True` uses the `/auth/...` path. Functions return (body, status)."""
from endpoints import UsersAPI


def _path(user_id, protected):
    return UsersAPI.get_protected(user_id) if protected else UsersAPI.get(user_id)


def list_users(api_client, **params):
    return api_client.get(UsersAPI.list(), params=params or None)


def get_user(api_client, user_id, protected=False):
    return api_client.get(_path(user_id, protected))


def filter_by(api_client, key, value, **params):
    return api_client.get(UsersAPI.filter(), params={"key": key, "value": value, **params})


def search(api_client, q, **params):
    return api_client.get(UsersAPI.search(), params={"q": q, **params})


def find_users_by_role(api_client, role, limit=1):
    """Discover real users per role at runtime (the sandbox exposes passwords)."""
    body, status = filter_by(api_client, "role", role, limit=limit)
    return body.get("users", []) if status == 200 else []


def update_user(api_client, user_id, data, protected=True):
    return api_client.put(_path(user_id, protected), json=data)


def delete_user(api_client, user_id, protected=True):
    return api_client.delete(_path(user_id, protected))
