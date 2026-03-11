"""Shared test fixtures for Homey AI Hub tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_homey():
    """Mock Homey SDK instance for testing providers without Homey runtime."""
    homey = MagicMock()
    homey.settings = MagicMock()
    homey.settings.get = MagicMock(return_value=None)
    homey.settings.set = AsyncMock()
    homey.settings.unset = AsyncMock()
    homey.flow = MagicMock()
    homey.flow.get_action_card = MagicMock()
    return homey


@pytest.fixture
def mock_action_card():
    """Mock Homey FlowCardAction."""
    card = MagicMock()
    card.register_run_listener = MagicMock()
    card.register_argument_autocomplete_listener = MagicMock()
    return card
