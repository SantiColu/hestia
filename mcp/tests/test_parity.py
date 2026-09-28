"""Parity API ↔ MCP: every API operation in the contract has exactly one tool."""

import json
import pathlib
from typing import Any

from hestia_mcp.api import NOT_TOOLS, OPERATIONS
from hestia_mcp.server import TOOL_OPERATIONS

CONTRACT = pathlib.Path(__file__).parents[2] / "shared" / "openapi.json"


def _contract_operations() -> dict[str, tuple[str, str]]:
    spec: dict[str, Any] = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return {
        op["operationId"]: (method.upper(), path)
        for path, item in spec["paths"].items()
        for method, op in item.items()
    }


def test_every_api_operation_has_a_tool() -> None:
    contract = _contract_operations()
    covered = set(TOOL_OPERATIONS.values())
    missing = set(contract) - covered - set(NOT_TOOLS)
    assert missing == set(), f"API operations without an MCP tool: {sorted(missing)}"


def test_one_tool_per_operation() -> None:
    operations = list(TOOL_OPERATIONS.values())
    assert len(operations) == len(set(operations))


def test_tools_match_contract_routes() -> None:
    contract = _contract_operations()
    for operation_id, route in OPERATIONS.items():
        assert operation_id in contract, f"{operation_id} is not in shared/openapi.json"
        assert contract[operation_id] == route, operation_id
    assert set(NOT_TOOLS) <= set(contract)


def test_literal_enums_match_contract() -> None:
    from typing import get_args

    from hestia_mcp.server import StageType, TemplateId

    schemas = json.loads(CONTRACT.read_text(encoding="utf-8"))["components"]["schemas"]
    assert set(get_args(StageType)) == set(schemas["StageType"]["enum"])
    assert set(get_args(TemplateId)) == set(schemas["TemplateId"]["enum"])
