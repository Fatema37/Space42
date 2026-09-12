"""Shared plumbing fixtures. Identities live in auth_fixtures.py, reporting in utils/reporting.py."""
import pytest

from config import get_settings
from utils.api_client import APIClient

pytest_plugins = ["auth_fixtures", "utils.reporting"]


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def make_client(settings):
    """Factory: an APIClient for a token (None = anonymous). keep_cookies=True only for cookie tests."""
    def _make(token=None, keep_cookies=False):
        return APIClient(settings.base_url, token=token, keep_cookies=keep_cookies,
                         timeout=settings.request_timeout, max_retries=settings.max_retries)
    return _make
