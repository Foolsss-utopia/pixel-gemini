"""Smoke test that every documented Pixel device profile loads cleanly.

For each preset key registered in ``config.DEVICE_PRESETS`` we re-import the
relevant modules with ``DEVICE_PROFILE`` pointing at that preset and verify:

* ``config.DEVICE_MODEL`` / ``config.ANDROID_VERSION`` / ``config.BUILD_ID``
  are populated and consistent with the preset.
* ``services.device_simulator.DEVICE_SPECS`` matches the profile's spec dict
  (``DEVICE_SPECS_BY_PROFILE[<profile>]``).
* ``random_build_id()`` returns a build ID from the profile's pool.
* ``create_device_profile()`` produces a ``DeviceProfile`` whose user-agent
  contains the expected Android version and device model, and whose Client
  Hints headers expose the right ``Sec-CH-UA-Platform-Version`` /
  ``Sec-CH-UA-Model`` values.

Also verifies the unknown-profile fallback: setting ``DEVICE_PROFILE`` to a
junk value must fall back to ``DEFAULT_DEVICE_PROFILE`` (no crash).

The script exits with a non-zero status on the first failure so it can be
used as a CI gate.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def _reload_modules() -> tuple:
    """Drop and re-import config + device_simulator so they pick up the env."""
    for name in ("services.device_simulator", "config"):
        sys.modules.pop(name, None)
    config = importlib.import_module("config")
    device_simulator = importlib.import_module("services.device_simulator")
    return config, device_simulator


def _check_profile(profile_name: str) -> None:
    os.environ["DEVICE_PROFILE"] = profile_name
    config, device_simulator = _reload_modules()

    preset = config.DEVICE_PRESETS[profile_name]

    assert config.DEVICE_PROFILE_NAME == profile_name, (
        f"DEVICE_PROFILE_NAME mismatch: expected {profile_name!r}, "
        f"got {config.DEVICE_PROFILE_NAME!r}"
    )
    assert config.DEVICE_MODEL == preset["model"], (
        f"DEVICE_MODEL mismatch for {profile_name}: "
        f"expected {preset['model']!r}, got {config.DEVICE_MODEL!r}"
    )
    assert config.ANDROID_VERSION == preset["android_version"], (
        f"ANDROID_VERSION mismatch for {profile_name}: "
        f"expected {preset['android_version']!r}, got {config.ANDROID_VERSION!r}"
    )
    assert config.ANDROID_SDK == preset["android_sdk"], (
        f"ANDROID_SDK mismatch for {profile_name}: "
        f"expected {preset['android_sdk']!r}, got {config.ANDROID_SDK!r}"
    )

    expected_specs = device_simulator.DEVICE_SPECS_BY_PROFILE[profile_name]
    assert device_simulator.DEVICE_SPECS is expected_specs, (
        f"DEVICE_SPECS not bound to {profile_name} specs"
    )

    build_pool = device_simulator.DEVICE_BUILDS_BY_PROFILE[profile_name]
    sampled_build = device_simulator.random_build_id()
    assert sampled_build in build_pool, (
        f"random_build_id() returned {sampled_build!r} which is not in "
        f"the {profile_name} build pool"
    )

    profile = device_simulator.create_device_profile()
    ua = profile.user_agent
    assert f"Android {preset['android_version']}" in ua, (
        f"User-agent for {profile_name} missing 'Android "
        f"{preset['android_version']}': {ua}"
    )
    assert preset["model"] in ua, (
        f"User-agent for {profile_name} missing model {preset['model']!r}: {ua}"
    )

    headers = profile.client_hints_headers()
    expected_platform_version = f'"{preset["android_version"]}.0.0"'
    assert headers.get("Sec-CH-UA-Platform-Version") == expected_platform_version, (
        f"Sec-CH-UA-Platform-Version for {profile_name} expected "
        f"{expected_platform_version!r}, got "
        f"{headers.get('Sec-CH-UA-Platform-Version')!r}"
    )
    expected_model = f'"{preset["model"]}"'
    assert headers.get("Sec-CH-UA-Model") == expected_model, (
        f"Sec-CH-UA-Model for {profile_name} expected {expected_model!r}, "
        f"got {headers.get('Sec-CH-UA-Model')!r}"
    )

    print(
        f"[OK] {profile_name}: model={config.DEVICE_MODEL} "
        f"android={config.ANDROID_VERSION} build={sampled_build} "
        f"ua_chrome={profile.chrome_version}"
    )


def _check_unknown_profile_fallback() -> None:
    os.environ["DEVICE_PROFILE"] = "this_profile_does_not_exist"
    config, _ = _reload_modules()
    assert config.DEVICE_PROFILE_NAME == config.DEFAULT_DEVICE_PROFILE, (
        f"Unknown DEVICE_PROFILE did not fall back to "
        f"{config.DEFAULT_DEVICE_PROFILE!r} (got {config.DEVICE_PROFILE_NAME!r})"
    )
    print(
        f"[OK] unknown profile fell back to default "
        f"({config.DEFAULT_DEVICE_PROFILE})"
    )


def main() -> int:
    # Load presets via a clean import.
    os.environ.pop("DEVICE_PROFILE", None)
    config, _ = _reload_modules()
    profile_names = sorted(config.DEVICE_PRESETS.keys())
    if not profile_names:
        print("ERROR: DEVICE_PRESETS registry is empty", file=sys.stderr)
        return 1

    print(f"Checking {len(profile_names)} device profile(s): {profile_names}")
    for name in profile_names:
        _check_profile(name)
    _check_unknown_profile_fallback()
    print(f"All {len(profile_names)} device profiles loaded cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
