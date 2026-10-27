"""Configuration loader for Abliteration Suite."""

from pathlib import Path
import tomllib

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.toml"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {}


CONFIG = load_config()

BASE_URL = CONFIG.get("app", {}).get("base_url", "https://abliteration.ai")
API_BASE_URL = CONFIG.get("app", {}).get("api_base_url", "https://api.abliteration.ai")
SIGNUP_URL = CONFIG.get("app", {}).get("signup_url", "https://abliteration.ai/sign-up")
SIGNIN_URL = CONFIG.get("app", {}).get("signin_url", "https://abliteration.ai/sign-in")
CONSOLE_URL = CONFIG.get("app", {}).get("console_url", "https://abliteration.ai/console")
APIKEYS_URL = CONFIG.get("app", {}).get("apikeys_url", "https://abliteration.ai/console/api-keys")

FLAGSHIP_MODEL = CONFIG.get("models", {}).get("flagship", "abliterated-model-large-v2")
MODELS = CONFIG.get("models", {}).get("models", [
    "abliterated-model-large-v2",
    "abliterated-model-large",
    "abliterated-model"
])

NINE_ROUTER_URL = CONFIG.get("nine_router", {}).get("url", "http://127.0.0.1:20127")
NINE_ROUTER_PROVIDER = CONFIG.get("nine_router", {}).get("provider_name", "abliteration")

HEADLESS = CONFIG.get("browser", {}).get("headless", True)
TIMEOUT = CONFIG.get("browser", {}).get("timeout", 35)
TURNSTILE_SITEKEY = CONFIG.get("browser", {}).get("turnstile_sitekey", "0x4AAAAAAEcO2qYYBE_ztENL")

DATA_DIR = ROOT_DIR / CONFIG.get("storage", {}).get("data_dir", "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNTS_JSON = ROOT_DIR / CONFIG.get("storage", {}).get("accounts_json", "data/accounts.json")
KEYS_TXT = ROOT_DIR / CONFIG.get("storage", {}).get("keys_txt", "data/keys.txt")
