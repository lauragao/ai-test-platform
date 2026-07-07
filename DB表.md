# 数据库表设计

> 依据 [设计文档.md](./设计文档.md) 梳理。数据库建议 MySQL 8.0+ / PostgreSQL，字符集 UTF-8。  
> 主键统一使用 `BIGINT` 自增或 `VARCHAR(32)` UUID，下文以 `BIGINT` 为例。

**命名规范：** 所有业务表统一使用 `nb_test_` 前缀，例如 `nb_test_documents`。

## 1. 表清单总览

| 序号 | 表名 | 说明 | MVP |
|------|------|------|-----|
| 1 | `nb_test_documents` | 上传的需求文档基础信息 | ✅ |
| 2 | `nb_test_document_sections` | 解析后的章节/段落结构化内容 | ✅ |
| 3 | `nb_test_tasks` | 异步任务主表（状态机） | ✅ |
| 4 | `nb_test_task_steps` | 任务流水线步骤明细（断点续跑） | ✅ |
| 5 | `nb_test_requirements` | AI 抽取的原子需求点 | ✅ |
| 6 | `nb_test_requirement_issues` | 需求问题（不清晰/遗漏/矛盾/风险） | ✅ |
| 7 | `nb_test_issue_source_refs` | 问题与原文位置的引用关系 | 阶段二 |
| 8 | `nb_test_test_cases` | 测试用例 | ✅ |
| 9 | `nb_test_test_case_requirements` | 测试用例与需求点多对多关联 | 阶段二 |
| 10 | `nb_test_exports` | 导出文件记录 | ✅ |
| 11 | `nb_test_feedbacks` | 用户对 AI 结果的反馈 | 阶段三 |
| 12 | `nb_test_ai_runs` | AI 调用日志（含 token/费用） | ✅ |
| 13 | `nb_test_prompt_templates` | Prompt 模板版本管理 | 阶段三 |
| 14 | `nb_test_users` | 用户（团队化阶段） | 暂缓 |

---

## 2. ER 关系概览

```
nb_test_documents 1 ── N nb_test_document_sections
nb_test_documents 1 ── N nb_test_tasks
nb_test_tasks     1 ── N nb_test_task_steps
nb_test_tasks     1 ── N nb_test_ai_runs
nb_test_documents 1 ── N nb_test_requirements
nb_test_document_sections 1 ── N nb_test_requirements
nb_test_requirements 1 ── N nb_test_requirement_issues
nb_test_requirement_issues 1 ── N nb_test_issue_source_refs
nb_test_document_sections 1 ── N nb_test_issue_source_refs
nb_test_tasks     1 ── N nb_test_test_cases
nb_test_requirements N ── N nb_test_test_cases  (via nb_test_test_case_requirements)
nb_test_tasks     1 ── N nb_test_exports
nb_test_requirement_issues / nb_test_test_cases / nb_test_ai_runs 1 ── N nb_test_feedbacks
```

---

## 3. 表结构明细

### 3.1 nb_test_documents — 文档表

存储上传文件的元信息与解析摘要。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| title | VARCHAR(255) | Y | 文档标题（可从文件名或内容提取） |
| file_name | VARCHAR(255) | Y | 原始文件名 |
| file_path | VARCHAR(512) | Y | 存储路径（本地或对象存储 key） |
| file_size | BIGINT | Y | 文件大小（字节） |
| file_hash | VARCHAR(64) | N | 文件 MD5/SHA256，用于去重 |
| source_type | VARCHAR(32) | Y | 来源格式：`word` / `pdf` / `html` / `markdown` / `txt` / `image` |
| mime_type | VARCHAR(128) | N | MIME 类型 |
| page_count | INT | N | 页数（PDF/Word 等） |
| parse_status | VARCHAR(32) | Y | 解析状态：`pending` / `parsing` / `success` / `failed` |
| parse_version | VARCHAR(32) | N | 解析器版本 |
| parse_confidence | DECIMAL(5,2) | N | 整体解析置信度（OCR 场景） |
| parse_error | TEXT | N | 解析失败原因 |
| summary | TEXT | N | AI 生成的需求摘要 |
| metadata | JSON | N | 扩展元数据（作者、版本号等） |
| created_at | DATETIME | Y | 创建时间 |
| updated_at | DATETIME | Y | 更新时间 |
| deleted_at | DATETIME | N | 软删除 |

