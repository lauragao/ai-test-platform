import { Alert } from 'antd'
import type { TaskQualityWarnings } from '../api/types'

interface QualityAlertProps {
  warnings?: TaskQualityWarnings | null
}

export default function QualityAlert({ warnings }: QualityAlertProps) {
  if (!warnings?.should_warn_user || !warnings.items.length) return null

  const type =
    warnings.alert_level === 'critical'
      ? 'error'
      : warnings.alert_level === 'warning'
        ? 'warning'
        : 'info'

  return (
    <Alert
      type={type}
      showIcon
      message="质量告警"
      description={
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {warnings.items.map((item, index) => (
            <li key={`${item.warning_type}-${index}`}>
              [{item.level}] {item.message}
            </li>
          ))}
        </ul>
      }
      style={{ marginBottom: 16 }}
    />
  )
}
