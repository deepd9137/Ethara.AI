"""
Test configuration.
- Single session-scoped event loop so asyncpg doesn't get "wrong loop" errors.
- Rate limiter disabled so the 10/5min cap doesn't trigger during the full suite.
"""

from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(scope="session")
def event_loop_policy() -> object:
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(autouse=True)
def disable_rate_limiting() -> Generator[None, None, None]:
    with patch("app.core.limiter.limiter.enabled", False):
        yield
