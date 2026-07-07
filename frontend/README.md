# Frontend

AI 需求分析与测试用例生成平台 — MVP 前端（React + Ant Design）。

## 功能

- 上传需求文档（`.md` / `.txt` / `.docx`）
- 任务列表与状态轮询
- 任务详情（进度条、步骤时间线、质量告警、失败重试）
- 分析报告（问题列表、测试用例、原文章节）
- 导出 Excel / XMind

## 快速开始

**先启动后端**（端口 8000）：

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**再启动前端**：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开：http://localhost:5173

Vite 已将 `/api` 代理到 `http://localhost:8000`。

## 页面路由

| 路径 | 说明 |
|------|------|
| `/` | 任务列表 + 上传 |
| `/tasks/:taskNo` | 任务详情 |
| `/tasks/:taskNo/report` | 分析报告 |

## 构建

```bash
npm run build
npm run preview
```

## 技术栈

- React 18 + TypeScript
- Vite 5
- Ant Design 5
- React Router 6
- Axios
