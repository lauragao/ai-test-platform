import { ReloadOutlined } from '@ant-design/icons'
import { Button, Card, Space, Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listTasks } from '../api/tasks'
import type { TaskSummary } from '../api/types'
import { PageHeader } from '../components/AppLayout'
import FileUploadPanel from '../components/FileUploadPanel'
import { STATUS_LABELS, statusColor } from '../utils/status'

export default function TaskListPage() {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<TaskSummary[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setTasks(await listTasks(50))
    } catch {
      message.error('加载任务列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const columns: ColumnsType<TaskSummary> = [
    {
      title: '任务号',
      dataIndex: 'task_no',
      render: (no: string) => <Link to={`/tasks/${no}`}>{no}</Link>,
    },
    {
      title: '文件',
      dataIndex: 'source_file',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (status: string) => (
        <Tag color={statusColor(status)}>{STATUS_LABELS[status] ?? status}</Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      width: 80,
      render: (p: number) => `${p}%`,
    },
    {
      title: '告警',
      dataIndex: 'should_warn_user',
      width: 80,
      render: (warn: boolean) => (warn ? <Tag color="warning">有</Tag> : '-'),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      width: 120,
      render: (_, row) => (
        <Space>
          <Link to={`/tasks/${row.task_no}`}>详情</Link>
          {(row.status === 'case_completed' || row.status === 'completed') && (
            <Link to={`/tasks/${row.task_no}/report`}>报告</Link>
          )}
        </Space>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        title="任务列表"
        extra={
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            刷新
          </Button>
        }
      />

      <Card title="上传需求文档" style={{ marginBottom: 24 }}>
        <FileUploadPanel
          onSuccess={(taskNo) => {
            load()
            navigate(`/tasks/${taskNo}`)
          }}
        />
      </Card>

      <Card title="最近任务">
        <Table
          rowKey="task_no"
          loading={loading}
          columns={columns}
          dataSource={tasks}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无任务，请上传需求文档开始分析' }}
        />
      </Card>
    </>
  )
}
