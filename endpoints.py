"""All DummyJSON API paths in one place. Services import from here; no HTTP happens
in this file. `/auth/...` paths require a token."""


class AuthAPI:
    @staticmethod
    def login():
        return "/auth/login"

    @staticmethod
    def me():
        return "/auth/me"

    @staticmethod
    def refresh():
        return "/auth/refresh"


class UsersAPI:
    @staticmethod
    def list():
        return "/users"

    @staticmethod
    def filter():
        return "/users/filter"

    @staticmethod
    def search():
        return "/users/search"

    @staticmethod
    def get(user_id):
        return f"/users/{user_id}"

    @staticmethod
    def get_protected(user_id):
        return f"/auth/users/{user_id}"
