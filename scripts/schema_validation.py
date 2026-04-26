#!/usr/bin/env python3
"""Minimal JSON Schema validation for skill-framework schemas.

This intentionally implements only the JSON Schema subset used by the
framework-owned schema files. Unsupported schema keywords fail closed so a new
schema rule cannot silently become documentation-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_KEYWORDS = {
    "$schema",
    "$defs",
    "$ref",
    "additionalProperties",
    "const",
    "enum",
    "items",
    "minItems",
    "minProperties",
    "minimum",
    "properties",
    "required",
    "title",
    "type",
}


@dataclass
class SchemaError(Exception):
    message: str
    path: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}" if self.path else self.message


def validate_schema_document(instance: Any, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for error in _validate(instance, schema, schema, "$"):
        errors.append(str(error))
    return errors


def _validate(instance: Any, schema: Any, root_schema: dict[str, Any], path: str) -> list[SchemaError]:
    if not isinstance(schema, dict):
        return [SchemaError("schema node must be an object", path)]

    unsupported = sorted(key for key in schema if key not in SUPPORTED_KEYWORDS)
    if unsupported:
        return [SchemaError(f"unsupported schema keyword(s): {', '.join(unsupported)}", path)]

    if "$ref" in schema:
        ref = schema["$ref"]
        resolved = _resolve_ref(root_schema, ref)
        if resolved is None:
            return [SchemaError(f"unresolved $ref: {ref}", path)]
        return _validate(instance, resolved, root_schema, path)

    errors: list[SchemaError] = []

    if "const" in schema and instance != schema["const"]:
        errors.append(SchemaError(f"expected const {schema['const']!r}", path))

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(SchemaError(f"expected one of {schema['enum']!r}, got {instance!r}", path))

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(instance, expected_type):
        errors.append(SchemaError(f"expected type {expected_type!r}, got {_json_type(instance)}", path))
        return errors

    if isinstance(instance, dict):
        errors.extend(_validate_object(instance, schema, root_schema, path))
    elif isinstance(instance, list):
        errors.extend(_validate_array(instance, schema, root_schema, path))
    elif isinstance(instance, (int, float)) and not isinstance(instance, bool):
        errors.extend(_validate_number(instance, schema, path))

    return errors


def _validate_object(instance: dict[str, Any], schema: dict[str, Any], root_schema: dict[str, Any], path: str) -> list[SchemaError]:
    errors: list[SchemaError] = []

    for field in schema.get("required", []):
        if field not in instance:
            errors.append(SchemaError(f"missing required property: {field}", path))

    min_properties = schema.get("minProperties")
    if min_properties is not None and len(instance) < min_properties:
        errors.append(SchemaError(f"expected at least {min_properties} properties", path))

    properties = schema.get("properties", {})
    for key, value in instance.items():
        child_path = f"{path}/{_escape_pointer(key)}"
        if key in properties:
            errors.extend(_validate(value, properties[key], root_schema, child_path))
            continue

        additional = schema.get("additionalProperties", True)
        if additional is False:
            errors.append(SchemaError(f"additional property is not allowed: {key}", path))
        elif isinstance(additional, dict):
            errors.extend(_validate(value, additional, root_schema, child_path))

    return errors


def _validate_array(instance: list[Any], schema: dict[str, Any], root_schema: dict[str, Any], path: str) -> list[SchemaError]:
    errors: list[SchemaError] = []

    min_items = schema.get("minItems")
    if min_items is not None and len(instance) < min_items:
        errors.append(SchemaError(f"expected at least {min_items} item(s)", path))

    item_schema = schema.get("items")
    if item_schema is not None:
        for index, item in enumerate(instance):
            errors.extend(_validate(item, item_schema, root_schema, f"{path}/{index}"))

    return errors


def _validate_number(instance: int | float, schema: dict[str, Any], path: str) -> list[SchemaError]:
    minimum = schema.get("minimum")
    if minimum is not None and instance < minimum:
        return [SchemaError(f"expected value >= {minimum}", path)]
    return []


def _matches_type(instance: Any, expected_type: Any) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(instance, item) for item in expected_type)
    if expected_type == "object":
        return isinstance(instance, dict)
    if expected_type == "array":
        return isinstance(instance, list)
    if expected_type == "string":
        return isinstance(instance, str)
    if expected_type == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected_type == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected_type == "boolean":
        return isinstance(instance, bool)
    if expected_type == "null":
        return instance is None
    return False


def _json_type(instance: Any) -> str:
    if isinstance(instance, dict):
        return "object"
    if isinstance(instance, list):
        return "array"
    if isinstance(instance, str):
        return "string"
    if isinstance(instance, bool):
        return "boolean"
    if isinstance(instance, int) and not isinstance(instance, bool):
        return "integer"
    if isinstance(instance, float):
        return "number"
    if instance is None:
        return "null"
    return type(instance).__name__


def _resolve_ref(root_schema: dict[str, Any], ref: str) -> Any | None:
    if not ref.startswith("#/"):
        return None
    current: Any = root_schema
    for part in ref[2:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _escape_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")
