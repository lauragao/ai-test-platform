export interface TaskSummary {
  task_no: string
  task_type: string
  status: string
  progress: number
  current_step?: string | null
  step_message?: string | null
  source_file?: string | null
  should_warn_user: boolean
  alert_level: string
  created_at: string
  updated_at: string
  finished_at?: string | null
}

export interface QualityWarningItem {
  warning_type: string
  level: string
  message: string
  metrics?: Record<string, unknown>
}

export interface TaskQualityWarnings {
  items: QualityWarningItem[]
  alert_level: string
  should_warn_user: boolean
  updated_at: string
}

export interface TaskDetail extends TaskSummary {
  id?: number | null
  document_id?: number | null
  error_code?: string | null
  error_message?: string | null
  retry_count: number
  max_retry: number
  timeout_seconds: number
  config: Record<string, unknown>
  quality_warnings?: TaskQualityWarnings | null
  started_at?: string | null
  has_report: boolean
}

export interface TaskStep {
  id: number
  task_no: string
  step_name: string
  step_order: number
  status: string
  error_code?: string | null
  error_message?: string | null
  retry_count: number
  max_retry: number
  timeout_seconds: number
  duration_ms?: number | null
  started_at?: string | null
  finished_at?: string | null
}

export interface SourceRef {
  section_id: string
  quote: string
  page_no?: number | null
}

export interface RequirementIssue {
  issue_key: string
  requirement_id?: string | null
  issue_type: string
  severity: string
  title: string
  description: string
  suggestion?: string | null
  evidence_type?: string
  source_refs?: SourceRef[]
}

export interface RequirementItem {
  req_key: string
  section_id?: string | null
  module?: string | null
  title: string
  description: string
  priority?: string | null
}

export interface TestCaseItem {
  case_key: string
  module?: string | null
  title: string
  priority: string
  case_type?: string
  precondition?: string | null
  steps: string[]
  expected_result: string
  source_requirement_ids?: string[]
}

export interface TaskReport {
  task_no: string
  task_status: string
  quality_warnings?: TaskQualityWarnings | null
  extract: { summary: string; requirements?: RequirementItem[] }
  completeness?: Record<string, unknown> | null
  requirements: RequirementItem[]
  analyze: { summary: string; issues: RequirementIssue[] }
  parse_quality: Record<string, unknown>
  case_quality: Record<string, unknown>
  cases: { summary: string; test_cases: TestCaseItem[] }
}

export interface DocumentSection {
  section_id: string
  title?: string | null
  level: number
  content: string
  parse_confidence?: number | null
}

export interface TaskDocument {
  task_no: string
  source_file?: string | null
  section_count: number
  document_parse_confidence?: number | null
  sections: DocumentSection[]
}

export interface ExportResult {
  task_no: string
  format: string
  filename: string
  download_url: string
  file_size: number
}
