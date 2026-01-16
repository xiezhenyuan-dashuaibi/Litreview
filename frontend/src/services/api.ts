import axios from 'axios';
import { 
  StartRequest, 
  StartResponse, 
  UploadResponse, 
  SummaryStatusResponse,
  ClusterAnalyzeResponse,
  GenerateStartRequest,
  GenerateStartResponse,
  ApiResponse 
} from '../types';

const API_BASE_URL = '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // 处理未认证情况
      console.error('未认证，需要重新登录');
    }
    return Promise.reject(error);
  }
);

export const systemApi = {
  // 系统启动
  start: async (data: StartRequest): Promise<ApiResponse<StartResponse>> => {
    const response = await apiClient.post('/system/start', data);
    return response.data;
  },

  // 测试模型API连接
  testModel: async (apiKey: string, model?: string): Promise<ApiResponse<{ ok: boolean; status_code: number }>> => {
    const response = await apiClient.post('/system/test/model', { apiKey, model });
    return response.data;
  },

  // 测试OCR API连接
  testOcr: async (accessKeyId: string, secretAccessKey: string): Promise<ApiResponse<{ ok: boolean; status_code: number }>> => {
    const response = await apiClient.post('/system/test/ocr', { accessKeyId, secretAccessKey });
    return response.data;
  },

  // 选择工作目录（本机弹窗）
  pickWorkingDir: async (): Promise<ApiResponse<{ path: string }>> => {
    const response = await apiClient.get('/system/pick-working-dir');
    return response.data;
  },

  // 检查工作目录 (默认检查是否为空，expectCollection=true时检查是否包含"文献整理合集")
  checkWorkingDir: async (path: string, expectCollection: boolean = false): Promise<ApiResponse<{ ok: boolean }>> => {
    const response = await apiClient.post('/system/check-working-dir', { path, expect_collection: expectCollection });
    return response.data;
  },

  // 检查系统状态
  checkStatus: async (): Promise<ApiResponse<{ status: string }>> => {
    const response = await apiClient.get('/system/status');
    return response.data;
  },

  // 打开 raw_content_dict.json 所在输出文件夹（最终文献综述）
  openRawContentFolder: async (): Promise<ApiResponse<{ path: string }>> => {
    const response = await axios.post('http://127.0.0.1:8001/api/system/open-raw-content-folder', {});
    return response.data;
  }
};

export const systemDebugApi = {
  printEnv: async (): Promise<ApiResponse<{ ARK_API_KEY: string; LITREVIEW_WORKDIR: string; VOLC_ACCESS_KEY: string; VOLC_SECRET_KEY: string }>> => {
    const response = await apiClient.post('/system/print-env', {});
    return response.data;
  }
};

export const systemConfigApi = {
  getEnv: async (): Promise<ApiResponse<{ ARK_API_KEY: string; VOLC_ACCESS_KEY: string; VOLC_SECRET_KEY: string; RESEARCH_TOPIC?: string; RESEARCH_DESCRIPTION?: string }>> => {
    const response = await apiClient.get('/system/config');
    return response.data;
  },
  save: async (data: { apiKey: string; workingDirectory: string; accessKeyId: string; secretAccessKey: string }): Promise<ApiResponse<{ apiKey: string; workingDirectory: string; accessKeyId: string; secretAccessKey: string }>> => {
    const response = await apiClient.post('/system/save-config', data);
    return response.data;
  }
};

export const uploadApi = {
  // 上传ZIP文件
  uploadZip: async (file: File): Promise<ApiResponse<UploadResponse>> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await axios.post('/api/upload/zip', formData);
    
    return response.data;
  }
};

export const researchApi = {
  save: async (topic: string, description: string): Promise<ApiResponse<{ saved: boolean }>> => {
    const response = await apiClient.post('/research/save', { topic, description });
    return response.data;
  }
};

export const summaryApi = {
  // 获取摘要状态
  getStatus: async (taskId: string): Promise<ApiResponse<SummaryStatusResponse>> => {
    const response = await apiClient.get(`/summary/status/${taskId}`);
    return response.data;
  },

  // 开始摘要生成
  startSummary: async (taskId: string): Promise<ApiResponse<{ summaryId: string }>> => {
    const response = await apiClient.post('/summary/start', { taskId });
    return response.data;
  }
};

export const clusterApi = {
  // 执行聚类分析
  analyze: async (data: { taskId: string; k: number; similarityThreshold: number }): Promise<ApiResponse<ClusterAnalyzeResponse>> => {
    const response = await apiClient.post('/cluster/start', data);
    return response.data;
  }
};

export const generateApi = {
  // 开始生成综述
  startGeneration: async (data: GenerateStartRequest): Promise<ApiResponse<GenerateStartResponse>> => {
    // 使用完整 URL 绕过 MSW 拦截
    const response = await axios.post('http://127.0.0.1:8001/api/generate/start', data);
    return response.data;
  },

  // 获取生成状态
  getStatus: async (generationId: string): Promise<ApiResponse<any>> => {
    const response = await apiClient.get(`/generate/status/${generationId}`);
    return response.data;
  }
};

export default apiClient;
