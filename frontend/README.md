# AI文献综述生成器 - 前端框架

## 项目概述

这是一个基于React + TypeScript的AI文献综述生成器前端应用。该应用提供了完整的文献综述生成工作流，包括文件上传、智能摘要、聚类分析、方案协商和综述生成等功能。

## 技术栈

- **前端框架**: React 18 + TypeScript
- **构建工具**: Vite
- **UI组件库**: Ant Design 5.x
- **状态管理**: React Context + useReducer
- **路由**: React Router v6
- **样式**: TailwindCSS
- **Mock服务**: MSW (Mock Service Worker)
- **HTTP客户端**: Axios

## 项目结构

```
frontend/
├── src/
│   ├── components/          # 通用组件
│   ├── pages/              # 页面组件
│   ├── hooks/              # 自定义Hooks
│   ├── services/           # API服务
│   ├── mocks/              # Mock数据和处理器
│   ├── stores/             # 状态管理
│   ├── types/              # TypeScript类型定义
│   ├── utils/              # 工具函数
│   └── assets/             # 静态资源
├── public/                 # 公共资源
├── package.json            # 项目依赖
├── vite.config.ts          # Vite配置
├── tailwind.config.js      # TailwindCSS配置
└── tsconfig.json           # TypeScript配置
```

## 核心功能

### 1. 系统配置
- API密钥配置
- 工作目录设置
- 系统状态检查

### 2. 文件上传
- ZIP文件上传
- 文件大小限制（200MB）
- 上传进度显示

### 3. 文献摘要
- 批量文献处理
- 进度实时显示
- 摘要结果展示

### 4. 聚类分析
- 多维度分组方案
- 智能文献分类
- 方案对比选择

### 5. 方案协商
- 交互式对话界面
- 实时方案调整
- 分组结构优化

### 6. 综述生成
- 流式内容生成
- 实时编辑功能
- 多格式导出

## 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 开发环境

```bash
npm run dev
```

访问 http://localhost:3000 查看应用

### 构建项目

```bash
npm run build
```

### 预览构建结果

```bash
npm run preview
```

## Mock数据

项目使用MSW进行API模拟，所有后端调用都返回预设的模拟数据，便于前端开发和测试。实际部署时需要替换为真实的后端服务。

## 状态管理

使用React Context和useReducer进行全局状态管理，主要状态包括：
- 系统状态（配置信息）
- 上传状态（文件和进度）
- 摘要状态（处理结果）
- 聚类状态（分组方案）
- 生成状态（综述内容）

## 路由设计

- `/` - 首页介绍
- `/start` - 系统配置
- `/upload` - 文件上传
- `/summary` - 摘要生成
- `/cluster` - 聚类分析
- `/plan` - 方案展示
- `/generate` - 综述生成
- `/result` - 结果展示

## 部署说明

由于采用纯前端架构，可以直接部署到静态托管服务：

1. **Vercel**: 支持GitHub集成，自动部署
2. **Netlify**: 拖拽部署或Git集成
3. **GitHub Pages**: 免费静态托管
4. **Nginx**: 传统Web服务器部署

## 开发说明

### 添加新页面

1. 在`src/pages/`创建页面组件
2. 在`src/App.tsx`添加路由
3. 在`src/types/`定义相关类型
4. 在`src/mocks/`添加Mock处理器

### 添加新API

1. 在`src/types/`定义请求和响应类型
2. 在`src/services/api.ts`添加API函数
3. 在`src/mocks/handlers.ts`添加Mock处理器

### 状态管理

1. 在`src/stores/AppContext.tsx`添加action类型
2. 在reducer中添加处理逻辑
3. 在组件中使用`useAppContext`访问状态

## 注意事项

- 当前为开发模式，所有数据均为模拟数据
- 实际部署需要配置真实的后端API服务
- 文件上传大小限制为200MB
- 支持现代浏览器（Chrome, Firefox, Safari, Edge）

## 后续优化

- [ ] 添加WebSocket支持实时通信
- [ ] 实现断点续传功能
- [ ] 添加多语言支持
- [ ] 优化移动端体验
- [ ] 添加用户认证功能
- [ ] 实现云端同步

## 许可证

MIT License