"""Explicit environment selection; no credential discovery outside the chosen dotenv file."""
import os
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, SecretStr, model_validator


class ConfigurationError(ValueError):
    pass


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)
    mode: Literal["test", "live"] = "test"
    key_id: SecretStr
    key_secret: SecretStr

    @model_validator(mode="after")
    def validate_pair(self):
        key = self.key_id.get_secret_value()
        secret = self.key_secret.get_secret_value()
        if (not key.startswith(f"rzp_{self.mode}_") or not secret or key.strip() != key
                or secret.strip() != secret or "replace_me" in key or secret == "replace_me"):
            raise ValueError("Invalid credentials for selected mode.")
        return self

    @classmethod
    def load(cls, env_file: str | Path = ".env") -> "Settings":
        env = {**dotenv_values(env_file), **os.environ}
        mode = env.get("RZP_MODE", "test")
        if mode not in {"test", "live"}:
            raise ConfigurationError("RZP_MODE must be test or live.")
        prefix = f"RZP_{mode.upper()}_"
        key = env.get(prefix + "KEY_ID") or env.get("RZP_KEY_ID") or ""
        secret = env.get(prefix + "KEY_SECRET") or env.get("RZP_KEY_SECRET") or ""
        if not key or not secret:
            raise ConfigurationError(f"Configure {prefix}KEY_ID and {prefix}KEY_SECRET in .env.")
        for other_mode in ("test", "live"):
            if other_mode != mode and key.startswith(f"rzp_{other_mode}_"):
                raise ConfigurationError(
                    f"Your API key is for {other_mode.upper()}, but RZP_MODE={mode}. "
                    f"Use a {mode.upper()} key, or explicitly set RZP_MODE={other_mode} "
                    f"and configure RZP_{other_mode.upper()}_KEY_ID / "
                    f"RZP_{other_mode.upper()}_KEY_SECRET. Restart after editing .env."
                )
        if not key.startswith(f"rzp_{mode}_") or key.strip() != key or secret.strip() != secret:
            raise ConfigurationError("Credential format or selected mode does not match. Check .env.")
        if "replace_me" in key or secret == "replace_me":
            raise ConfigurationError("Replace example credentials before connecting.")
        return cls(mode=mode, key_id=SecretStr(key), key_secret=SecretStr(secret))
