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
│   │   │   ├── requirement_analysis.py
│   │   │   └── case_generation.py
│   │   └── schemas/                 # JSON Schema 校验
│   │       ├── issues_schema.py
│   │       └── cases_schema.py
│   ├── exporters/                   # Excel / XMind 导出
│   ├── memory/                      # 文件型记忆服务，后续可替换为 DB
│   ├── quality/                     # 覆盖率、优先级、孤儿用例质检
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

service = AiService()

sections = [
    DocumentSectionInput(
        section_id="sec_001",
        title="登录功能",
        level=1,
        content="用户通过手机号和验证码登录...",
    )
]

extract = service.extract_requirements(sections)
analyze = service.analyze_requirements(sections, extract.requirements)
cases = service.generate_test_cases(extract.requirements, analyze.issues)

# 或一键跑全流程
result = service.run_full_pipeline(sections)
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
