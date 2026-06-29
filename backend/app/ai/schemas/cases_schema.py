"""测试用例生成结果 JSON Schema。"""

CASES_SCHEMA: dict = {
    "type": "object",
    "required": ["summary", "test_cases"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "coverage_notes": {"type": ["string", "null"]},
        "test_cases": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [
                    "case_key",
                    "title",
                    "priority",
                    "case_type",
                    "steps",
                    "expected_result",
                    "source_requirement_ids",
                    "design_methods",
                    "risk_notes",
                ],
                "additionalProperties": False,
                "properties": {
                    "case_key": {"type": "string", "pattern": r"^TC_\d{3,}$"},
                    "module": {"type": ["string", "null"]},
                    "title": {"type": "string", "minLength": 1},
                    "priority": {
                        "type": "string",
                        "enum": ["P0", "P1", "P2", "P3"],
                    },
                    "case_type": {
                        "type": "string",
                        "enum": [
                            "functional",
                            "uat",
                            "exception",
                            "boundary",
                            "permission",
                            "data",
                            "flow",
                        ],
                    },
                    "precondition": {"type": ["string", "null"]},
                    "steps": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "expected_result": {"type": "string", "minLength": 1},
                    "source_requirement_ids": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                    "design_methods": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "string",
                            "enum": ["EP", "BVA", "ST", "EG", "EP+BVA"],
                        },
                    },
                    "regression_type": {
                        "type": ["string", "null"],
                        "enum": ["SMOKE", "CORE", "FULL", None],
                    },
                    "tag": {"type": ["string", "null"]},
                    "remark": {"type": ["string", "null"]},
                    "risk_notes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}
