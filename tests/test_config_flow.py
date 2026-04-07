"""Tests for the GitHub Chatter config flow module."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import TYPE_CHECKING
from typing import Any
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


def _install_homeassistant_stubs(monkeypatch: MonkeyPatch) -> None:
    config_entries: Any = ModuleType("homeassistant.config_entries")
    core: Any = ModuleType("homeassistant.core")
    helpers = ModuleType("homeassistant.helpers")
    aiohttp_client: Any = ModuleType("homeassistant.helpers.aiohttp_client")

    class ConfigFlow:
        domain: str | None

        def __init_subclass__(cls, *, domain: str | None = None, **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            cls.domain = domain

    class OptionsFlowWithReload:
        def __init__(self) -> None:
            self.config_entry: Any = None

    def callback(func: Any) -> Any:
        return func

    config_entries.ConfigFlow = ConfigFlow
    config_entries.ConfigFlowResult = dict[str, Any]
    config_entries.OptionsFlowWithReload = OptionsFlowWithReload
    core.callback = callback
    aiohttp_client.async_get_clientsession = MagicMock()

    monkeypatch.setitem(sys.modules, "homeassistant", ModuleType("homeassistant"))
    monkeypatch.setitem(sys.modules, "homeassistant.config_entries", config_entries)
    monkeypatch.setitem(sys.modules, "homeassistant.core", core)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers)
    monkeypatch.setitem(
        sys.modules, "homeassistant.helpers.aiohttp_client", aiohttp_client
    )


def test_async_get_options_flow_returns_no_arg_options_flow(
    monkeypatch: MonkeyPatch,
) -> None:
    _install_homeassistant_stubs(monkeypatch)
    sys.modules.pop("custom_components.github_chatter.config_flow", None)

    config_flow = importlib.import_module(
        "custom_components.github_chatter.config_flow"
    )

    flow = config_flow.GitHubChatterConfigFlow.async_get_options_flow(MagicMock())

    assert isinstance(flow, config_flow.GitHubChatterOptionsFlow)
