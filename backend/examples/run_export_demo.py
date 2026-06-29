#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出功能示例：生成 Excel 与 XMind。"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.ai.models import RequirementItem, TestCaseItem  # noqa: E402
from app.exporters import ExcelExporter, XmindExporter  # noqa: E402
from app.quality import QualityCheckService  # noqa: E402


def main():
    requirements = [
        RequirementItem(
            req_key="req_001",
            module="登录",
            title="手机号验证码登录",
            description="用户可以通过手机号和验证码登录系统。",
            priority="P0",
        )
    ]
    cases = [
        TestCaseItem(
            case_key="TC_001",
            module="登录/验证码登录",
            title="输入正确手机号和验证码登录成功",
            priority="P0",
            case_type="functional",
            precondition="用户手机号已注册且账号状态正常",
            steps=[
                "1. 打开登录页面",
                "2. 输入已注册手机号",
                "3. 输入正确验证码",
                "4. 点击登录按钮",
            ],
            expected_result="登录成功，进入系统首页",
            source_requirement_ids=["req_001"],
            design_methods=["ST"],
            regression_type="SMOKE",
            tag="PC",
        )
    ]

    output_dir = BACKEND_ROOT / "tmp" / "exports"
    xmind_path = XmindExporter().export(cases, output_dir / "demo_test_cases.xmind")
    excel_path = ExcelExporter().export(
        cases,
        output_dir / "demo_test_cases.xlsx",
        requirements=requirements,
        include_traceability=True,
    )
    quality = QualityCheckService().check(requirements, cases)

    print(f"XMind: {xmind_path}")
    print(f"Excel: {excel_path}")
    print(f"Quality: {quality.model_dump()}")


if __name__ == "__main__":
    main()
