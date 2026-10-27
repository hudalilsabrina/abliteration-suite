"""Microsoft Graph API mailbox reader for Outlook accounts with OAuth refresh tokens."""

import logging
import os
import re
import time
from typing import List, Dict, Optional, Tuple, Set
import requests

logger = logging.getLogger("abliteration.outlook_graph")

OTP_PATTERNS = [
    re.compile(r"verification code is\s+(\d{6})", re.IGNORECASE),
    re.compile(r"code is\s+(\d{6})", re.IGNORECASE),
    re.compile(r"code:\s+(\d{6})", re.IGNORECASE),
    re.compile(r"\b(\d{6})\b[^\n\r]{0,40}(?:verify|verification|expire|abliteration)", re.IGNORECASE),
    re.compile(r"\b(\d{6})\b"),
]


class OutlookGraphMailBox:
    def __init__(self, email: str, refresh_token: str, client_id: str = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"):
        self.email = email
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.access_token: Optional[str] = None
        self.token_expiry: float = 0.0

    def refresh_access_token(self) -> str:
        if self.access_token and time.time() < self.token_expiry - 60:
            return self.access_token
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": "https://graph.microsoft.com/Mail.ReadWrite https://graph.microsoft.com/User.Read offline_access openid profile",
        }
        resp = requests.post(url, data=data, timeout=15)
        resp.raise_for_status()
        d = resp.json()
        self.access_token = d["access_token"]
        self.token_expiry = time.time() + d.get("expires_in", 3600)
        return self.access_token

    def poll_messages(self, limit: int = 10) -> List[Dict[str, str]]:
        tok = self.refresh_access_token()
        url = f"https://graph.microsoft.com/v1.0/me/messages?$top={limit}&$orderby=receivedDateTime%20desc"
        headers = {"Authorization": f"Bearer {tok}"}
        resp = requests.get(url, headers=headers, timeout=15)
        if not resp.ok:
            return []
        msgs = resp.json().get("value") or []
        results = []
        for m in msgs:
            results.append({
                "id": m.get("id"),
                "subject": str(m.get("subject") or ""),
                "body": str((m.get("body") or {}).get("content") or m.get("bodyPreview") or ""),
                "receivedDateTime": m.get("receivedDateTime") or "",
            })
        return results

    def wait_for_otp(self, timeout: int = 60, interval: float = 2.5, ignore_ids: Optional[Set[str]] = None) -> Optional[str]:
        start = time.time()
        logger.info(f"Waiting for fresh OTP email on {self.email} via Graph API (timeout={timeout}s)...")
        seen_ids = set(ignore_ids or set())

        while time.time() - start < timeout:
            try:
                msgs = self.poll_messages(limit=5)
                for m in msgs:
                    mid = m.get("id") or m.get("subject", "")
                    if mid in seen_ids:
                        continue
                    subject = m.get("subject", "")
                    body = m.get("body", "")
                    full_text = f"{subject} {body}"

                    if "verification" in full_text.lower() or "abliteration" in full_text.lower() or "code" in full_text.lower():
                        for pattern in OTP_PATTERNS:
                            match = pattern.search(full_text)
                            if match:
                                otp = match.group(1)
                                logger.info(f"Successfully extracted OTP code: {otp}")
                                return otp
                    seen_ids.add(mid)
            except Exception as e:
                logger.debug(f"Graph poll error: {e}")
            time.sleep(interval)
        return None


def get_oauth_account(email_query: Optional[str] = None) -> Optional[OutlookGraphMailBox]:
    oauth_file = "/root/live_script/accounts_oauth.txt"
    if not os.path.exists(oauth_file):
        return None

    with open(oauth_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("----")
            if len(parts) >= 4:
                em = parts[0].strip()
                cid = parts[2].strip()
                ref_tok = parts[3].strip()
                if email_query:
                    if email_query.lower() in em.lower():
                        return OutlookGraphMailBox(email=em, refresh_token=ref_tok, client_id=cid)
                else:
                    return OutlookGraphMailBox(email=em, refresh_token=ref_tok, client_id=cid)
    return None
