"""Browser automation engine for Abliteration AI signup & key harvesting using Camoufox."""

import asyncio
import logging
from typing import Dict, Any, Optional, Tuple

from camoufox.async_api import AsyncCamoufox
from src.config import SIGNUP_URL, CONSOLE_URL, APIKEYS_URL, HEADLESS, TIMEOUT

logger = logging.getLogger("abliteration.browser")


async def solve_turnstile(page, timeout: int = 15) -> Tuple[bool, Optional[str]]:
    """Detects and solves the Cloudflare Turnstile widget (handles both visible and auto/invisible modes)."""
    logger.info("Detecting Cloudflare Turnstile widget on Abliteration...")

    for _ in range(timeout * 2):
        # 1. Check if token already populated (auto/managed pass)
        token = await page.evaluate("() => document.querySelector('input[name=\"cf-turnstile-response\"]')?.value")
        if token and len(token) > 20:
            logger.info(f"Turnstile auto-solved! Token len: {len(token)}")
            return True, token

        # 2. Check if visible interactive container is ready
        has_frame = any("challenges.cloudflare.com" in f.url for f in page.frames)
        rect = await page.evaluate("""() => {
            const input = document.querySelector('input[name="cf-turnstile-response"]');
            const parent = input ? input.parentElement : null;
            return parent ? parent.getBoundingClientRect() : null;
        }""")

        if has_frame and rect and rect.get("height", 0) >= 50:
            # Interactive mode - click coordinate
            click_x = rect["x"] + 35
            click_y = rect["y"] + 35
            logger.info(f"Clicking visible Turnstile checkbox at ({click_x:.1f}, {click_y:.1f})...")
            await page.mouse.move(click_x, click_y)
            await asyncio.sleep(0.15)
            await page.mouse.click(click_x, click_y)

        await asyncio.sleep(0.5)

    # Final check
    token = await page.evaluate("() => document.querySelector('input[name=\"cf-turnstile-response\"]')?.value")
    if token and len(token) > 20:
        return True, token

    logger.warning("Turnstile token generation timed out.")
    return False, None


async def start_signup_flow(page, email: str, password: str, referral_code: Optional[str] = None) -> Dict[str, Any]:
    """Fills signup form, solves Turnstile, and submits registration to trigger OTP."""
    target_url = f"{SIGNUP_URL}?referral_code={referral_code}" if referral_code else SIGNUP_URL
    logger.info(f"Navigating to {target_url}...")
    await page.goto(target_url, wait_until="domcontentloaded", timeout=TIMEOUT * 1000)
    await asyncio.sleep(3)

    # 1. Solve Turnstile
    solved, token = await solve_turnstile(page)
    if not solved:
        return {"success": False, "error": "Failed to solve Turnstile challenge"}

    # 2. Fill email & password
    logger.info(f"Filling email {email}...")
    await page.fill('input[type="email"]', email)
    await asyncio.sleep(0.2)
    await page.fill('input[type="password"]', password)
    await asyncio.sleep(0.3)

    # 3. Click Create account
    submit_btn = page.locator('button[type="submit"]:has-text("Create account")')
    if await submit_btn.count() == 0:
        return {"success": False, "error": "Create account button not found"}

    logger.info("Submitting registration form...")
    await submit_btn.first.click()

    # 4. Wait for verification screen
    for _ in range(15):
        await asyncio.sleep(1)
        body_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
        if "verification code" in body_text.lower() or "check your inbox" in body_text.lower():
            logger.info("Successfully arrived at OTP verification screen!")
            return {"success": True, "status": "PENDING_OTP", "email": email}

        # Check for error alert
        alerts = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('[role="alert"], .alert, .text-danger, .error')).map(e => e.innerText);
        }""")
        if alerts:
            return {"success": False, "error": " | ".join(alerts)}

    return {"success": False, "error": "Timed out waiting for verification code screen"}


async def submit_otp_code(page, code: str) -> Dict[str, Any]:
    """Submits the 6-digit OTP code on the verification screen."""
    clean_code = code.strip()
    logger.info(f"Submitting 6-digit verification code: {clean_code}...")

    # Find code input
    code_input = page.locator('input[name="code"], input[maxLength="6"], input[type="text"]')
    if await code_input.count() == 0:
        return {"success": False, "error": "Verification code input not found"}

    # Fill code character by character or fill
    await code_input.first.fill(clean_code)
    await asyncio.sleep(0.5)

    # Check if page already auto-submitted or navigated
    if "/console" in page.url:
        logger.info(f"Auto-navigated to console upon 6th digit: {page.url}")
        return {"success": True, "url": page.url}

    # Click Verify and continue if not disabled
    verify_btn = page.locator('button[type="submit"]:has-text("Verify and continue"), button:has-text("Verify")')
    if await verify_btn.count() > 0:
        try:
            is_disabled = await verify_btn.first.is_disabled()
            if not is_disabled:
                await verify_btn.first.click(timeout=4000)
        except Exception as e:
            logger.debug(f"Verify button click note: {e}")

    # Wait for navigation to console
    for _ in range(15):
        await asyncio.sleep(1)
        cur_url = page.url
        if "/console" in cur_url or cur_url.endswith("/console"):
            logger.info(f"Verification successful! Redirected to {cur_url}")
            return {"success": True, "url": cur_url}

        alerts = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('[role="alert"], .cui-alert, .error')).map(e => e.innerText);
        }""")
        if alerts:
            return {"success": False, "error": " | ".join(alerts)}

    return {"success": False, "error": f"Verification timed out, current URL: {page.url}"}


