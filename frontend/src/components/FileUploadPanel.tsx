import { InboxOutlined } from '@ant-design/icons'
import { Input, Upload, message } from 'antd'
import type { UploadProps } from 'antd'
import { useState } from 'react'
import { createTask } from '../api/tasks'

const ACCEPT = '.md,.markdown,.txt,.docx'

interface FileUploadPanelProps {
  onSuccess: (taskNo: string) => void
}

export default function FileUploadPanel({ onSuccess }: FileUploadPanelProps) {
  const [title, setTitle] = useState('')
  const [uploading, setUploading] = useState(false)

  const uploadProps: UploadProps = {
    accept: ACCEPT,
    maxCount: 1,
    showUploadList: false,
    beforeUpload: async (file) => {
      setUploading(true)
      try {
        const taskNo = await createTask(file, title || undefined)
        message.success(`任务已提交：${taskNo}`)
        onSuccess(taskNo)
      } catch (err: unknown) {
        const msg =
          err && typeof err === 'object' && 'response' in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined
        message.error(msg ?? '上传失败，请重试')
      } finally {
        setUploading(false)
      }
      return false
    },
  }

  return (
    <div>
      <Input
        placeholder="文档标题（可选）"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        style={{ marginBottom: 12, maxWidth: 400 }}
        allowClear
      />
      <Upload.Dragger {...uploadProps} disabled={uploading}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽上传需求文档</p>
        <p className="ant-upload-hint">支持 .md / .txt / .docx，分析约需 5~10 分钟</p>
      </Upload.Dragger>
    </div>
  )
}
