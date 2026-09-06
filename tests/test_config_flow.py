"""Config flow tests, focused on the reauth path.

The bug these guard against: ``async_step_token`` is shared by the user and
reauth sources, and used to call ``_abort_if_unique_id_configured()``
unconditionally. During reauth the unique ID belongs to the entry being
repaired, so the duplicate guard aborted the flow with ``already_configured``
and the freshly issued tokens were discarded.
"""
import unittest
from unittest.mock import AsyncMock, patch

try:
    import pytest
    from homeassistant.config_entries import SOURCE_USER
    from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResultType
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.perfectdraft.const import (
        CONF_ACCESS_TOKEN,
        CONF_ID_TOKEN,
        CONF_MACHINE_ID,
        CONF_REFRESH_TOKEN,
        DOMAIN,
    )
    from custom_components.perfectdraft.exceptions import (
        AuthenticationError,
        PerfectDraftConnectionError,
    )
except ImportError as err:
    # Keeps `python3 -m unittest discover -s tests` working for anyone who
    # only wants the stdlib-only keg-detection tests: unittest turns a
    # SkipTest raised during import into a skip rather than an error.
    raise unittest.SkipTest(
        "Home Assistant test harness missing "
        "(pip install -r requirements-test.txt)"
    ) from err

EMAIL = "drinker@example.com"
PASSWORD = "hunter2"
TOKEN = "recaptcha-token"
MACHINE_ID = "machine-1"

CLIENT_PATH = "custom_components.perfectdraft.config_flow.PerfectDraftApiClient"
SETUP_PATH = "custom_components.perfectdraft.async_setup_entry"

STORED_DATA = {
    CONF_EMAIL: EMAIL,
    CONF_ACCESS_TOKEN: "old-access",
    CONF_ID_TOKEN: "old-id",
    CONF_REFRESH_TOKEN: "old-refresh",
    CONF_MACHINE_ID: MACHINE_ID,
}


def _mock_client(*, authenticate_error=None, machines=((MACHINE_ID,))):
    """An API client that hands back recognisably new tokens."""
    client = AsyncMock()
    client.access_token = "new-access"
    client.id_token = "new-id"
    client.refresh_token = "new-refresh"
    if authenticate_error is not None:
        client.authenticate.side_effect = authenticate_error
    client.get_user_profile.return_value = {
        "perfectdraftMachines": [{"id": m} for m in machines]
    }
    return client


def _entry(hass: HomeAssistant, data=None, unique_id=EMAIL) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=unique_id,
        data=dict(STORED_DATA if data is None else data),
        title=f"PerfectDraft ({EMAIL})",
    )
    entry.add_to_hass(hass)
    return entry


async def _run_reauth(hass, entry, client, *, email=EMAIL, token=TOKEN):
    """Drive reauth_confirm then token, returning the final flow result."""
    with (
        patch(CLIENT_PATH, return_value=client),
        patch(SETUP_PATH, return_value=True),
    ):
        result = await entry.start_reauth_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: email, CONF_PASSWORD: PASSWORD}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "token"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"recaptcha_token": token}
        )
        await hass.async_block_till_done()
    return result


# --- Reauth: the regression this change fixes ---


async def test_reauth_persists_new_tokens(hass: HomeAssistant) -> None:
    entry = _entry(hass)
    result = await _run_reauth(hass, entry, _mock_client())

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_ACCESS_TOKEN] == "new-access"
    assert entry.data[CONF_ID_TOKEN] == "new-id"
    assert entry.data[CONF_REFRESH_TOKEN] == "new-refresh"


async def test_reauth_preserves_email_and_machine_id(hass: HomeAssistant) -> None:
    entry = _entry(hass)
    await _run_reauth(hass, entry, _mock_client())

    assert entry.data[CONF_EMAIL] == EMAIL
    assert entry.data[CONF_MACHINE_ID] == MACHINE_ID
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_reauth_never_aborts_as_already_configured(hass: HomeAssistant) -> None:
    """The exact failure reported: auth succeeds, then the flow dies here."""
    entry = _entry(hass)
    result = await _run_reauth(hass, entry, _mock_client())

    assert result["reason"] != "already_configured"
    assert result["reason"] == "reauth_successful"