**索引：**
- `idx_nb_test_documents_source_type`
- `idx_nb_test_documents_parse_status`
- `idx_nb_test_documents_created_at`
- `idx_nb_test_documents_file_hash`

---

### 3.2 nb_test_document_sections — 文档章节表

结构化中间层，支撑原文定位与高亮。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| document_id | BIGINT | FK | 关联 `nb_test_documents.id` |
| parent_id | BIGINT | N | 父章节 ID，构建标题层级 |
| section_key | VARCHAR(64) | N | 业务侧章节标识，如 `sec_001` |
| title | VARCHAR(512) | N | 章节标题 |
| level | TINYINT | Y | 标题层级，1=一级标题 |
| content | LONGTEXT | Y | 章节正文 |
| sort_order | INT | Y | 同级排序 |
| page_start | INT | N | 起始页码 |
| page_end | INT | N | 结束页码 |
| start_offset | INT | N | 全文字符起始偏移 |
| end_offset | INT | N | 全文字符结束偏移 |
| tables | JSON | N | 表格结构化数据 |
| images | JSON | N | 图片信息（路径、OCR 文本、置信度） |
| source_snapshot | JSON | N | 原文快照：字符长度、空白比、表格/特殊字符密度等 |
| parse_confidence | DECIMAL(5,2) | N | 本段解析置信度（0~1，由 source_snapshot 启发式计算） |
| parse_warnings | JSON | N | 解析异常，如表格解析失败 |
| created_at | DATETIME | Y | 创建时间 |
| updated_at | DATETIME | Y | 更新时间 |

**索引：**
- `idx_nb_test_sections_document_id`
- `idx_nb_test_sections_parent_id`
- `idx_nb_test_sections_document_sort`（document_id + sort_order）

**`source_snapshot` JSON 示例：**

```json
{
  "raw_char_length": 120,
  "whitespace_count": 10,
  "whitespace_ratio": 0.0833,
  "table_marker_count": 0,
  "table_marker_density": 0.0,
  "special_char_count": 2,
  "special_char_density": 1.67,
  "alphanumeric_count": 45,
  "alphanumeric_ratio": 0.375,
  "cjk_count": 58,
  "line_count": 3
}
```

---

### 3.3 nb_test_tasks — 任务表

一次「上传 → 解析 → 分析 → 生成 → 导出」的完整异步任务。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| document_id | BIGINT | FK | 关联 `nb_test_documents.id` |
| task_no | VARCHAR(64) | Y | 任务编号，对外展示 |
| task_type | VARCHAR(32) | Y | 任务类型：`full`（全流程）/ `analyze_only` / `generate_cases_only` |
| status | VARCHAR(32) | Y | 状态机，见下方枚举 |
| progress | TINYINT | Y | 进度 0-100 |
| current_step | VARCHAR(64) | N | 当前步骤名称 |
| step_message | VARCHAR(512) | N | 当前步骤说明 |
| error_code | VARCHAR(64) | N | 错误码 |
| error_message | TEXT | N | 错误详情 |
| retry_count | INT | Y | 已重试次数，默认 0 |
| max_retry | INT | Y | 最大重试次数，默认 3 |
| timeout_seconds | INT | Y | 任务级默认步骤超时（秒），默认 180 |
| config | JSON | N | 任务配置（分析类型、导出格式、模型选择、各步骤 timeout 覆盖等） |
| quality_warnings | JSON | N | 质量告警（解析置信度、inferred 占比、引用错乱、用例覆盖率等，见下方示例） |
| started_at | DATETIME | N | 开始执行时间 |
| finished_at | DATETIME | N | 结束时间 |
| created_at | DATETIME | Y | 创建时间 |
| updated_at | DATETIME | Y | 更新时间 |

**status 枚举：**
`created` → `uploaded` → `parsing` → `parsed` → `analyzing` → `analysis_completed` → `generating_cases` → `case_completed` → `exporting` → `completed`  
异常态：`failed` / `cancelled`

**`failed` 常见 `error_code`：** `step_timeout` / `ai_call_timeout` / `max_retries_exceeded` / `pipeline_failed`

**索引：**
- `idx_nb_test_tasks_document_id`
- `idx_nb_test_tasks_status`
- `idx_nb_test_tasks_task_no`（UNIQUE）
- `idx_nb_test_tasks_created_at`