async def harvest_api_key_from_console(page) -> Dict[str, Any]:
    """Navigates to /console/api-keys and extracts or creates an API key."""
    logger.info(f"Navigating to {APIKEYS_URL}...")
    await page.goto(APIKEYS_URL, wait_until="domcontentloaded", timeout=TIMEOUT * 1000)
    await asyncio.sleep(4)

    # Check if an API key is already shown in the UI
    existing_key = await page.evaluate("""() => {
        const text = document.body ? document.body.innerText : '';
        const match = text.match(/\\b([as]k-[a-zA-Z0-9_-]{20,}|ak_[a-zA-Z0-9_-]{20,})\\b/);
        return match ? match[1] : null;
    }""")
    if existing_key:
        logger.info(f"Found existing API key in console: {existing_key}")
        return {"success": True, "api_key": existing_key}

    # Click Create API Key button if present
    create_btn = page.locator('button:has-text("Create API key"), button:has-text("Create key"), button:has-text("Add key")')
    if await create_btn.count() > 0:
        logger.info("Clicking 'Create API key' button...")
        await create_btn.first.click()
        await asyncio.sleep(2)

        # Fill name input if present
        name_input = page.locator('input[name="name"]')
        if await name_input.count() > 0:
            await name_input.first.fill("auto-key")
            await asyncio.sleep(0.5)

        # Handle dialog confirm if needed
        confirm_btn = page.locator('button[type="submit"]:has-text("Create key"), button[type="submit"]:has-text("Create"), button:has-text("Confirm")')
        if await confirm_btn.count() > 0:
            await confirm_btn.first.click()
            await asyncio.sleep(3)

        # Look for revealed key
        key_after = await page.evaluate("""() => {
            const text = document.body ? document.body.innerText : '';
            const match = text.match(/\\b([as]k-[a-zA-Z0-9_-]{20,}|ak_[a-zA-Z0-9_-]{20,})\\b/);
            return match ? match[1] : null;
        }""")
        if key_after:
            return {"success": True, "api_key": key_after}

    # Extract session cookies as fallback
    cookies = await page.context.cookies()
    ablit_cookies = {c["name"]: c["value"] for c in cookies if "abliteration.ai" in c.get("domain", "")}

    return {
        "success": False,
        "error": "API key not found automatically. Session cookies captured.",
        "cookies": ablit_cookies
    }
