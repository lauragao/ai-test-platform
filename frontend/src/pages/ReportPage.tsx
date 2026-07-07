import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import {
  Button,
  Card,
  Collapse,
  Descriptions,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  exportTask,
  getDownloadUrl,
  getTask,
  getTaskDocument,
  getTaskReport,
} from '../api/tasks'
import type {
  RequirementIssue,
  TaskDetail,
  TaskDocument,
  TaskReport,
  TestCaseItem,
} from '../api/types'
import { PageHeader } from '../components/AppLayout'
import QualityAlert from '../components/QualityAlert'
import { severityColor } from '../utils/status'

export default function ReportPage() {
  const { taskNo = '' } = useParams()
  const [task, setTask] = useState<TaskDetail | null>(null)
  const [report, setReport] = useState<TaskReport | null>(null)
  const [document, setDocument] = useState<TaskDocument | null>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState<'xlsx' | 'xmind' | null>(null)

  const load = useCallback(async () => {
    if (!taskNo) return
    setLoading(true)
    try {
      const [detail, rep] = await Promise.all([getTask(taskNo), getTaskReport(taskNo)])
      setTask(detail)
      setReport(rep)
      try {
        setDocument(await getTaskDocument(taskNo))
      } catch {
        setDocument(null)
      }
    } catch {
      message.error('加载报告失败，请确认任务已完成')
    } finally {
      setLoading(false)
    }
  }, [taskNo])

  useEffect(() => {
    load()
  }, [load])

  const handleExport = async (format: 'xlsx' | 'xmind') => {
    setExporting(format)
    try {
      const result = await exportTask(taskNo, format)
      window.open(getDownloadUrl(result.download_url), '_blank')
      message.success(`${format.toUpperCase()} 导出成功`)
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      message.error(msg ?? '导出失败')
    } finally {
      setExporting(null)
    }
  }

  const issueColumns: ColumnsType<RequirementIssue> = [
    {
      title: '严重程度',
      dataIndex: 'severity',
      width: 100,
      render: (s: string) => <Tag color={severityColor(s)}>{s}</Tag>,
    },
    { title: '类型', dataIndex: 'issue_type', width: 100 },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      width: 240,
    },
    {
      title: '建议',
      dataIndex: 'suggestion',
      ellipsis: true,
      width: 200,
    },
  ]

  const caseColumns: ColumnsType<TestCaseItem> = [
    { title: '编号', dataIndex: 'case_key', width: 110 },
    { title: '模块', dataIndex: 'module', width: 120, ellipsis: true },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 80,
      render: (p: string) => <Tag>{p}</Tag>,
    },
    {
      title: '步骤',
      dataIndex: 'steps',
      width: 200,
      ellipsis: true,
      render: (steps: string[]) => steps?.join(' → '),
    },
    {
      title: '预期结果',
      dataIndex: 'expected_result',
      ellipsis: true,
      width: 180,
    },
    {
      title: '关联需求',
      dataIndex: 'source_requirement_ids',
      width: 120,
      render: (ids: string[]) => ids?.join(', ') ?? '-',
    },
  ]

  const issues = report?.analyze?.issues ?? []
  const cases = report?.cases?.test_cases ?? []
  const requirements = report?.requirements ?? []

  return (
    <>
      <PageHeader
        title="分析报告"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
              刷新
            </Button>
            <Button
              icon={<DownloadOutlined />}
              loading={exporting === 'xlsx'}
              onClick={() => handleExport('xlsx')}
            >
              导出 Excel
            </Button>
            <Button
              icon={<DownloadOutlined />}
              loading={exporting === 'xmind'}
              onClick={() => handleExport('xmind')}
            >
              导出 XMind
            </Button>
          </Space>
        }
      />

      <QualityAlert warnings={task?.quality_warnings ?? report?.quality_warnings} />

      <Card loading={loading} style={{ marginBottom: 24 }}>
        <Space size="large" wrap>
          <Statistic title="需求点" value={requirements.length} />
          <Statistic title="发现问题" value={issues.length} />
          <Statistic title="测试用例" value={cases.length} />
          {document && (
            <Statistic title="文档章节" value={document.section_count} suffix="节" />
          )}
        </Space>
        {report?.extract?.summary && (
          <Typography.Paragraph type="secondary" style={{ marginTop: 16, marginBottom: 0 }}>
            {report.extract.summary}
          </Typography.Paragraph>
        )}
      </Card>

      {document && document.sections.length > 0 && (
        <Card title="原文章节" style={{ marginBottom: 24 }}>
          <Collapse
            items={document.sections.map((sec) => ({
              key: sec.section_id,
              label: (
                <Space>
                  <span>{sec.title || sec.section_id}</span>
                  {sec.parse_confidence != null && (
                    <Tag>置信度 {(sec.parse_confidence * 100).toFixed(0)}%</Tag>
                  )}
                </Space>
              ),
              children: (
                <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                  {sec.content}
                </Typography.Paragraph>
              ),
            }))}
          />
        </Card>
      )}

      <Card title={`需求问题（${issues.length}）`} style={{ marginBottom: 24 }}>
        <Table
          rowKey="issue_key"
          size="small"
          columns={issueColumns}
          dataSource={issues}
          pagination={{ pageSize: 10 }}
          expandable={{
            expandedRowRender: (row) => (
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="完整描述">{row.description}</Descriptions.Item>
                {row.suggestion && (
                  <Descriptions.Item label="修改建议">{row.suggestion}</Descriptions.Item>
                )}
                {row.source_refs?.map((ref, i) => (
                  <Descriptions.Item key={i} label={`原文引用 ${i + 1}`}>
                    [{ref.section_id}] {ref.quote}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            ),
          }}
        />
      </Card>

      <Card title={`测试用例（${cases.length}）`}>
        <Table
          rowKey="case_key"
          size="small"
          columns={caseColumns}
          dataSource={cases}
          pagination={{ pageSize: 15 }}
          expandable={{
            expandedRowRender: (row) => (
              <div>
                {row.precondition && (
                  <Typography.Paragraph>
                    <strong>前置条件：</strong>
                    {row.precondition}
                  </Typography.Paragraph>
                )}
                <Typography.Paragraph>
                  <strong>步骤：</strong>
                </Typography.Paragraph>
                <ol style={{ margin: 0, paddingLeft: 20 }}>
                  {row.steps.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
                <Typography.Paragraph style={{ marginTop: 8 }}>
                  <strong>预期结果：</strong>
                  {row.expected_result}
                </Typography.Paragraph>
              </div>
            ),
          }}
        />
      </Card>

      <div style={{ marginTop: 16 }}>
        <Space>
          <Link to={`/tasks/${taskNo}`}>← 任务详情</Link>
          <Link to="/">任务列表</Link>
        </Space>
      </div>
    </>
  )
}
