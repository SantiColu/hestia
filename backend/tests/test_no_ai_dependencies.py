"""Hestia is deterministic and works without AI (ADR 0015).

The backend must not declare or lock any AI SDK or framework. Imports are checked by the
import-linter contract "Hestia never imports AI SDKs or frameworks" (pyproject.toml); this
test covers declared dependencies (every workspace pyproject) and the full lock, including
transitive packages. `pydantic` itself is allowed: only Pydantic's AI and observability
products are forbidden. `mcp/` is a separate project and is out of scope on purpose.
"""

import re
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]

# Normalized distribution names (PEP 503). A name ending in "-*" forbids the whole family.
FORBIDDEN = (
    "anthropic",
    "openai",
    "pydantic-ai",
    "pydantic-ai-*",
    "logfire",
    "logfire-*",
    "langchain",
    "langchain-*",
    "llama-index",
    "llama-index-*",
    "litellm",
    "transformers",
)

# Top-level modules the import-linter contract must forbid.
FORBIDDEN_MODULES = {
    "anthropic",
    "openai",
    "pydantic_ai",
    "logfire",
    "langchain",
    "llama_index",
    "litellm",
    "transformers",
}


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def is_forbidden(name: str) -> bool:
    name = normalize(name)
    return any(
        name.startswith(rule[:-1]) if rule.endswith("-*") else name == rule for rule in FORBIDDEN
    )


def requirement_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    assert match, f"unparseable requirement: {requirement!r}"
    return match.group(1)


def declared(pyproject: dict[str, Any]) -> Iterator[str]:
    project = pyproject.get("project", {})
    yield from project.get("dependencies", [])
    for extra in project.get("optional-dependencies", {}).values():
        yield from extra
    for group in pyproject.get("dependency-groups", {}).values():
        yield from (item for item in group if isinstance(item, str))


def test_rule_matches_expected_names() -> None:
    for name in ("openai", "pydantic_ai", "pydantic-ai-slim", "langchain-openai", "Logfire-API"):
        assert is_forbidden(name), name
    for name in ("pydantic", "pydantic-core", "pydantic-settings", "langchainish", "openapi"):
        assert not is_forbidden(name), name


def test_no_ai_dependency_is_declared() -> None:
    pyprojects = [BACKEND / "pyproject.toml", *BACKEND.glob("*/*/pyproject.toml")]
    assert len(pyprojects) > 1, "workspace members not found"
    offenders = [
        f"{path.relative_to(BACKEND)}: {requirement}"
        for path in pyprojects
        for requirement in declared(tomllib.loads(path.read_text()))
        if is_forbidden(requirement_name(requirement))
    ]
    assert not offenders, "AI dependencies are forbidden (ADR 0015):\n" + "\n".join(offenders)


def test_no_ai_package_is_locked() -> None:
    lock = tomllib.loads((BACKEND / "uv.lock").read_text())
    packages = [package["name"] for package in lock["package"]]
    assert packages, "uv.lock has no packages"
    offenders = sorted(name for name in packages if is_forbidden(name))
    assert not offenders, f"AI packages in uv.lock are forbidden (ADR 0015): {offenders}"


def test_import_contract_forbids_ai_modules() -> None:
    config = tomllib.loads((BACKEND / "pyproject.toml").read_text())["tool"]["importlinter"]
    assert config.get("include_external_packages") is True
    contracts = [
        contract
        for contract in config["contracts"]
        if contract["name"] == "Hestia never imports AI SDKs or frameworks"
    ]
    assert len(contracts) == 1, "the no-AI import-linter contract is missing"
    missing = FORBIDDEN_MODULES - set(contracts[0]["forbidden_modules"])
    assert not missing, f"import-linter contract does not forbid: {sorted(missing)}"
