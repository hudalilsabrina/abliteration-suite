"""API Client for Abliteration AI (OpenAI-compatible inference)."""

import urllib.request
import urllib.error
import json
import logging
from typing import Dict, Any, Optional, List

from src.config import API_BASE_URL, FLAGSHIP_MODEL

logger = logging.getLogger("abliteration.client")


class AbliterationClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Abliteration-Suite/1.0",
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = FLAGSHIP_MODEL,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calls /v1/chat/completions on api.abliteration.ai."""
        url = f"{API_BASE_URL}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.code, "message": e.read().decode()}
        except Exception as e:
            return {"error": str(e)}

    def get_models(self) -> Dict[str, Any]:
        """Fetches available model catalog from /v1/models."""
        url = f"{API_BASE_URL}/v1/models"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.code, "message": e.read().decode()}
        except Exception as e:
            return {"error": str(e)}

    def check_key_validity(self) -> Dict[str, Any]:
        """Validates key by sending a single lightweight completion request."""
        res = self.chat_completion(
            messages=[{"role": "user", "content": "1+1=?"}],
            model=FLAGSHIP_MODEL,
            max_tokens=10
        )
        if "choices" in res:
            answer = res["choices"][0]["message"]["content"]
            return {"valid": True, "answer": answer.strip()}
        return {"valid": False, "response": res}
