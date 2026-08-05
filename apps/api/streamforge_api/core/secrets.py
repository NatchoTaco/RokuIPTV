from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, cast

from cryptography.fernet import Fernet

from streamforge_api.core.config import Settings


class SecretBox:
    def __init__(self, settings: Settings) -> None:
        key_bytes = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt_json(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return self._fernet.encrypt(serialized).decode("ascii")

    def decrypt_json(self, encrypted_payload: str | None) -> dict[str, Any]:
        if not encrypted_payload:
            return {}
        decrypted = self._fernet.decrypt(encrypted_payload.encode("ascii"))
        parsed = json.loads(decrypted.decode("utf-8"))
        if not isinstance(parsed, dict):
            return {}
        return cast(dict[str, Any], parsed)
