"""需求问题分析结果 JSON Schema。"""

ISSUES_SCHEMA: dict = {
    "type": "object",
    "required": ["summary", "issues"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "issue_key",
                    "issue_type",
                    "severity",
                    "title",
                    "description",
                    "evidence_type",
                    "source_refs",
                ],
                "additionalProperties": False,
                "properties": {
                    "issue_key": {"type": "string", "pattern": r"^issue_\d{3,}$"},
                    "requirement_id": {"type": ["string", "null"]},
                    "issue_type": {
                        "type": "string",
                        "enum": ["unclear", "missing", "conflict", "risk"],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "title": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "suggestion": {"type": ["string", "null"]},
                    "evidence_type": {
                        "type": "string",
                        "enum": ["explicit", "inferred"],
                    },
                    "source_refs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["section_id", "quote"],
                            "additionalProperties": False,
                            "properties": {
                                "section_id": {"type": "string"},
                                "quote": {"type": "string", "minLength": 1},
                                "page_no": {"type": ["integer", "null"]},
                            },
                        },
                    },
                },
            },
        },
    },
}
