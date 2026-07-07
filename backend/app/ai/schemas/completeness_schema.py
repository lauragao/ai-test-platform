"""需求点完备性自检结果 JSON Schema。"""

COMPLETENESS_SCHEMA: dict = {
    "type": "object",
    "required": ["summary", "coverage_map", "sections_to_refill"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "overall_coverage_rate": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "coverage_map": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [
                    "section_id",
                    "coverage_status",
                    "requirement_count",
                    "linked_req_keys",
                ],
                "additionalProperties": False,
                "properties": {
                    "section_id": {"type": "string", "minLength": 1},
                    "section_title": {"type": ["string", "null"]},
                    "coverage_status": {
                        "type": "string",
                        "enum": ["covered", "partial", "missing"],
                    },
                    "requirement_count": {"type": "integer", "minimum": 0},
                    "linked_req_keys": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "gap_reason": {"type": ["string", "null"]},
                },
            },
        },
        "sections_to_refill": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["section_id", "reason"],
                "additionalProperties": False,
                "properties": {
                    "section_id": {"type": "string", "minLength": 1},
                    "reason": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}
