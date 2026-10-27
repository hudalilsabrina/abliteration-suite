"""Account and API Key management for Abliteration Suite."""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from src.config import ACCOUNTS_JSON, KEYS_TXT


def load_state() -> Dict[str, Dict]:
    if ACCOUNTS_JSON.exists():
        try:
            with open(ACCOUNTS_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state: Dict[str, Dict]):
    with open(ACCOUNTS_JSON, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def load_keys() -> List[str]:
    keys = []
    if KEYS_TXT.exists():
        with open(KEYS_TXT, "r", encoding="utf-8") as f:
            for line in f:
                k = line.strip()
                if k and not k.startswith("#"):
                    keys.append(k)

    state = load_state()
    for acc in state.values():
        k = acc.get("api_key")
        if k and k not in keys:
            keys.append(k)

    return sorted(list(set(keys)))


def save_key_to_file(key: str):
    existing = []
    if KEYS_TXT.exists():
        with open(KEYS_TXT, "r", encoding="utf-8") as f:
            existing = [l.strip() for l in f if l.strip()]

    if key not in existing:
        with open(KEYS_TXT, "a", encoding="utf-8") as f:
            f.write(f"{key}\n")


def record_account(email: str, password: str, api_key: Optional[str] = None, status: str = "PENDING_VERIFICATION", **kwargs):
    state = load_state()
    state[email] = {
        "email": email,
        "password": password,
        "api_key": api_key,
        "status": status,
        "updated_at": datetime.now().isoformat(),
        **kwargs
    }
    save_state(state)
    if api_key:
        save_key_to_file(api_key)


def update_status(email: str, status: str, api_key: Optional[str] = None, **kwargs):
    state = load_state()
    if email not in state:
        state[email] = {"email": email}
    state[email]["status"] = status
    if api_key:
        state[email]["api_key"] = api_key
        save_key_to_file(api_key)
    state[email]["updated_at"] = datetime.now().isoformat()
    state[email].update(kwargs)
    save_state(state)
