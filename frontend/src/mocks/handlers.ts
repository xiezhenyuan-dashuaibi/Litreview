import { http, HttpResponse } from 'msw';
import { 
  StartRequest, 
  StartResponse, 
  UploadResponse, 
  SummaryStatusResponse,
  ClusterAnalyzeResponse,
  GenerateStartResponse
} from '../types';
import { mockPapers, mockSummaryResults, mockClusterSchemes } from './data';

// 模拟延迟
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// 任务进度状态（内存模拟）
const taskStatus: Record<string, { total: number; completed: number; failed: number; files: string[] }> = {};

// 系统启动
export const startHandler = http.post('/api/system/start', async ({ request }) => {
  await delay(1000);
  
  const body = await request.json() as StartRequest;
  
  if (!body.apiKey || !body.workingDirectory) {
    return HttpResponse.json({
      status: 'error',
      message: 'API密钥和工作目录不能为空'
    }, { status: 400 });
  }

  const response: StartResponse = {
    sessionId: `session_${Date.now()}`,
    workingPath: body.workingDirectory
  };

  return HttpResponse.json({
    status: 'success',
    message: '系统启动成功',
    data: response
  });
});

// 文件上传
export const uploadHandler = http.post('/api/upload/zip', async ({ request }) => {
  await delay(2000);
  
  const formData = await request.formData();
  const file = formData.get('file');
  
  if (!file || !(file instanceof File)) {
    return HttpResponse.json({
      status: 'error',
      message: '请上传有效的ZIP文件'
    }, { status: 400 });
  }

  const response: UploadResponse = {
    taskId: `task_${Date.now()}`,
    fileCount: mockPapers.length,
    extractPath: `/tmp/extracted_${Date.now()}`
  };

  // 初始化对应任务的摘要状态
  taskStatus[response.taskId] = {
    total: 5,
    completed: 0,
    failed: 0,
    files: ['paper_1.pdf', 'paper_2.pdf', 'paper_3.pdf', 'paper_4.pdf', 'paper_5.pdf']
  };

  return HttpResponse.json({
    status: 'success',
    message: '文件上传成功',
    data: response
  });
});

// 摘要状态
export const summaryStatusHandler = http.get('/api/summary/status/:taskId', async ({ params }) => {
  await delay(500);
  
  const { taskId } = params as { taskId: string };
  const status = taskStatus[taskId] || { total: 5, completed: 0, failed: 0, files: [] };

  // 每次查询推进一篇（直到完成）
  if (status.completed < status.total) {
    status.completed += 1;
  }

  const isCompleted = status.completed >= status.total;

  const response: SummaryStatusResponse = {
    status: isCompleted ? 'completed' : 'processing',
    progress: Math.round((status.completed / status.total) * 100),
    total: status.total,
    completed: status.completed,
    failed: status.failed,
    currentFile: isCompleted ? undefined : status.files[status.completed]
  };

  return HttpResponse.json({
    status: 'success',
    data: response
  });
});

// 摘要开始
export const summaryStartHandler = http.post('/api/summary/start', async ({ request }) => {
  await delay(800);

  const body = await request.json() as { taskId?: string };
  if (!body?.taskId) {
    return HttpResponse.json({
      status: 'error',
      message: '缺少 taskId'
    }, { status: 400 });
  }

  return HttpResponse.json({
    status: 'success',
    message: '摘要任务已启动',
    data: { summaryId: `summary_${Date.now()}` }
  });
});

// 聚类分析
export const clusterAnalyzeHandler = http.post('/api/cluster/analyze', async ({ request }) => {
  await delay(3000);
  
  const body = await request.json();
  
  const response: ClusterAnalyzeResponse = {
    schemes: mockClusterSchemes
  };

  return HttpResponse.json({
    status: 'success',
    message: '聚类分析完成',
    data: response
  });
});

// 生成开始
export const generateStartHandler = http.post('/api/generate/start', async ({ request }) => {
  await delay(1000);
  
  const body = await request.json();
  
  const response: GenerateStartResponse = {
    generationId: `gen_${Date.now()}`,
    estimatedTime: 600 // 10分钟
  };

  return HttpResponse.json({
    status: 'success',
    message: '综述生成任务已启动',
    data: response
  });
});

// 生成状态
export const generateStatusHandler = http.get('/api/generate/status/:generationId', async () => {
  await delay(1000);
  
  return HttpResponse.json({
    status: 'success',
    data: {
      status: 'generating',
      progress: Math.floor(Math.random() * 100),
      currentSection: '相关工作综述',
      content: '# 文献综述\n\n## 引言\n\n随着人工智能技术的快速发展...\n\n## 相关工作综述\n\n### 深度学习在图像识别中的应用\n\n深度学习技术已经在图像识别领域取得了突破性进展...'
    }
  });
});

export const handlers = [
  startHandler,
  uploadHandler,
  summaryStartHandler,
  summaryStatusHandler,
  clusterAnalyzeHandler,
  generateStartHandler,
  generateStatusHandler
];
