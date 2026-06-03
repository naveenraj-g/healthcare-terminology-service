from typing import Any


def inline_schema(schema: dict) -> dict:
    """
    Resolve all $ref pointers in a Pydantic model_json_schema() output by
    inlining the referenced definitions — makes it safe to embed in FastAPI
    responses={} dicts where the root-level $defs are not accessible.
    Circular references are broken by emitting { "type": "object" }.
    """
    defs: dict = schema.get("$defs", {})

    def _resolve(node: Any, seen: frozenset) -> Any:
        if isinstance(node, dict):
            if "$ref" in node and node["$ref"].startswith("#/$defs/"):
                name = node["$ref"][len("#/$defs/"):]
                if name in seen or name not in defs:
                    return {"type": "object", "description": f"(recursive ref: {name})"}
                return _resolve(defs[name], seen | {name})
            return {k: _resolve(v, seen) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [_resolve(item, seen) for item in node]
        return node

    return _resolve(schema, frozenset())
