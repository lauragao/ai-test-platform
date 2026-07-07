import client from './client'
import type {
  ExportResult,
  TaskDetail,
  TaskDocument,
  TaskReport,
  TaskStep,
  TaskSummary,
} from './types'

export async function listTasks(limit = 20): Promise<TaskSummary[]> {
  const { data } = await client.get<{ items: TaskSummary[] }>('/tasks', {
    params: { limit },
  })
  return data.items
}

export async function getTask(taskNo: string): Promise<TaskDetail> {
  const { data } = await client.get<TaskDetail>(`/tasks/${taskNo}`)
  return data
}

export async function getTaskSteps(taskNo: string): Promise<TaskStep[]> {
  const { data } = await client.get<{ items: TaskStep[] }>(`/tasks/${taskNo}/steps`)
  return data.items
}

export async function getTaskReport(taskNo: string): Promise<TaskReport> {
  const { data } = await client.get<TaskReport>(`/tasks/${taskNo}/report`)
  return data
}

export async function getTaskDocument(taskNo: string): Promise<TaskDocument> {
  const { data } = await client.get<TaskDocument>(`/tasks/${taskNo}/document`)
  return data
}

export async function createTask(file: File, title?: string): Promise<string> {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  const { data } = await client.post<{ task_no: string }>('/tasks/run', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data.task_no
}

export async function retryTask(taskNo: string): Promise<void> {
  await client.post(`/tasks/${taskNo}/retry`)
}

export async function exportTask(
  taskNo: string,
  format: 'xlsx' | 'xmind',
): Promise<ExportResult> {
  const { data } = await client.post<ExportResult>(`/tasks/${taskNo}/export`, null, {
    params: { format },
  })
  return data
}

export function getDownloadUrl(path: string): string {
  if (path.startsWith('http')) return path
  return path.startsWith('/') ? path : `/${path}`
}
