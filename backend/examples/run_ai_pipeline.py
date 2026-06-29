#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AiService 使用示例。

用法：
  cd backend
  cp .env.example .env   # 填入 AI_API_KEY
  pip install -r requirements.txt
  python examples/run_ai_pipeline.py --file ../requirements/requirement.md
"""

import argparse
import json
import re
import sys
from pathlib import Path

# 将 backend 目录加入模块搜索路径
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.ai import AiService, DocumentSectionInput  # noqa: E402
from app.ai.models import AiRunRecord  # noqa: E402


def parse_markdown_sections(content: str) -> list[DocumentSectionInput]:
    """将 Markdown 按标题切分为章节（MVP 简易解析）。"""
    sections: list[DocumentSectionInput] = []
    current_title: str | None = None
    current_level = 1
    current_lines: list[str] = []
    sec_idx = 0

    def flush():
        nonlocal sec_idx
        text = "\n".join(current_lines).strip()
        if not text and not current_title:
            return
        sec_idx += 1
        sections.append(
            DocumentSectionInput(
                section_id=f"sec_{sec_idx:03d}",
                title=current_title,
                level=current_level,
                content=text or (current_title or ""),
            )
        )

    for line in content.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush()
            current_level = len(heading.group(1))
            current_title = heading.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    flush()

    if not sections:
        sections.append(
            DocumentSectionInput(
                section_id="sec_001",
                title="全文",
                level=1,
                content=content.strip(),
            )
        )
    return sections


def on_run_complete(record: AiRunRecord) -> None:
    print(
        f"  [ai_run] {record.run_type.value} | "
        f"status={record.status} | tokens={record.total_tokens} | "
        f"duration={record.duration_ms}ms"
    )


def main():
    parser = argparse.ArgumentParser(description="运行 AI 需求分析 + 用例生成流水线")
    parser.add_argument("--file", required=True, help="需求文档路径（.md / .txt）")
    parser.add_argument(
        "--step",
        choices=["all", "extract", "analyze", "cases"],
        default="all",
        help="执行步骤，默认全流程",
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)

    content = file_path.read_text(encoding="utf-8")
    sections = parse_markdown_sections(content)
    print(f"已解析 {len(sections)} 个章节，开始 AI 处理...\n")

    service = AiService(on_run_complete=on_run_complete)

    if args.step == "all":
        result = service.run_full_pipeline(sections)
        output = {
            "extract": result["extract"].model_dump(),
            "analyze": result["analyze"].model_dump(),
            "cases": result["cases"].model_dump(),
        }
    elif args.step == "extract":
        output = service.extract_requirements(sections).model_dump()
    elif args.step == "analyze":
        extract = service.extract_requirements(sections)
        output = service.analyze_requirements(sections, extract.requirements).model_dump()
    else:
        extract = service.extract_requirements(sections)
        analyze = service.analyze_requirements(sections, extract.requirements)
        output = service.generate_test_cases(
            extract.requirements, analyze.issues
        ).model_dump()

    out_path = BACKEND_ROOT / "tmp" / f"ai_result_{file_path.stem}.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {out_path}")


if __name__ == "__main__":
    main()
