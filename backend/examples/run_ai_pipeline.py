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
import sys
from pathlib import Path

# 将 backend 目录加入模块搜索路径
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.ai import AiService, DocumentSectionInput  # noqa: E402
from app.ai.models import AiRunRecord  # noqa: E402
from app.document.enrich import enrich_sections_with_snapshot  # noqa: E402
from app.document.markdown_parser import parse_markdown_sections  # noqa: E402
from app.tasks import PipelineTaskRunner, default_task_service  # noqa: E402
from app.tasks.pipeline_runner import default_result_store  # noqa: E402


def on_run_complete(record: AiRunRecord) -> None:
    print(
        f"  [ai_run] {record.run_type.value} | "
        f"status={record.status} | tokens={record.total_tokens} | "
        f"duration={record.duration_ms}ms"
    )


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = data.model_dump() if hasattr(data, "model_dump") else data
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="运行 AI 需求分析 + 用例生成流水线")
    parser.add_argument("--file", required=True, help="需求文档路径（.md / .txt）")
    parser.add_argument(
        "--step",
        choices=["all", "extract", "completeness", "analyze", "cases"],
        default="all",
        help="执行步骤，默认全流程",
    )
    parser.add_argument("--title", default=None, help="文档标题（完备性自检时使用）")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)

    content = file_path.read_text(encoding="utf-8")
    sections = enrich_sections_with_snapshot(parse_markdown_sections(content))
    print(f"已解析 {len(sections)} 个章节，开始 AI 处理...\n")

    service = AiService(on_run_complete=on_run_complete)

    if args.step == "all":
        task_service = default_task_service(BACKEND_ROOT)
        result_store = default_result_store(BACKEND_ROOT)
        runner = PipelineTaskRunner(
            AiService(on_run_complete=on_run_complete),
            task_service,
            result_store,
        )
        run_result = runner.run_full(
            sections,
            source_file=str(file_path),
            document_title=args.title,
            source_type=file_path.suffix.lstrip(".") or "unknown",
        )
        task = run_result["task"]
        output_dir = run_result["output_dir"]

        if task.quality_warnings and task.quality_warnings.should_warn_user:
            print(f"\n[警告] 任务 {task.task_no} 质量告警（已写入 quality_warnings）：")
            for item in task.quality_warnings.items:
                print(f"  - [{item.level}] {item.message}")

        print(f"\n任务记录已保存: {BACKEND_ROOT / 'tmp' / 'tasks' / (task.task_no + '.json')}")
        if output_dir:
            print(f"\n结果已写入目录: {output_dir}")
            print("  ├── extract.json          # 抽取的需求点")
            print("  ├── analyze.json          # 发现的问题")
            print("  ├── requirements.json     # 合并后的需求列表")
            print("  ├── parse_quality.json    # 解析质量检查")
            print("  ├── case_quality.json     # 用例质量检查")
            print("  ├── test_cases.json       # 测试用例")
            print("  ├── completeness.json     # 完备性自检（如有）")
            print("  └── manifest.json         # 索引与统计")
        return

    # 单步模式：写入 tmp/steps/{step}/{文件名}/
    step_dir = BACKEND_ROOT / "tmp" / "steps" / args.step / file_path.stem
    step_dir.mkdir(parents=True, exist_ok=True)

    if args.step == "extract":
        _write_json(step_dir / "extract.json", service.extract_requirements(sections))
    elif args.step == "completeness":
        extract = service.extract_requirements(sections)
        _write_json(step_dir / "extract.json", extract)
        _write_json(
            step_dir / "completeness.json",
            service.check_requirement_completeness(
                sections, extract.requirements, document_title=args.title
            ),
        )
    elif args.step == "analyze":
        extract = service.extract_requirements(sections)
        completeness = service.check_requirement_completeness(
            sections, extract.requirements, document_title=args.title
        )
        from app.ai.utils import collect_refill_section_ids, merge_requirements

        requirements = list(extract.requirements)
        refill_ids = collect_refill_section_ids(completeness)
        if refill_ids:
            refill_sections = [s for s in sections if s.section_id in refill_ids]
            if refill_sections:
                refill = service.extract_requirements(refill_sections)
                requirements = merge_requirements(requirements, refill.requirements)
        _write_json(step_dir / "extract.json", extract)
        _write_json(step_dir / "completeness.json", completeness)
        _write_json(step_dir / "requirements.json", requirements)
        _write_json(step_dir / "analyze.json", service.analyze_requirements(sections, requirements))
    else:
        result = service.run_full_pipeline(sections, document_title=args.title)
        _write_json(step_dir / "requirements.json", result["requirements"])
        _write_json(step_dir / "analyze.json", result["analyze"])
        _write_json(step_dir / "test_cases.json", result["cases"])

    print(f"\n结果已写入目录: {step_dir}")


if __name__ == "__main__":
    main()