**`quality_warnings` JSON 示例：**

```json
{
  "items": [
    {
      "warning_type": "parse_quality",
      "level": "warning",
      "message": "文档解析置信度低于阈值，可能影响分析质量，建议检查 PDF 是否为扫描件或版式是否复杂。",
      "metrics": {
        "document_parse_confidence": 0.52,
        "inferred_issue_ratio": 0.48,
        "broken_citation_ratio": 0.25
      }
    },
    {
      "warning_type": "case_coverage",
      "level": "warning",
      "message": "需求覆盖率 88.0% 低于目标 95.0%",
      "metrics": {
        "coverage_rate": 88.0,
        "orphan_case_count": 2
      }
    }
  ],
  "alert_level": "warning",
  "should_warn_user": true,
  "updated_at": "2026-07-06T18:00:00"
}
```

---

### 3.4 nb_test_task_steps — 任务步骤表

记录流水线各步骤，支持断点续跑与调试。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| task_id | BIGINT | FK | 关联 `nb_test_tasks.id` |
| step_name | VARCHAR(64) | Y | 步骤名：`parse` / `clean` / `chunk` / `extract_requirements` / `check_issues` / `generate_cases` / `validate` / `export` |
| step_order | INT | Y | 步骤顺序 |
| status | VARCHAR(32) | Y | `pending` / `running` / `success` / `failed` / `skipped` / `timeout` |
| input_snapshot | JSON | N | 输入摘要（非全文，便于排查） |
| output_snapshot | JSON | N | 输出摘要或结果 ID 列表 |
| error_code | VARCHAR(64) | N | 如 `step_timeout` / `ai_call_timeout` / `validation_failed` |
| error_message | TEXT | N | 失败原因 |
| retry_count | INT | Y | 本步骤已重试次数，默认 0 |
| max_retry | INT | Y | 本步骤最大重试次数，默认 3 |
| timeout_seconds | INT | Y | 本步骤超时（秒），超时后标记 failed 并触发重试或任务 failed |
| started_at | DATETIME | N | 开始时间 |
| finished_at | DATETIME | N | 结束时间 |
| duration_ms | INT | N | 耗时（毫秒） |
| created_at | DATETIME | Y | 创建时间 |
| updated_at | DATETIME | Y | 更新时间 |

**索引：**
- `idx_nb_test_task_steps_task_id`
- `idx_nb_test_task_steps_task_order`（task_id + step_order）

---

### 3.5 nb_test_requirements — 原子需求表

AI 从文档中拆分出的最小可测试需求单元。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| document_id | BIGINT | FK | 关联 `nb_test_documents.id` |
| task_id | BIGINT | FK | 关联 `nb_test_tasks.id` |
| section_id | BIGINT | N | 主要来源章节 `nb_test_document_sections.id` |
| req_key | VARCHAR(64) | N | 业务标识，如 `req_001` |
| module | VARCHAR(128) | N | 所属模块，如「登录」 |
| title | VARCHAR(512) | Y | 需求标题 |
| description | TEXT | Y | 需求描述 |
| req_type | VARCHAR(32) | N | 类型：`functional` / `rule` / `flow` / `data` / `permission` |
| priority | VARCHAR(16) | N | 优先级：P0 / P1 / P2 |
| acceptance_criteria | TEXT | N | 验收标准 |
| source_quote | TEXT | N | 原文引用片段 |
| page_no | INT | N | 来源页码 |
| status | VARCHAR(32) | Y | `draft` / `confirmed` / `rejected` |
| metadata | JSON | N | 角色、状态流、数据对象等扩展信息 |
| created_at | DATETIME | Y | 创建时间 |
| updated_at | DATETIME | Y | 更新时间 |

**索引：**
- `idx_nb_test_requirements_document_id`
- `idx_nb_test_requirements_task_id`
- `idx_nb_test_requirements_section_id`
- `idx_nb_test_requirements_module`

---

### 3.6 nb_test_requirement_issues — 需求问题表

