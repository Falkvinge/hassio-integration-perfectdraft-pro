#!/usr/bin/env python3
"""Local test harness for the PerfectDraft API integration.

Exercises the token-refresh + data flow without Home Assistant:
  1. Refresh tokens via /auth/renewaccesstokens
  2. Fetch user profile (/api/me)
  3. Fetch machine details

Reads credentials from .credentials.json (gitignored).

Usage:
    python3 test_harness.py
    python3 test_harness.py --step refresh     # stop after token refresh
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

_pkg = Path(__file__).parent / "custom_components" / "perfectdraft"
sys.path.insert(0, str(Path(__file__).parent / "custom_components"))

import importlib.util


def _load_module(name: str, filepath: Path):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


const = _load_module("perfectdraft.const", _pkg / "const.py")
exceptions = _load_module("perfectdraft.exceptions", _pkg / "exceptions.py")
api = _load_module("perfectdraft.api", _pkg / "api.py")

API_BASE_URL = const.API_BASE_URL
API_KEY = const.API_KEY
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
        log.error("Missing %s — create it with user_id and refresh_token", CRED_FILE)
        sys.exit(1)
    creds = json.loads(CRED_FILE.read_text())
    if not creds.get("user_id") or not creds.get("refresh_token"):
        log.error(
            "Fill in user_id and refresh_token in %s\n"
            "Format: {\"user_id\": \"...\", \"refresh_token\": \"...\", \"email\": \"...\"}",
            CRED_FILE,
        )
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
    user_id = creds["user_id"]
    refresh_token = creds["refresh_token"]

    print(f"\n--- PerfectDraft API Test Harness ---")
    print(f"  User ID:  {user_id[:20]}..." if len(user_id) > 20 else f"  User ID:  {user_id}")
    print(f"  API base: {API_BASE_URL}")
    print()

    async with aiohttp.ClientSession() as session:
        client = PerfectDraftApiClient(session)

        # --- Step 1: Refresh tokens ---
        print("[1/4] Refreshing tokens via /auth/renewaccesstokens...")
        try:
            refresh_data = await client.refresh_access_token(
                user_id=user_id,
                refresh_token=refresh_token,
            )
            print(f"  OK — got fresh tokens")
            print(f"  AccessToken:  {client.access_token[:30]}..." if client.access_token else "  AccessToken: None")
            print(f"  RefreshToken: {client.refresh_token[:30]}..." if client.refresh_token else "  RefreshToken: None")
            dump_json("Refresh response", refresh_data, dump=dump)
        except (AuthenticationError, PerfectDraftApiError, PerfectDraftConnectionError) as exc:
            print(f"  FAILED — {type(exc).__name__}: {exc}")
            return

        if step == "refresh":
            print("\n--- Stopping after refresh step ---")
            return

        # --- Step 2: User profile ---
        print(f"\n[2/4] Fetching user profile (/api/me)...")
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

        # --- Step 3: Machine details ---
        machine_id = _extract_machine_id(profile)
        if not machine_id:
            print(f"\n[3/4] Cannot fetch machine details — no machine_id found")
            print(f"  Profile keys: {list(profile.keys())}")
            dump_json("Full profile", profile, dump=True)
            return

        print(f"\n[3/4] Fetching machine details for {machine_id}...")
        try:
            details = await client.get_machine_details(machine_id)
            print(f"  OK — response received")
            dump_json("Machine details", details, dump=True)
        except (PerfectDraftApiError, PerfectDraftConnectionError) as exc:
            print(f"  FAILED — {type(exc).__name__}: {exc}")
            return

        # --- Step 4: Try keg endpoint ---
        print(f"\n[4/4] Fetching machine kegs...")
        try:
            kegs = await client._request("GET", "/api/perfectdraft_machine_kegs")
            print(f"  OK — response received")
            dump_json("Machine kegs", kegs, dump=True)
        except (PerfectDraftApiError, PerfectDraftConnectionError, AuthenticationError) as exc:
            print(f"  FAILED — {type(exc).__name__}: {exc}")

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
                for id_key in ("id", "machine_id", "machineId", "deviceId", "serial", "@id"):
                    if id_key in item:
                        return str(item[id_key])
            return str(item)

    for key, val in profile.items():
        if any(hint in key.lower() for hint in ("machine", "device")):
            log.info("Potential machine field: %s = %s", key, val)

    return None


def main():
    parser = argparse.ArgumentParser(description="PerfectDraft API test harness")
    parser.add_argument(
        "--step",
        choices=["refresh", "profile", "all"],
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
