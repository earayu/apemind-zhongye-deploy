#!/usr/bin/env python3
"""Initialize a local ApeRAG Docker Compose demo environment.

The script is intentionally idempotent: it creates the admin user,
public model accounts, models, and model-use defaults only when they
are missing or need to be updated.

Secrets are read from environment variables or command-line arguments.
Do not hard-code provider keys or admin passwords in this file.
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
from dataclasses import dataclass, field
from typing import Any

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@aperag.local"
DEFAULT_API_URL = "http://127.0.0.1:8000"


@dataclass(frozen=True)
class AccountSpec:
    key: str
    provider_type: str
    name: str
    display_name: str
    base_url: str
    api_key: str | None


@dataclass(frozen=True)
class ModelSpec:
    account_key: str
    provider_model_id: str
    display_name: str
    capability: str
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelUseSpec:
    scenario: str
    strategy: str
    primary: tuple[str, str]
    fallbacks: list[tuple[str, str]] = field(default_factory=list)


MODEL_SPECS = [
    ModelSpec(
        "dashscope",
        "text-embedding-v4",
        "Bailian text-embedding-v4",
        "embedding",
        {"embedding_dimensions": 1024, "allowed_scenarios": ["collection_embedding"]},
    ),
    ModelSpec(
        "openrouter",
        "deepseek/deepseek-v4-pro",
        "DeepSeek V4 Pro",
        "chat",
        {
            "context_window": 128000,
            "max_output_tokens": 65536,
            "supports_tool_calling": True,
            "allowed_scenarios": ["agent_chat"],
        },
    ),
    ModelSpec(
        "openrouter",
        "openai/gpt-5.4",
        "OpenAI GPT-5.4",
        "chat",
        {
            "context_window": 400000,
            "max_output_tokens": 65536,
            "supports_tool_calling": True,
            "allowed_scenarios": ["agent_chat"],
        },
    ),
    ModelSpec(
        "openrouter",
        "anthropic/claude-sonnet-4.6",
        "Claude Sonnet 4.6",
        "chat",
        {
            "context_window": 200000,
            "max_output_tokens": 65536,
            "supports_tool_calling": True,
            "allowed_scenarios": ["agent_chat"],
        },
    ),
    ModelSpec(
        "openrouter",
        "moonshotai/kimi-k2.6",
        "Kimi K2.6",
        "chat",
        {
            "context_window": 256000,
            "max_output_tokens": 65536,
            "supports_tool_calling": True,
            "allowed_scenarios": ["agent_chat"],
        },
    ),
    ModelSpec(
        "openrouter",
        "qwen/qwen3.5-35b-a3b",
        "OpenRouter Qwen3.5 35B A3B",
        "chat",
        {
            "context_window": 131072,
            "max_output_tokens": 32768,
            "allowed_scenarios": ["collection_completion", "background_task"],
        },
    ),
    ModelSpec(
        "openrouter",
        "qwen/qwen3-30b-a3b-instruct-2507",
        "OpenRouter Qwen3 30B A3B Instruct 2507",
        "chat",
        {
            "context_window": 32768,
            "max_output_tokens": 16384,
            "allowed_scenarios": ["collection_completion", "background_task"],
        },
    ),
    ModelSpec(
        "openrouter",
        "google/gemini-2.5-flash",
        "OpenRouter Gemini 2.5 Flash",
        "chat",
        {
            "context_window": 1048576,
            "max_output_tokens": 65536,
            "supports_tool_calling": True,
            "allowed_scenarios": ["collection_completion", "background_task"],
        },
    ),
    ModelSpec(
        "openrouter",
        "xiaomi/mimo-v2-flash",
        "OpenRouter MiMo v2 Flash",
        "chat",
        {
            "context_window": 32768,
            "max_output_tokens": 8192,
            "allowed_scenarios": ["collection_completion", "background_task"],
        },
    ),
    ModelSpec(
        "openrouter",
        "qwen/qwen-turbo",
        "OpenRouter Qwen Turbo",
        "chat",
        {
            "context_window": 32768,
            "max_output_tokens": 8192,
            "allowed_scenarios": ["collection_completion", "background_task"],
        },
    ),
]

MODEL_USE_SPECS = [
    ModelUseSpec("collection_embedding", "single", ("dashscope", "text-embedding-v4")),
    ModelUseSpec(
        "agent_chat",
        "fallback",
        ("openrouter", "deepseek/deepseek-v4-pro"),
        [
            ("openrouter", "openai/gpt-5.4"),
            ("openrouter", "anthropic/claude-sonnet-4.6"),
            ("openrouter", "moonshotai/kimi-k2.6"),
        ],
    ),
    ModelUseSpec(
        "background_task",
        "fallback",
        ("openrouter", "qwen/qwen3.5-35b-a3b"),
        [
            ("openrouter", "qwen/qwen3-30b-a3b-instruct-2507"),
            ("openrouter", "google/gemini-2.5-flash"),
            ("openrouter", "xiaomi/mimo-v2-flash"),
            ("openrouter", "qwen/qwen-turbo"),
        ],
    ),
    ModelUseSpec(
        "collection_completion",
        "fallback",
        ("openrouter", "qwen/qwen3.5-35b-a3b"),
        [
            ("openrouter", "qwen/qwen3-30b-a3b-instruct-2507"),
            ("openrouter", "google/gemini-2.5-flash"),
            ("openrouter", "xiaomi/mimo-v2-flash"),
            ("openrouter", "qwen/qwen-turbo"),
        ],
    ),
]


class ApeRAGClient:
    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        import requests

        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(
            method,
            self._url(path),
            timeout=self.timeout_seconds,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def register(self, username: str, email: str, password: str) -> bool:
        response = self.session.post(
            self._url("/api/v2/auth/register"),
            json={"username": username, "email": email, "password": password},
            timeout=self.timeout_seconds,
        )
        if response.status_code in (200, 201):
            return True
        if response.status_code in (400, 409):
            return False
        response.raise_for_status()
        return False

    def login(self, username: str, password: str) -> None:
        self.request("POST", "/api/v2/auth/login", json={"username": username, "password": password})

    def list_model_accounts(self, scope: str) -> list[dict[str, Any]]:
        return self.request("GET", "/api/v2/model-accounts", params={"scope": scope}).json().get("items", [])

    def create_model_account(self, payload: dict[str, Any], scope: str) -> dict[str, Any]:
        return self.request("POST", "/api/v2/model-accounts", json=payload, params={"scope": scope}).json()

    def update_model_account(self, account_id: str, payload: dict[str, Any], scope: str) -> dict[str, Any]:
        return self.request(
            "PUT",
            f"/api/v2/model-accounts/{account_id}",
            json=payload,
            params={"scope": scope},
        ).json()

    def list_models(self, account_id: str, scope: str) -> list[dict[str, Any]]:
        return (
            self.request("GET", f"/api/v2/model-accounts/{account_id}/models", params={"scope": scope})
            .json()
            .get("items", [])
        )

    def create_model(self, payload: dict[str, Any], scope: str) -> dict[str, Any]:
        return self.request("POST", "/api/v2/models", json=payload, params={"scope": scope}).json()

    def update_model(self, model_id: str, payload: dict[str, Any], scope: str) -> dict[str, Any]:
        return self.request("PUT", f"/api/v2/models/{model_id}", json=payload, params={"scope": scope}).json()

    def list_model_uses(self, scope: str) -> list[dict[str, Any]]:
        return self.request("GET", "/api/v2/model-uses", params={"scope": scope}).json().get("items", [])

    def update_model_use(self, scenario: str, payload: dict[str, Any], scope: str) -> dict[str, Any]:
        return self.request(
            "PUT",
            f"/api/v2/model-uses/{scenario}",
            json=payload,
            params={"scope": scope},
        ).json()


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def log(message: str) -> None:
    print(message, flush=True)


def build_account_specs(args: argparse.Namespace) -> list[AccountSpec]:
    return [
        AccountSpec(
            key="dashscope",
            provider_type="dashscope",
            name=args.dashscope_account_name,
            display_name="AlibabaCloud Bailian",
            base_url=args.dashscope_base_url,
            api_key=args.dashscope_api_key,
        ),
        AccountSpec(
            key="openrouter",
            provider_type="openai_compatible",
            name=args.openrouter_account_name,
            display_name="OpenRouter",
            base_url=args.openrouter_base_url,
            api_key=args.openrouter_api_key,
        ),
    ]


def ensure_admin(client: ApeRAGClient, args: argparse.Namespace) -> None:
    log("== 1. Admin account ==")
    created = client.register(args.admin_username, args.admin_email, args.admin_password)
    if created:
        log(f"created admin user: {args.admin_username}")
    else:
        log(f"admin user exists: {args.admin_username}")

    client.login(args.admin_username, args.admin_password)
    log("admin login ok")


def ensure_accounts(
    client: ApeRAGClient,
    account_specs: list[AccountSpec],
    scope: str,
    update_existing_keys: bool,
) -> dict[str, str]:
    log("== 2. Model accounts ==")
    existing = {item["name"]: item for item in client.list_model_accounts(scope)}
    account_id_by_key: dict[str, str] = {}

    for spec in account_specs:
        existing_account = existing.get(spec.name)
        if existing_account:
            account_id_by_key[spec.key] = existing_account["id"]
            if spec.api_key and update_existing_keys:
                client.update_model_account(
                    existing_account["id"],
                    {
                        "name": spec.name,
                        "display_name": spec.display_name,
                        "base_url": spec.base_url,
                        "api_key": spec.api_key,
                        "status": "ACTIVE",
                    },
                    scope,
                )
                log(f"updated account: {spec.display_name} ({spec.name})")
            else:
                log(f"account exists: {spec.display_name} ({spec.name})")
            continue

        if not spec.api_key:
            log(f"skip account without api key: {spec.display_name} ({spec.name})")
            continue

        created = client.create_model_account(
            {
                "provider_type": spec.provider_type,
                "name": spec.name,
                "display_name": spec.display_name,
                "base_url": spec.base_url,
                "api_key": spec.api_key,
            },
            scope,
        )
        account_id_by_key[spec.key] = created["id"]
        log(f"created account: {spec.display_name} ({created['id']})")

    return account_id_by_key


def ensure_models(client: ApeRAGClient, account_id_by_key: dict[str, str], scope: str) -> dict[tuple[str, str], str]:
    log("== 3. Models ==")
    existing_model_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for account_key, account_id in account_id_by_key.items():
        for model in client.list_models(account_id, scope):
            existing_model_by_key[(account_key, model["provider_model_id"])] = model

    model_id_by_key: dict[tuple[str, str], str] = {}
    for spec in MODEL_SPECS:
        account_id = account_id_by_key.get(spec.account_key)
        if not account_id:
            log(f"skip model without account: {spec.display_name}")
            continue

        key = (spec.account_key, spec.provider_model_id)
        existing_model = existing_model_by_key.get(key)
        payload = {
            "account_id": account_id,
            "provider_model_id": spec.provider_model_id,
            "display_name": spec.display_name,
            "capability": spec.capability,
            "runner_type": "openai_compatible",
            "runner_config": {},
            **spec.attrs,
        }
        if existing_model:
            model_id_by_key[key] = existing_model["id"]
            client.update_model(existing_model["id"], payload, scope)
            log(f"updated model: {spec.display_name}")
            continue

        created = client.create_model(payload, scope)
        model_id_by_key[key] = created["id"]
        log(f"created model: {spec.display_name}")

    return model_id_by_key


def ensure_model_uses(client: ApeRAGClient, model_id_by_key: dict[tuple[str, str], str], scope: str) -> None:
    log("== 4. Model uses ==")
    existing_uses = {item["scenario"]: item for item in client.list_model_uses(scope)}

    for spec in MODEL_USE_SPECS:
        primary_id = model_id_by_key.get(spec.primary)
        if not primary_id:
            log(f"skip model use without primary model: {spec.scenario}")
            continue

        fallback_ids = [model_id_by_key[key] for key in spec.fallbacks if key in model_id_by_key]
        payload = {
            "primary_model_id": primary_id,
            "fallback_model_ids": fallback_ids,
            "strategy": spec.strategy,
            "enabled": True,
        }
        existing = existing_uses.get(spec.scenario)
        if (
            existing
            and existing.get("primary_model_id") == primary_id
            and existing.get("fallback_model_ids", []) == fallback_ids
            and existing.get("strategy") == spec.strategy
            and existing.get("enabled") is True
        ):
            log(f"model use already configured: {spec.scenario}")
            continue

        client.update_model_use(spec.scenario, payload, scope)
        log(f"configured model use: {spec.scenario}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a local ApeRAG Docker Compose demo.")
    parser.add_argument("--api-url", default=env("APERAG_API_URL", DEFAULT_API_URL))
    parser.add_argument("--scope", choices=["public", "user"], default=env("APERAG_INIT_SCOPE", "public"))
    parser.add_argument("--admin-username", default=env("APERAG_ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME))
    parser.add_argument("--admin-email", default=env("APERAG_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL))
    parser.add_argument("--admin-password", default=env("APERAG_ADMIN_PASSWORD"))
    parser.add_argument("--generate-admin-password", action="store_true")
    parser.add_argument(
        "--dashscope-api-key",
        default=env("DASHSCOPE_API_KEY", env("ALIBABA_CLOUD_API_KEY")),
    )
    parser.add_argument(
        "--dashscope-base-url",
        default=env("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )
    parser.add_argument(
        "--dashscope-account-name",
        default=env("DASHSCOPE_ACCOUNT_NAME", "alibabacloud-bailian-local"),
    )
    parser.add_argument("--openrouter-api-key", default=env("OPENROUTER_API_KEY"))
    parser.add_argument(
        "--openrouter-base-url",
        default=env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    parser.add_argument("--openrouter-account-name", default=env("OPENROUTER_ACCOUNT_NAME", "openrouter-local"))
    parser.add_argument("--update-existing-keys", action="store_true", default=env("UPDATE_EXISTING_KEYS") == "1")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated_admin_password = False
    if not args.admin_password:
        if args.generate_admin_password:
            args.admin_password = random_password()
            generated_admin_password = True
        else:
            print(
                "APERAG_ADMIN_PASSWORD is required. Set it in the environment or pass --admin-password.",
                file=sys.stderr,
            )
            return 2

    client = ApeRAGClient(args.api_url)
    ensure_admin(client, args)
    account_id_by_key = ensure_accounts(
        client,
        build_account_specs(args),
        args.scope,
        args.update_existing_keys,
    )
    model_id_by_key = ensure_models(client, account_id_by_key, args.scope)
    ensure_model_uses(client, model_id_by_key, args.scope)

    log("== Done ==")
    log(f"web url: {args.api_url.replace(':8000', ':3000') if ':8000' in args.api_url else args.api_url}")
    log(f"admin username: {args.admin_username}")
    if generated_admin_password:
        log(f"generated admin password: {args.admin_password}")
    else:
        log("admin password: provided by APERAG_ADMIN_PASSWORD or --admin-password")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
