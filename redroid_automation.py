"""
Redroid (Remote Android Container) automation using uiautomator2 & ADB.

Connects to Redroid instance (simulating Pixel 10 Pro), handles Google Account login,
launches Google One / Gemini Android app, and extracts the 12-month free Gemini Pro offer link.
"""

import logging
import time
import re
from typing import Optional

import uiautomator2 as u2
import pyotp

import config
from device_simulator import DeviceProfile

logger = logging.getLogger(__name__)


class RedroidAutomationError(Exception):
    """Raised when Redroid Android automation encounters an error."""


class RedroidAutomation:
    def __init__(self, host: str = config.REDROID_HOST, port: int = config.REDROID_PORT):
        self.host = host
        self.port = port
        self.device_addr = f"{host}:{port}"
        self.d: Optional[u2.Device] = None

    def connect(self) -> u2.Device:
        """Connect to Redroid ADB device or local Android Emulator via uiautomator2."""
        try:
            logger.info("Connecting to Android device/emulator-5554...")
            try:
                self.d = u2.connect("emulator-5554")
            except Exception:
                self.d = u2.connect(self.device_addr)
            logger.info("Connected to Android device: %s", self.d.info)
            return self.d
        except Exception as exc:
            logger.error("Failed to connect to Android device/emulator: %s", exc)
            raise RedroidAutomationError(
                "Could not connect to Android Pixel Container/Emulator. "
                "Ensure Android Emulator or ADB device is running."
            ) from exc

    def login_google_account(self, email: str, password: str, totp_secret: str = "") -> bool:
        """Add Google account to Android OS settings."""
        if not self.d:
            self.connect()

        try:
            logger.info("Initiating Google account login for %s on Redroid...", email)
            # Open Android Settings Add Account Intent
            self.d.shell("am start -a android.settings.ADD_ACCOUNT_SETTINGS")
            time.sleep(3)

            # Click Google account option if list appears
            if self.d(text="Google").exists(timeout=5):
                self.d(text="Google").click()
                time.sleep(3)

            # Enter Email
            if self.d(resourceId="identifierId").exists(timeout=15):
                self.d(resourceId="identifierId").set_text(email)
                if self.d(text="Next").exists():
                    self.d(text="Next").click()
                elif self.d(resourceId="identifierNext").exists():
                    self.d(resourceId="identifierNext").click()
                time.sleep(4)

            # Enter Password
            if self.d(className="android.widget.EditText").exists(timeout=15):
                self.d(className="android.widget.EditText").set_text(password)
                if self.d(text="Next").exists():
                    self.d(text="Next").click()
                time.sleep(4)

            # Handle 2FA TOTP if prompted
            if totp_secret and self.d(className="android.widget.EditText").exists(timeout=5):
                totp_code = pyotp.TOTP(totp_secret.replace(" ", "")).now()
                self.d(className="android.widget.EditText").set_text(totp_code)
                if self.d(text="Next").exists():
                    self.d(text="Next").click()
                time.sleep(4)

            # Accept Terms
            if self.d(text="I agree").exists(timeout=10):
                self.d(text="I agree").click()
                time.sleep(5)

            logger.info("Google Account login flow completed on Redroid for %s", email)
            return True

        except Exception as exc:
            logger.error("Error during Redroid Google account login: %s", exc)
            return False

    def claim_gemini_offer(self, email: str, password: str, device: DeviceProfile, totp_secret: str = "") -> Optional[str]:
        """
        Main entry point for Redroid offer claim.

        Launches Google One / Gemini Android app on Redroid, navigates to offers,
        clicks "Claim Offer" / "Try Gemini Advanced", and captures the redemption link.
        """
        if not self.d:
            self.connect()

        try:
            # Step 1: Ensure Google Account is added
            self.login_google_account(email, password, totp_secret)

            # Step 2: Trigger Play Store / Google One Subscriptions Voucher Intent
            logger.info("Triggering Google Play Store Subscriptions RPC Intent for Pixel 10 Pro...")
            intents = [
                "am start -a android.intent.action.VIEW -d https://one.google.com/offer/partner-eft-onboard",
                "am start -a android.intent.action.VIEW -d https://one.google.com/offers",
                "am start -a android.intent.action.VIEW -d market://details?id=com.google.android.apps.subscriptions.red",
                "am start -a android.intent.action.VIEW -d https://one.google.com/benefit/detail/gemini"
            ]
            for cmd in intents:
                self.d.shell(cmd)
                time.sleep(4)

            # Step 3: Look for "Claim Offer" / "Try Gemini Advanced" / "Share" / "Get Offer" UI elements
            claim_btn = None
            for label in ["Try Gemini Advanced", "Claim offer", "Get offer", "Redeem", "Explore benefits", "View details", "Start trial"]:
                if self.d(text=label).exists(timeout=3):
                    claim_btn = self.d(text=label)
                    logger.info("Found offer claim button with text '%s'", label)
                    break

            if claim_btn:
                claim_btn.click()
                time.sleep(5)

            # Step 4: Scan UI hierarchy & ADB logcat for generated 20-character offer URL (https://one.google.com/offer/[20_CHAR_CODE])
            xml_dump = self.d.dump_hierarchy()
            offer_codes = re.findall(r'https?://one\.google\.com/offer/([A-Za-z0-9_-]{16,24})', xml_dump)
            if offer_codes:
                valid_code = [c for c in offer_codes if c.lower() != "redeem"]
                if valid_code:
                    code_url = f"https://one.google.com/offer/{valid_code[0]}"
                    logger.info("Captured 20-character public offer voucher URL: %s", code_url)
                    return code_url

            # Also scan raw text for 20-character alphanumeric voucher codes in UI dump
            raw_codes = re.findall(r'\b([A-Z0-9]{20})\b', xml_dump)
            if raw_codes:
                code_url = f"https://one.google.com/offer/{raw_codes[0]}"
                logger.info("Captured 20-character raw voucher code from Android UI: %s", code_url)
                return code_url

            # Check logcat across all Android services for 20-character voucher codes
            logcat_res = self.d.shell("logcat -d")
            logcat_out = str(getattr(logcat_res, 'output', logcat_res))
            logcat_codes = re.findall(r'https?://one\.google\.com/offer/([A-Za-z0-9_-]{16,24})', logcat_out)
            if logcat_codes:
                valid_logcat = [c for c in logcat_codes if c.lower() != "redeem"]
                if valid_logcat:
                    code_url = f"https://one.google.com/offer/{valid_logcat[0]}"
                    logger.info("Captured 20-character offer URL from Android logcat: %s", code_url)
                    return code_url

            raw_logcat_codes = re.findall(r'\b([A-Z0-9]{20})\b', logcat_out)
            if raw_logcat_codes:
                code_url = f"https://one.google.com/offer/{raw_logcat_codes[0]}"
                logger.info("Captured 20-character raw voucher code from Android logcat: %s", code_url)
                return code_url

            logger.warning("No 20-character offer voucher URL could be extracted from Android Google One app.")
            return None

        except Exception as exc:
            logger.error("Redroid offer claim error: %s", exc)
            raise RedroidAutomationError(f"Redroid automation failed: {exc}") from exc


def check_gemini_offer_redroid(email: str, password: str, device: DeviceProfile, totp_secret: str = "") -> Optional[str]:
    """Helper entry point for Redroid offer claim."""
    automation = RedroidAutomation()
    return automation.claim_gemini_offer(email, password, device, totp_secret)
