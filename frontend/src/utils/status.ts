import type { TagProps } from 'antd'

export const TERMINAL_STATUSES = new Set([
  'case_completed',
  'completed',
  'failed',
  'cancelled',
])

export const STEP_LABELS: Record<string, string> = {
  extract_requirements: '需求抽取',
  check_requirement_completeness: '完备性自检',
  analyze_requirements: '问题分析',
  generate_cases: '用例生成',
  validate: '质量校验',
  upload: '文件上传',
}

export const STATUS_LABELS: Record<string, string> = {
  created: '已创建',
  uploaded: '已上传',
  parsing: '解析中',
  parsed: '已解析',
  analyzing: '分析中',
  analysis_completed: '分析完成',
  generating_cases: '生成用例中',
  case_completed: '已完成',
  completed: '全部完成',
  exporting: '导出中',
  failed: '失败',
  cancelled: '已取消',
}

export function statusColor(status: string): TagProps['color'] {
  if (status === 'failed') return 'error'
  if (status === 'cancelled') return 'default'
  if (status === 'case_completed' || status === 'completed') return 'success'
  if (status.includes('ing') || status === 'analyzing' || status === 'uploaded') return 'processing'
  return 'blue'
}

export function severityColor(severity: string): TagProps['color'] {
  const map: Record<string, TagProps['color']> = {
    high: 'red',
    medium: 'orange',
    low: 'gold',
  }
  return map[severity.toLowerCase()] ?? 'default'
}

export function isRunning(status: string): boolean {
  return !TERMINAL_STATUSES.has(status)
}
