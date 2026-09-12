"""Users contract checks. Functional REST features (paging, sort, search) are left out —
this is a security assessment. Writes are simulated (echoed, not saved)."""
import pytest

from models import User
from services import users

pytestmark = [pytest.mark.users, pytest.mark.contract]


class TestGetUser:

    def test_default_list_has_users_and_paging_fields(self, anonymous):
        body, status = users.list_users(anonymous.api_client)
        assert status == 200
        assert body["users"] and {"total", "skip", "limit"} <= set(body)

    def test_existing_user_matches_schema(self, anonymous, normal_user):
        body, status = users.get_user(anonymous.api_client, normal_user.user_id)
        assert status == 200
        assert User(**body).id == normal_user.user_id                 # check the shape

    @pytest.mark.negative
    def test_unknown_id_returns_404(self, anonymous):
        body, status = users.get_user(anonymous.api_client, 9999)
        assert status == 404 and "message" in body

    @pytest.mark.negative
    def test_invalid_id_returns_400(self, anonymous):
        body, status = users.get_user(anonymous.api_client, "abc")
        assert status == 400 and "message" in body

    def test_filter_by_role_returns_only_that_role(self, anonymous):
        # discovery uses this call to pick a user per role
        body, status = users.filter_by(anonymous.api_client, "role", "admin", select="role")
        assert status == 200 and body["users"]
        assert all(u["role"] == "admin" for u in body["users"])


class TestUpdateUser:

    def test_update_echoes_the_change(self, normal_user):
        body, status = users.update_user(normal_user.api_client, normal_user.user_id, {"lastName": "Changed"})
        assert status == 200
        assert body["id"] == normal_user.user_id and body["lastName"] == "Changed"

    def test_update_is_simulated_not_persisted(self, anonymous, normal_user):
        users.update_user(normal_user.api_client, normal_user.user_id, {"lastName": "Changed"})
        body, status = users.get_user(anonymous.api_client, normal_user.user_id)
        assert status == 200 and body["lastName"] != "Changed"


class TestDeleteUser:

    def test_delete_returns_deleted_marker(self, normal_user):
        body, status = users.delete_user(normal_user.api_client, normal_user.user_id)
        assert status == 200
        assert body["id"] == normal_user.user_id and body["isDeleted"] is True and body.get("deletedOn")

    def test_delete_is_simulated_not_persisted(self, anonymous, normal_user):
        users.delete_user(normal_user.api_client, normal_user.user_id)
        body, status = users.get_user(anonymous.api_client, normal_user.user_id)
        assert status == 200 and body["id"] == normal_user.user_id