async def test_reauth_reloads_the_entry(hass: HomeAssistant) -> None:
    entry = _entry(hass)
    client = _mock_client()

    with (
        patch(CLIENT_PATH, return_value=client),
        patch(SETUP_PATH, return_value=True) as mock_setup,
    ):
        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"recaptcha_token": TOKEN}
        )
        await hass.async_block_till_done()

    assert mock_setup.call_count == 1


async def test_reauth_rejects_a_different_account(hass: HomeAssistant) -> None:
    entry = _entry(hass)
    result = await _run_reauth(
        hass, entry, _mock_client(), email="someone.else@example.com"
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_account_mismatch"
    assert entry.data[CONF_ACCESS_TOKEN] == "old-access"
    assert entry.data[CONF_REFRESH_TOKEN] == "old-refresh"


async def test_reauth_accepts_same_account_different_case(
    hass: HomeAssistant,
) -> None:
    entry = _entry(hass)
    result = await _run_reauth(hass, entry, _mock_client(), email="Drinker@Example.COM")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_ACCESS_TOKEN] == "new-access"


async def test_reauth_bad_token_keeps_old_tokens(hass: HomeAssistant) -> None:
    entry = _entry(hass)
    client = _mock_client(authenticate_error=AuthenticationError("token expired"))
    result = await _run_reauth(hass, entry, client)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "token"
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data[CONF_ACCESS_TOKEN] == "old-access"
    assert entry.data[CONF_REFRESH_TOKEN] == "old-refresh"


async def test_reauth_skips_profile_when_machine_id_known(
    hass: HomeAssistant,
) -> None:
    entry = _entry(hass)
    client = _mock_client()
    await _run_reauth(hass, entry, client)

    client.get_user_profile.assert_not_called()
    assert entry.data[CONF_MACHINE_ID] == MACHINE_ID


async def test_reauth_recovers_missing_machine_id(hass: HomeAssistant) -> None:
    data = {k: v for k, v in STORED_DATA.items() if k != CONF_MACHINE_ID}
    entry = _entry(hass, data=data)
    client = _mock_client()
    await _run_reauth(hass, entry, client)

    client.get_user_profile.assert_called_once()
    assert entry.data[CONF_MACHINE_ID] == MACHINE_ID


# --- User setup: must be unchanged by this fix ---


async def test_user_setup_creates_entry(hass: HomeAssistant) -> None:
    client = _mock_client()

    with (
        patch(CLIENT_PATH, return_value=client),
        patch(SETUP_PATH, return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
        )
        assert result["step_id"] == "token"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"recaptcha_token": TOKEN}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ACCESS_TOKEN] == "new-access"
    assert result["data"][CONF_MACHINE_ID] == MACHINE_ID
    assert result["result"].unique_id == EMAIL


async def test_user_setup_still_blocks_duplicates(hass: HomeAssistant) -> None:
    _entry(hass)
    client = _mock_client()

    with (
        patch(CLIENT_PATH, return_value=client),
        patch(SETUP_PATH, return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"recaptcha_token": TOKEN}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_setup_connection_error(hass: HomeAssistant) -> None:
    client = _mock_client(
        authenticate_error=PerfectDraftConnectionError("no route to host")
    )

    with patch(CLIENT_PATH, return_value=client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"recaptcha_token": TOKEN}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


# --- Translations must cover every reachable abort reason ---


@pytest.mark.parametrize(
    "reason",
    ["already_configured", "reauth_successful", "reauth_account_mismatch"],
)
def test_abort_reasons_are_translated(reason: str) -> None:
    import json
    from pathlib import Path

    root = Path(__file__).parent.parent / "custom_components" / "perfectdraft"
    for name in ("strings.json", "translations/en.json"):
        data = json.loads((root / name).read_text(encoding="utf-8"))
        assert reason in data["config"]["abort"], f"{reason} missing from {name}"
