#!/usr/bin/env python3
"""Local test harness for the PerfectDraft API integration.

Exercises the full auth + data flow without Home Assistant:
  1. Server-side reCAPTCHA token generation
  2. Authentication (sign-in)
  3. Token refresh
  4. Fetch user profile (/api/me)
  5. Fetch machine details

Reads credentials from .credentials.json (gitignored).

Usage:
    python3 test_harness.py
    python3 test_harness.py --step auth       # stop after auth
    python3 test_harness.py --step recaptcha   # only test recaptcha token gen
    python3 test_harness.py --step profile     # stop after profile fetch
    python3 test_harness.py --dump             # dump full API responses as JSON
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import aiohttp

# Import only the standalone modules (no HA dependency)
_pkg = Path(__file__).parent / "custom_components" / "perfectdraft"
sys.path.insert(0, str(Path(__file__).parent / "custom_components"))

# Block homeassistant imports so __init__.py doesn't blow up if accidentally loaded
sys.modules["homeassistant"] = type(sys)("homeassistant")

import importlib.util

def _load_module(name: str, filepath: Path):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

const = _load_module("perfectdraft.const", _pkg / "const.py")
exceptions = _load_module("perfectdraft.exceptions", _pkg / "exceptions.py")

# api.py imports from .const and .exceptions — those are now in sys.modules
api = _load_module("perfectdraft.api", _pkg / "api.py")
recaptcha = _load_module("perfectdraft.recaptcha", _pkg / "recaptcha.py")

API_BASE_URL = const.API_BASE_URL
API_KEY = const.API_KEY
RECAPTCHA_SITE_KEY = const.RECAPTCHA_SITE_KEY
async_generate_recaptcha_token = recaptcha.async_generate_recaptcha_token
PerfectDraftApiClient = api.PerfectDraftApiClient
AuthenticationError = exceptions.AuthenticationError
PerfectDraftApiError = exceptions.PerfectDraftApiError
PerfectDraftConnectionError = exceptions.PerfectDraftConnectionError

CRED_FILE = Path(__file__).parent / ".credentials.json"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
log = logging.getLogger("test_harness")


def load_credentials() -> dict:
    if not CRED_FILE.exists():
        log.error("Missing %s — copy from template and fill in your creds", CRED_FILE)
        sys.exit(1)
    creds = json.loads(CRED_FILE.read_text())
    if creds.get("email", "").startswith("YOUR_"):
        log.error("Fill in your real credentials in %s", CRED_FILE)
        sys.exit(1)
    return creds


def dump_json(label: str, data, *, dump: bool):
    if dump:
        print(f"\n{'=' * 60}")
        print(f"  {label}")
        print(f"{'=' * 60}")
        print(json.dumps(data, indent=2, default=str))
        print()
    else:
        if isinstance(data, dict):
            print(f"  {label}: keys={list(data.keys())}")
        else:
            print(f"  {label}: {data}")


async def run(step: str, dump: bool):
    creds = load_credentials()
    email = creds["email"]
    password = creds["password"]

    print(f"\n--- PerfectDraft API Test Harness ---")
    print(f"  Email:    {email}")
    print(f"  API base: {API_BASE_URL}")
    print(f"  API key:  {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"  Site key: {RECAPTCHA_SITE_KEY[:8]}...{RECAPTCHA_SITE_KEY[-4:]}")
    print()

    async with aiohttp.ClientSession() as session:
        client = PerfectDraftApiClient(session)

        # --- Step 1: reCAPTCHA ---
        print("[1/5] Generating reCAPTCHA token (server-side)...")
        token = await async_generate_recaptcha_token(session)
        if token:
            print(f"  OK — token length: {len(token)}")
            print(f"  Token prefix: {token[:40]}...")
        else:
            print("  FAILED — no token generated")
            print("  This means the anchor/reload approach didn't work.")
            print("  The API call will likely fail without a valid token.")
            token = "DUMMY_TOKEN_FOR_TESTING"
            print(f"  Using dummy token to see what the API says...")

        if step == "recaptcha":
            print("\n--- Stopping after recaptcha step ---")
            return

        # --- Step 2: Authenticate ---
        print(f"\n[2/5] Authenticating as {email}...")
        try:
            auth_data = await client.authenticate(email, password, token)
            print(f"  OK — got tokens")
            print(f"  AccessToken:  {client.access_token[:20]}..." if client.access_token else "  AccessToken: None")
            print(f"  RefreshToken: {client.refresh_token[:20]}..." if client.refresh_token else "  RefreshToken: None")
            dump_json("Auth response", auth_data, dump=dump)
        except (AuthenticationError, PerfectDraftApiError, PerfectDraftConnectionError) as exc:
            print(f"  FAILED — {type(exc).__name__}: {exc}")
            print("\n  If this is an auth error, possible causes:")
            print("    - reCAPTCHA token was rejected (invalid/expired/wrong type)")
            print("    - Wrong email/password")
            print("    - IP rate-limited by Imperva WAF")
            return

        if step == "auth":
            print("\n--- Stopping after auth step ---")
            return

        # --- Step 3: Refresh token ---
        print(f"\n[3/5] Testing token refresh...")
        try:
            refresh_data = await client.refresh_access_token()
            print(f"  OK — access token refreshed")
            dump_json("Refresh response", refresh_data, dump=dump)
        except (AuthenticationError, PerfectDraftApiError, PerfectDraftConnectionError) as exc:
            print(f"  FAILED — {type(exc).__name__}: {exc}")
            print("  (Continuing with original access token...)")

        # --- Step 4: User profile ---
        print(f"\n[4/5] Fetching user profile (/api/me)...")
        try:
            profile = await client.get_user_profile()
            print(f"  OK — response received")
            dump_json("Profile", profile, dump=dump)
        except (PerfectDraftApiError, PerfectDraftConnectionError) as exc:
            print(f"  FAILED — {type(exc).__name__}: {exc}")
            return

        if step == "profile":
            print("\n--- Stopping after profile step ---")
            return

        # --- Step 5: Machine details ---
        machine_id = _extract_machine_id(profile)
        if not machine_id:
            print(f"\n[5/5] Cannot fetch machine details — no machine_id found")
            print(f"  Profile keys: {list(profile.keys())}")
            print(f"  Full profile dump needed to find the machine ID field")
            dump_json("Full profile", profile, dump=True)
            return

        print(f"\n[5/5] Fetching machine details for {machine_id}...")
        try:
            details = await client.get_machine_details(machine_id)
            print(f"  OK — response received")
            dump_json("Machine details", details, dump=True)
        except (PerfectDraftApiError, PerfectDraftConnectionError) as exc:
            print(f"  FAILED — {type(exc).__name__}: {exc}")
            return

    print(f"\n--- All steps complete ---")


def _extract_machine_id(profile: dict) -> str | None:
    """Try every plausible field name for the machine ID."""
    if "machine_id" in profile:
        return profile["machine_id"]

    for key in ("machines", "perfectdraft_machines", "machineIds",
                "machine_ids", "devices", "machineList"):
        machines = profile.get(key)
        if isinstance(machines, list) and machines:
            item = machines[0]
            if isinstance(item, dict):
                for id_key in ("id", "machine_id", "machineId", "deviceId", "serial"):
                    if id_key in item:
                        return str(item[id_key])
            return str(item)

    # Brute-force: look for any key containing "machine" or "device"
    for key, val in profile.items():
        if any(hint in key.lower() for hint in ("machine", "device")):
            log.info("Potential machine field: %s = %s", key, val)

    return None


def main():
    parser = argparse.ArgumentParser(description="PerfectDraft API test harness")
    parser.add_argument(
        "--step",
        choices=["recaptcha", "auth", "profile", "all"],
        default="all",
        help="Stop after this step (default: all)",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump full JSON responses",
    )
    args = parser.parse_args()
    asyncio.run(run(args.step, args.dump))


if __name__ == "__main__":
    main()
