import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import ReportPage from './pages/ReportPage'
import TaskDetailPage from './pages/TaskDetailPage'
import TaskListPage from './pages/TaskListPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<TaskListPage />} />
          <Route path="tasks/:taskNo" element={<TaskDetailPage />} />
          <Route path="tasks/:taskNo/report" element={<ReportPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
