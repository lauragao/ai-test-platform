import { Steps, Typography } from 'antd'
import type { TaskStep } from '../api/types'
import { STEP_LABELS } from '../utils/status'

interface TaskProgressProps {
  steps: TaskStep[]
  progress: number
  stepMessage?: string | null
}

function stepStatus(status: string): 'wait' | 'process' | 'finish' | 'error' {
  if (status === 'success') return 'finish'
  if (status === 'running') return 'process'
  if (status === 'failed' || status === 'timeout') return 'error'
  return 'wait'
}

export default function TaskProgress({ steps, progress, stepMessage }: TaskProgressProps) {
  const ordered = [...steps].sort((a, b) => a.step_order - b.step_order)

  return (
    <div>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        进度 {progress}% {stepMessage ? `· ${stepMessage}` : ''}
      </Typography.Paragraph>
      <Steps
        size="small"
        items={ordered.map((step) => ({
          title: STEP_LABELS[step.step_name] ?? step.step_name,
          status: stepStatus(step.status),
          description:
            step.duration_ms != null
              ? `${Math.round(step.duration_ms / 1000)}s`
              : step.error_message ?? undefined,
        }))}
      />
    </div>
  )
}