AI 发现的不清晰、遗漏、矛盾、风险等问题。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| document_id | BIGINT | FK | 关联 `nb_test_documents.id` |
| task_id | BIGINT | FK | 关联 `nb_test_tasks.id` |
| requirement_id | BIGINT | N | 关联 `nb_test_requirements.id`（可空，文档级问题） |
| issue_key | VARCHAR(64) | N | 业务标识，如 `issue_001` |
| issue_type | VARCHAR(32) | Y | `unclear` / `missing` / `conflict` / `risk` |
| severity | VARCHAR(16) | Y | `high` / `medium` / `low` |
| title | VARCHAR(512) | Y | 问题标题 |
| description | TEXT | Y | 问题描述 |
| suggestion | TEXT | N | 修改建议 |
| evidence_type | VARCHAR(32) | Y | 依据类型：`explicit`（原文明确）/ `inferred`（推测） |
| status | VARCHAR(32) | Y | `pending` / `accepted` / `modified` / `rejected` / `false_positive` |
| user_note | TEXT | N | 用户备注 |
| modified_content | TEXT | N | 用户修改后的内容 |
| reject_reason | VARCHAR(255) | N | 拒绝/误报原因 |
| reviewed_at | DATETIME | N | 用户审阅时间 |
| created_at | DATETIME | Y | 创建时间 |
| updated_at | DATETIME | Y | 更新时间 |

**索引：**
- `idx_nb_test_issues_document_id`
- `idx_nb_test_issues_task_id`
- `idx_nb_test_issues_requirement_id`
- `idx_nb_test_issues_type_severity`（issue_type + severity）
- `idx_nb_test_issues_status`

---

### 3.7 nb_test_issue_source_refs — 问题原文引用表

支撑「点击问题 → 高亮原文」的定位能力。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| issue_id | BIGINT | FK | 关联 `nb_test_requirement_issues.id` |
| section_id | BIGINT | FK | 关联 `nb_test_document_sections.id` |
| quote | TEXT | Y | 引用的原文片段 |
| page_no | INT | N | 页码 |
| start_offset | INT | N | 段内起始偏移 |
| end_offset | INT | N | 段内结束偏移 |
| created_at | DATETIME | Y | 创建时间 |

**索引：**
- `idx_nb_test_source_refs_issue_id`
- `idx_nb_test_source_refs_section_id`

---

### 3.8 nb_test_test_cases — 测试用例表

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| document_id | BIGINT | FK | 关联 `nb_test_documents.id` |
| task_id | BIGINT | FK | 关联 `nb_test_tasks.id` |
| case_key | VARCHAR(64) | N | 用例编号，如 `TC_001` |
| module | VARCHAR(128) | N | 所属模块 |
| title | VARCHAR(512) | Y | 用例标题 |
| priority | VARCHAR(16) | Y | P0 / P1 / P2 |
| case_type | VARCHAR(32) | Y | `functional` / `uat` / `exception` / `boundary` / `permission` / `data` / `flow` |
| precondition | TEXT | N | 前置条件 |
| steps | JSON | Y | 测试步骤数组 |
| expected_result | TEXT | Y | 预期结果 |
| risk_notes | JSON | N | 风险说明 |
| status | VARCHAR(32) | Y | `draft` / `accepted` / `modified` / `rejected` |
| user_note | TEXT | N | 用户备注 |
| modified_content | JSON | N | 用户修改后的步骤/预期等 |
| reviewed_at | DATETIME | N | 用户审阅时间 |
| created_at | DATETIME | Y | 创建时间 |
| updated_at | DATETIME | Y | 更新时间 |

**索引：**
- `idx_nb_test_test_cases_document_id`
- `idx_nb_test_test_cases_task_id`
- `idx_nb_test_test_cases_module`
- `idx_nb_test_test_cases_case_type`
- `idx_nb_test_test_cases_status`

---

### 3.9 nb_test_test_case_requirements — 用例需求关联表

一个用例可覆盖多个需求点，一个需求点可对应多条用例。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| test_case_id | BIGINT | FK | 关联 `nb_test_test_cases.id` |
| requirement_id | BIGINT | FK | 关联 `nb_test_requirements.id` |
| created_at | DATETIME | Y | 创建时间 |

**约束：**
- UNIQUE（test_case_id, requirement_id）

**索引：**
- `idx_nb_test_tcr_requirement_id`

---

