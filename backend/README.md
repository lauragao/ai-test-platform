# Backend

AI 需求分析与测试用例生成平台后端（MVP）。

## 目录结构

```
backend/
├── app/
│   ├── config.py
│   ├── ai/
│   │   ├── ai_service.py          # AiService 统一封装
│   │   ├── llm_client.py            # OpenAI 兼容 LLM 客户端
│   │   ├── models.py                # Pydantic 数据模型
│   │   ├── utils.py                 # 工具函数
│   │   ├── prompts/                 # Prompt 模板目录
│   │   │   ├── requirement_extract.py
│   │   │   ├── requirement_completeness_check.py
│   │   │   ├── requirement_analysis.py
│   │   │   └── case_generation.py
│   │   └── schemas/                 # JSON Schema 校验
│   │       ├── issues_schema.py
│   │       ├── completeness_schema.py
│   │       └── cases_schema.py
│   ├── tasks/                       # 任务状态与 quality_warnings 持久化
│   │   ├── task_service.py
│   │   ├── pipeline_runner.py
│   │   └── quality_warnings.py
│   ├── document/                    # 原文快照与解析置信度
│   │   ├── section_snapshot.py
│   │   └── enrich.py
│   ├── exporters/                   # Excel / XMind 导出
│   ├── memory/                      # 文件型记忆服务，后续可替换为 DB
│   ├── quality/                     # 解析质量告警、用例覆盖率质检
│   │   ├── parse_quality_service.py
│   │   └── quality_check_service.py
│   └── requirement_sources/         # 需求目录读取、需求 ID 辅助
├── examples/
│   ├── run_ai_pipeline.py
│   └── run_export_demo.py
├── requirements.txt
└── .env.example
```

## 快速开始

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 AI_API_KEY 和 AI_BASE_URL
```

## AiService 核心 API

```python
from app.ai import AiService, DocumentSectionInput
from app.document.enrich import enrich_sections_with_snapshot
from app.quality import ParseQualityService

service = AiService()

sections = enrich_sections_with_snapshot([
    DocumentSectionInput(
        section_id="sec_001",
        title="登录功能",
        level=1,
        content="用户通过手机号和验证码登录...",
    )
])
# sections[0].source_snapshot  - 原文快照（字符长度、空白比、特殊字符密度等）
# sections[0].parse_confidence - 单段解析置信度 0~1

extract = service.extract_requirements(sections)

completeness = service.check_requirement_completeness(
    sections,
    extract.requirements,
    document_title="登录模块 PRD",
)

# 定向补抽 partial/missing 章节（run_full_pipeline 已内置此逻辑）
from app.ai.utils import collect_refill_section_ids, merge_requirements

requirements = list(extract.requirements)
refill_ids = collect_refill_section_ids(completeness)
if refill_ids:
    refill_sections = [s for s in sections if s.section_id in refill_ids]
    refill = service.extract_requirements(refill_sections)
    requirements = merge_requirements(requirements, refill.requirements)

analyze = service.analyze_requirements(sections, requirements)

# 解析质量兜底：低置信 / 大量 inferred / 引用错乱时主动告警
parse_quality = ParseQualityService().check_after_analysis(
    sections,
    analyze.issues,
    source_type="pdf",
)
if parse_quality.should_warn_user:
    for alert in parse_quality.alerts:
        print(alert)

cases = service.generate_test_cases(requirements, analyze.issues)

# 或一键跑全流程（含完备性自检 + 定向补抽 + 解析质量告警）
result = service.run_full_pipeline(sections, document_title="登录模块 PRD", source_type="pdf")
# result["completeness"]   - 最后一次完备性自检结果
# result["requirements"]   - 补抽合并后的最终需求列表
# result["parse_quality"]  - 解析质量报告（含 alerts / should_warn_user）
```

## 任务 quality_warnings

```python
from app.tasks import PipelineTaskRunner, default_task_service
from app.ai import AiService

runner = PipelineTaskRunner(AiService(), default_task_service())
run_result = runner.run_full(sections, source_file="prd.pdf", source_type="pdf")

task = run_result["task"]
# task.quality_warnings.items      - 告警列表（parse_quality / case_coverage 等）
# task.quality_warnings.should_warn_user - 是否需在任务详情页展示告警条

# MVP 任务 JSON 保存在 backend/tmp/tasks/{task_no}.json
```

```bash
python examples/run_ai_pipeline.py --file ../requirements/requirement.md --step all
# 输出含 task_no、quality_warnings，并写入 tmp/tasks/
```

## REST API

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问 OpenAPI 文档：`http://localhost:8000/docs`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/tasks` | 任务列表（含 `should_warn_user`） |
| GET | `/api/tasks/{task_no}` | 任务详情（含 `quality_warnings`） |
| GET | `/api/tasks/{task_no}/quality-warnings` | 质量告警 |
| GET | `/api/tasks/{task_no}/steps` | 步骤明细（timeout / retry / duration_ms） |
| GET | `/api/tasks/{task_no}/report` | 分析报告（需求/问题/用例） |
| POST | `/api/tasks/run` | 上传 `.md`/`.txt` 并异步执行流水线（202） |
| POST | `/api/tasks/timeout-scan` | 扫描 running 步骤超时（cron/运维） |

提交任务示例：

```bash
curl -X POST "http://localhost:8000/api/tasks/run" \
  -F "file=@../requirements/requirement.md" \
  -F "title=登录模块 PRD"
```

轮询任务状态：

```bash
curl "http://localhost:8000/api/tasks/task_20260706182600_6de72ba6"
curl "http://localhost:8000/api/tasks/task_20260706182600_6de72ba6/quality-warnings"
curl "http://localhost:8000/api/tasks/task_20260706182600_6de72ba6/report"
```

## 导出 Excel / XMind

```python
from app.exporters import ExcelExporter, XmindExporter

XmindExporter().export(cases, "tmp/test_cases.xmind")
ExcelExporter().export(
    cases,
    "tmp/test_cases.xlsx",
    requirements=requirements,
    include_traceability=True,
)
```

导出前可做质量检查：

```python
from app.quality import QualityCheckService

quality = QualityCheckService().check(requirements, cases)
```

## 规则与记忆

旧工具中的测试设计方法、优先级、追溯矩阵、解析规则、业务规则已迁移到：

```python
from app.ai.rules import get_case_generation_rules
```

`AiService.generate_test_cases()` 会自动注入这些规则。

旧 `.memory` 思路已迁移为：

```python
from app.memory import MemoryService

memory = MemoryService(".")
memory.init()
memory.add_generation_record({"type": "test_case", "case_count": 10})
```

旧 `requirements/` 文件夹读取能力已迁移为：

```python
from app.requirement_sources import RequirementReader

text, assets = RequirementReader().read_directory("requirements")
```

## 命令行示例

```bash
python examples/run_ai_pipeline.py \
  --file ../requirements/requirement.md
```

不调用 AI，仅验证导出链路：

```bash
python examples/run_export_demo.py
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_API_KEY` | API 密钥 | 必填 |
| `AI_BASE_URL` | 兼容接口地址 | `https://api.openai.com/v1` |
| `AI_MODEL` | 模型名称 | `gpt-4o-mini` |
| `AI_TEMPERATURE` | 温度 | `0.2` |
| `AI_MAX_RETRIES` | 校验失败重试次数 | `3` |
| `AI_TIMEOUT_SECONDS` | 超时秒数 | `120` |
