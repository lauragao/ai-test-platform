import { FileSearchOutlined, UnorderedListOutlined } from '@ant-design/icons'
import { Layout, Menu, Typography } from 'antd'
import { Link, Outlet, useLocation } from 'react-router-dom'

const { Header, Content } = Layout

export default function AppLayout() {
  const location = useLocation()
  const selected = location.pathname.startsWith('/tasks') ? '/tasks' : '/'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          padding: '0 24px',
          background: '#001529',
        }}
      >
        <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
          AI 需求分析平台
        </Typography.Title>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[selected]}
          style={{ flex: 1, minWidth: 0 }}
          items={[
            {
              key: '/',
              icon: <UnorderedListOutlined />,
              label: <Link to="/">任务列表</Link>,
            },
          ]}
        />
      </Header>
      <Content style={{ padding: '24px 48px', maxWidth: 1280, margin: '0 auto', width: '100%' }}>
        <Outlet />
      </Content>
    </Layout>
  )
}

export function PageHeader({ title, extra }: { title: string; extra?: React.ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
        flexWrap: 'wrap',
        gap: 12,
      }}
    >
      <Typography.Title level={3} style={{ margin: 0 }}>
        <FileSearchOutlined style={{ marginRight: 8 }} />
        {title}
      </Typography.Title>
      {extra}
    </div>
  )
}