### 3.10 nb_test_exports — 导出记录表

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| task_id | BIGINT | FK | 关联 `nb_test_tasks.id` |
| document_id | BIGINT | FK | 关联 `nb_test_documents.id` |
| export_type | VARCHAR(32) | Y | `excel` / `markdown` / `xmind` / `json` |
| file_name | VARCHAR(255) | Y | 导出文件名 |
| file_path | VARCHAR(512) | Y | 存储路径 |
| file_size | BIGINT | N | 文件大小 |
| export_scope | VARCHAR(32) | Y | 导出范围：`issues` / `test_cases` / `full_report` |
| status | VARCHAR(32) | Y | `pending` / `success` / `failed` |
| error_message | TEXT | N | 失败原因 |
| created_at | DATETIME | Y | 创建时间 |

**索引：**
- `idx_nb_test_exports_task_id`
- `idx_nb_test_exports_document_id`

---

### 3.11 nb_test_feedbacks — 用户反馈表

沉淀采纳/修改/拒绝等操作，用于优化 prompt 和评估集。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| task_id | BIGINT | FK | 关联 `nb_test_tasks.id` |
| target_type | VARCHAR(32) | Y | 目标类型：`issue` / `test_case` / `requirement` / `ai_run` |
| target_id | BIGINT | Y | 目标记录 ID |
| feedback_type | VARCHAR(32) | Y | `accept` / `modify` / `reject` / `false_positive` / `add_new` |
| original_content | JSON | N | 修改前内容快照 |
| new_content | JSON | N | 修改后内容 |
| reason | VARCHAR(512) | N | 拒绝或修改原因 |
| ai_run_id | BIGINT | N | 关联 `nb_test_ai_runs.id` |
| created_at | DATETIME | Y | 创建时间 |

**索引：**
- `idx_nb_test_feedbacks_task_id`
- `idx_nb_test_feedbacks_target`（target_type + target_id）
- `idx_nb_test_feedbacks_feedback_type`

---

### 3.12 nb_test_ai_runs — AI 调用记录表

记录每次 AI 调用的输入输出、成本与质量追踪。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| task_id | BIGINT | FK | 关联 `nb_test_tasks.id` |
| task_step_id | BIGINT | N | 关联 `nb_test_task_steps.id` |
| run_type | VARCHAR(64) | Y | 调用类型：`summarize` / `extract_requirements` / `check_clarity` / `check_completeness` / `check_conflict` / `generate_cases` / `validate_output` |
| model_name | VARCHAR(128) | Y | 模型名称 |
| model_version | VARCHAR(64) | N | 模型版本 |
| prompt_template_id | BIGINT | N | 关联 `nb_test_prompt_templates.id` |
| prompt_version | VARCHAR(32) | N | Prompt 版本号 |
| input_tokens | INT | N | 输入 token 数 |
| output_tokens | INT | N | 输出 token 数 |
| total_tokens | INT | N | 总 token 数 |
| cost_amount | DECIMAL(10,4) | N | 费用 |
| duration_ms | INT | N | 耗时（毫秒） |
| status | VARCHAR(32) | Y | `success` / `failed` / `retry` |
| input_summary | TEXT | N | 输入摘要（非全文） |
| output_raw | LONGTEXT | N | 原始输出 |
| output_parsed | JSON | N | 解析后的结构化结果 |
| validation_result | JSON | N | Schema 校验结果 |
| error_message | TEXT | N | 失败原因 |
| created_at | DATETIME | Y | 创建时间 |

**索引：**
- `idx_nb_test_ai_runs_task_id`
- `idx_nb_test_ai_runs_run_type`
- `idx_nb_test_ai_runs_created_at`

---

### 3.13 nb_test_prompt_templates — Prompt 模板表（阶段三）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| template_key | VARCHAR(64) | Y | 模板标识，如 `check_clarity` |
| name | VARCHAR(128) | Y | 模板名称 |
| version | VARCHAR(32) | Y | 版本号 |
| content | LONGTEXT | Y | Prompt 正文 |
| variables | JSON | N | 变量定义 |
| is_active | TINYINT | Y | 是否启用，默认 0 |
| description | TEXT | N | 说明 |
| created_at | DATETIME | Y | 创建时间 |
| updated_at | DATETIME | Y | 更新时间 |

**索引：**
- `idx_nb_test_prompt_key_version`（template_key + version，UNIQUE）
- `idx_nb_test_prompt_active`（template_key + is_active）

---

