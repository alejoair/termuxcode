"""Utilities for partial agent execution based on missing blackboard fields."""
from __future__ import annotations

from pydantic import BaseModel
from termuxcode.core.memory.blackboard import Blackboard


def get_missing_fields(field_map: dict[str, str], bb: Blackboard) -> dict[str, str]:
    """Check the blackboard and return only the fields that are missing or empty.

    Args:
        field_map: Mapping of blackboard paths to schema field names.
        bb: Blackboard instance to check.

    Returns:
        Subset of field_map where the blackboard value is missing or empty.
    """
    missing = {}
    for bb_path, schema_field in field_map.items():
        value = bb.get(bb_path)
        if value is None or value == "" or value == []:
            missing[bb_path] = schema_field
    return missing


def build_partial_schema(
    full_model: type[BaseModel],
    missing_fields: dict[str, str],
) -> dict | None:
    """Build a JSON schema containing only the missing fields.

    Args:
        full_model: The full Pydantic model class.
        missing_fields: Output of get_missing_fields (bb_path -> schema_field).

    Returns:
        A JSON schema dict with only the missing fields, or None if nothing missing.
    """
    if not missing_fields:
        return None

    full_schema = full_model.model_json_schema()
    needed = set(missing_fields.values())
    all_fields = set(full_schema.get("properties", {}).keys())

    # If all fields are missing, return the full schema as-is
    if needed == all_fields:
        return full_schema

    partial = {
        "title": full_schema.get("title", "PartialResponse"),
        "type": "object",
        "properties": {
            k: v for k, v in full_schema.get("properties", {}).items()
            if k in needed
        },
    }
    # Preserve description if present
    if "description" in full_schema:
        partial["description"] = full_schema["description"]
    return partial
