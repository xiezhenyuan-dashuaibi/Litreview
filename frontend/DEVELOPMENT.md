# 开发环境配置

## 环境要求

- Node.js >= 16.0.0
- npm >= 7.0.0 或 yarn >= 1.22.0

## 开发模式

当前项目配置为开发模式，所有API调用都使用Mock数据。这允许您：

1. **无需后端服务**即可运行和测试前端功能
2. **快速开发**和调试用户界面
3. **模拟各种场景**，包括成功、失败、加载状态等

## 切换到生产模式

当后端服务准备就绪时，请按以下步骤操作：

### 1. 修改主入口文件

编辑 `src/main.tsx`：

```typescript
// 注释掉Mock服务启用代码
// async function enableMocking() {
//   if (process.env.NODE_ENV !== 'development') {
//     return;
//   }
//   
//   const { worker } = await import('./mocks/browser.ts')
//   return worker.start({
//     onUnhandledRequest: 'bypass',
//   });
// }

// 直接启动应用
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

### 2. 更新API配置

编辑 `src/services/api.ts`：

```typescript
// 修改API基础URL
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-api-server.com/api'  // 替换为您的API地址
  : '/api';
```

### 3. 更新Vite配置

编辑 `vite.config.ts`：

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // 生产环境不需要代理配置
    // proxy: {
    //   '/api': {
    //     target: 'http://localhost:3001',
    //     changeOrigin: true
    //   }
    // }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
```

### 4. 环境变量配置

创建 `.env.production` 文件：

```bash
# API服务器地址
VITE_API_BASE_URL=https://your-api-server.com/api

# 其他生产环境配置
VITE_APP_TITLE=AI文献综述生成器
VITE_APP_VERSION=1.0.0
```

### 5. 构建和部署

```bash
# 构建生产版本
npm run build

# 构建产物将在 dist/ 目录中
# 可以部署到任何静态文件服务器
```

## Mock数据说明

开发模式下的Mock数据包括：

### 模拟文献数据
- 5篇示例学术论文
- 包含标题、作者、年份、摘要、关键词等信息

### 模拟聚类方案
- 3种不同的分组方案（方法维度、应用域、技术路线）
- 每种方案包含多个分组

### 模拟生成内容
- 完整的综述文档结构
- 包含引言、相关工作、方法分析、应用现状、结论等章节

## 开发建议

1. **保持Mock数据更新**：确保Mock数据与实际API响应格式一致
2. **错误处理**：测试各种错误情况，包括网络错误、验证错误等
3. **性能优化**：模拟慢网络情况，确保良好的用户体验
4. **响应式设计**：在不同设备上测试界面适配性

## 常见问题

### Q: 如何添加新的Mock API？
A: 在 `src/mocks/handlers.ts` 中添加新的处理器，然后在 `src/mocks/browser.ts` 中导出。

### Q: 如何修改现有Mock数据？
A: 编辑 `src/mocks/data.ts` 中的数据，所有引用该数据的组件会自动更新。

### Q: 如何模拟网络延迟？
A: 在Mock处理器中使用 `delay()` 函数来模拟网络延迟。

### Q: 如何禁用Mock服务？
A: 临时禁用可以在浏览器控制台中执行：`worker.stop()`。

## 联系支持

如有问题，请通过以下方式联系：
- 邮箱：support@example.com
- 文档：查看项目README.md文件