### 3.14 nb_test_users — 用户表（暂缓，团队化阶段）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | BIGINT | PK | 主键 |
| username | VARCHAR(64) | Y | 用户名 |
| email | VARCHAR(128) | N | 邮箱 |
| password_hash | VARCHAR(255) | N | 密码哈希 |
| role | VARCHAR(32) | Y | `admin` / `tester` / `pm` / `viewer` |
| status | VARCHAR(16) | Y | `active` / `disabled` |
| created_at | DATETIME | Y | 创建时间 |
| updated_at | DATETIME | Y | 更新时间 |

> 引入用户后，需在 `nb_test_documents`、`nb_test_tasks`、`nb_test_feedbacks` 等表增加 `user_id` / `created_by` 字段。

---

## 4. MVP 最小建表建议

阶段一只需创建以下 **8 张表** 即可跑通闭环：

1. `nb_test_documents`
2. `nb_test_document_sections`
3. `nb_test_tasks`
4. `nb_test_task_steps`
5. `nb_test_requirements`
6. `nb_test_requirement_issues`
7. `nb_test_test_cases`
8. `nb_test_ai_runs`

阶段二补充：
- `nb_test_issue_source_refs`
- `nb_test_test_case_requirements`
- `nb_test_exports`

阶段三补充：
- `nb_test_feedbacks`
- `nb_test_prompt_templates`

---

## 5. 建表 SQL 示例（MySQL）

```sql
-- 文档表
CREATE TABLE nb_test_documents (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  title           VARCHAR(255) NOT NULL,
  file_name       VARCHAR(255) NOT NULL,
  file_path       VARCHAR(512) NOT NULL,
  file_size       BIGINT NOT NULL,
  file_hash       VARCHAR(64),
  source_type     VARCHAR(32) NOT NULL,
  mime_type       VARCHAR(128),
  page_count      INT,
  parse_status    VARCHAR(32) NOT NULL DEFAULT 'pending',
  parse_version   VARCHAR(32),
  parse_confidence DECIMAL(5,2),
  parse_error     TEXT,
  summary         TEXT,
  metadata        JSON,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at      DATETIME,
  INDEX idx_nb_test_documents_source_type (source_type),
  INDEX idx_nb_test_documents_parse_status (parse_status),
  INDEX idx_nb_test_documents_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 任务表
CREATE TABLE nb_test_tasks (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  document_id     BIGINT NOT NULL,
  task_no         VARCHAR(64) NOT NULL,
  task_type       VARCHAR(32) NOT NULL DEFAULT 'full',
  status          VARCHAR(32) NOT NULL DEFAULT 'created',
  progress        TINYINT NOT NULL DEFAULT 0,
  current_step    VARCHAR(64),
  step_message    VARCHAR(512),
  error_code      VARCHAR(64),
  error_message   TEXT,
  retry_count     INT NOT NULL DEFAULT 0,
  max_retry       INT NOT NULL DEFAULT 3,
  timeout_seconds INT NOT NULL DEFAULT 180,
  config          JSON,
  quality_warnings JSON,
  started_at      DATETIME,
  finished_at     DATETIME,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_nb_test_tasks_task_no (task_no),
  INDEX idx_nb_test_tasks_document_id (document_id),
  INDEX idx_nb_test_tasks_status (status),
  CONSTRAINT fk_nb_test_tasks_document FOREIGN KEY (document_id) REFERENCES nb_test_documents(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 其余表按上文字段定义类推创建，表名均加 nb_test_ 前缀
```

---

## 6. 设计说明

1. **JSON 字段使用场景**：`steps`、`tables`、`images`、`metadata`、`config` 等半结构化数据适合 JSON，便于 AI 输出直接入库。
2. **状态字段统一 VARCHAR**：便于扩展枚举值，应用层维护状态机转换规则。
3. **软删除仅 nb_test_documents**：任务与分析结果建议保留历史，便于追溯和评估。
4. **nb_test_issue_source_refs 独立成表**：比 JSON 数组更利于按章节反查关联问题，支撑双向定位。
5. **nb_test_test_case_requirements 独立成表**：支撑覆盖率统计（哪些需求未被用例覆盖）。
6. **nb_test_task_steps + nb_test_ai_runs 分离**：步骤管流程编排，AI 运行管模型调用细节与成本，职责清晰。
