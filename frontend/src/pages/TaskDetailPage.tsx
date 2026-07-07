import {
  FileTextOutlined,
  RedoOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  Button,
  Card,
  Descriptions,
  Progress,
  Space,
  Tag,
  Typography,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getTask, getTaskSteps, retryTask } from '../api/tasks'
import type { TaskDetail, TaskStep } from '../api/types'
import { PageHeader } from '../components/AppLayout'
import QualityAlert from '../components/QualityAlert'
import TaskProgress from '../components/TaskProgress'
import { STATUS_LABELS, isRunning, statusColor } from '../utils/status'

const POLL_INTERVAL = 4000

export default function TaskDetailPage() {
  const { taskNo = '' } = useParams()
  const navigate = useNavigate()
  const [task, setTask] = useState<TaskDetail | null>(null)
  const [steps, setSteps] = useState<TaskStep[]>([])
  const [loading, setLoading] = useState(true)
  const [retrying, setRetrying] = useState(false)

  const load = useCallback(async () => {
    if (!taskNo) return
    try {
      const [detail, stepList] = await Promise.all([
        getTask(taskNo),
        getTaskSteps(taskNo),
      ])
      setTask(detail)
      setSteps(stepList)
    } catch {
      message.error('加载任务详情失败')
    } finally {
      setLoading(false)
    }
  }, [taskNo])

  useEffect(() => {
    setLoading(true)
    load()
  }, [load])

  useEffect(() => {
    if (!task || !isRunning(task.status)) return
    const timer = window.setInterval(load, POLL_INTERVAL)
    return () => window.clearInterval(timer)
  }, [task?.status, load, task])

  const handleRetry = async () => {
    if (!taskNo) return
    setRetrying(true)
    try {
      await retryTask(taskNo)
      message.success('任务已重新提交')
      setLoading(true)
      await load()
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      message.error(msg ?? '重试失败')
    } finally {
      setRetrying(false)
    }
  }

  if (!task && !loading) {
    return <Typography.Text type="danger">任务不存在</Typography.Text>
  }

  const canViewReport =
    task?.has_report ||
    task?.status === 'case_completed' ||
    task?.status === 'completed'

  return (
    <>
      <PageHeader
        title={`任务详情`}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
              刷新
            </Button>
            {task?.status === 'failed' && (
              <Button
                type="primary"
                icon={<RedoOutlined />}
                loading={retrying}
                onClick={handleRetry}
              >
                重试
              </Button>
            )}
            {canViewReport && (
              <Button
                type="primary"
                icon={<FileTextOutlined />}
                onClick={() => navigate(`/tasks/${taskNo}/report`)}
              >
                查看报告
              </Button>
            )}
          </Space>
        }
      />

      <QualityAlert warnings={task?.quality_warnings} />

      <Card loading={loading} style={{ marginBottom: 24 }}>
        <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
          <Descriptions.Item label="任务号">{task?.task_no}</Descriptions.Item>
          <Descriptions.Item label="文件">{task?.source_file ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {task && (
              <Tag color={statusColor(task.status)}>
                {STATUS_LABELS[task.status] ?? task.status}
              </Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="当前步骤">
            {task?.step_message ?? task?.current_step ?? '-'}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {task?.created_at ? dayjs(task.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="完成时间">
            {task?.finished_at
              ? dayjs(task.finished_at).format('YYYY-MM-DD HH:mm:ss')
              : '-'}
          </Descriptions.Item>
          {task?.error_message && (
            <Descriptions.Item label="错误" span={2}>
              <Typography.Text type="danger">
                [{task.error_code}] {task.error_message}
              </Typography.Text>
            </Descriptions.Item>
          )}
        </Descriptions>

        <div style={{ marginTop: 24 }}>
          <Progress
            percent={task?.progress ?? 0}
            status={
              task?.status === 'failed'
                ? 'exception'
                : isRunning(task?.status ?? '')
                  ? 'active'
                  : 'success'
            }
          />
        </div>
      </Card>

      <Card title="执行步骤">
        {steps.length > 0 ? (
          <TaskProgress
            steps={steps}
            progress={task?.progress ?? 0}
            stepMessage={task?.step_message}
          />
        ) : (
          <Typography.Text type="secondary">
            {isRunning(task?.status ?? '')
              ? '流水线启动中，请稍候…（分析约需 5~10 分钟）'
              : '暂无步骤记录'}
          </Typography.Text>
        )}
      </Card>

      <div style={{ marginTop: 16 }}>
        <Link to="/">← 返回任务列表</Link>
      </div>
    </>
  )
}
