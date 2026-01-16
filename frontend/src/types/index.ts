export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  abstract: string;
  keywords: string[];
  method: string;
  conclusion: string;
  fileName: string;
}

export interface SummaryResult {
  paperId: string;
  title: string;
  background: string;
  method: string;
  conclusion: string;
  limitations: string;
  markdownPath: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error?: string;
}

export interface ClusterGroup {
  id: string;
  name: string;
  description: string;
  papers: string[];
  theme: string;
}

export interface ClusterScheme {
  id: string;
  name: string;
  description: string;
  groups: ClusterGroup[];
  applicableScenario: string;
}

export interface SystemState {
  isInitialized: boolean;
  workingDirectory: string;
  apiKey: string;
  accessKeyId?: string;
  secretAccessKey?: string;
  sessionId: string;
}

export interface UploadState {
  taskId: string;
  files: File[];
  progress: number;
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'failed';
  extractPath?: string;
}

export interface SummaryState {
  status: 'idle' | 'processing' | 'completed' | 'failed';
  progress: number;
  total: number;
  completed: number;
  failed: number;
  results: SummaryResult[];
  currentFile?: string;
}

export interface ClusterState {
  schemes: ClusterScheme[];
  selectedScheme: string;
  status: 'idle' | 'processing' | 'completed' | 'failed';
  graphData?: any;
}

export interface GenerateState {
  status: 'idle' | 'generating' | 'completed' | 'failed';
  content: string;
  progress: number;
  currentSection?: string;
}

export interface AppState {
  system: SystemState;
  upload: UploadState;
  summary: SummaryState;
  cluster: ClusterState;
  generate: GenerateState;
}

export interface ApiResponse<T> {
  status: 'success' | 'error';
  message: string;
  data?: T;
}

export interface StartRequest {
  apiKey: string;
  workingDirectory: string;
  accessKeyId?: string;
  secretAccessKey?: string;
}

export interface StartResponse {
  sessionId: string;
  workingPath: string;
}

export interface UploadResponse {
  taskId: string;
  fileCount: number;
  extractPath: string;
}

export interface SummaryStatusResponse {
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  total: number;
  completed: number;
  failed: number;
  currentFile?: string;
}

export interface ClusterAnalyzeRequest {
  taskId: string;
  k: number;
  similarityThreshold: number;
}

export interface ClusterAnalyzeResponse {
  schemes: ClusterScheme[];
  graphData?: any;
}

export interface GenerateStartRequest {
  schemeId: string;
  model: string;
  temperature: number;
}

export interface GenerateStartResponse {
  generationId: string;
  estimatedTime: number;
}

export interface WebSocketMessage {
  type: 'adjust' | 'adjust_result' | 'heartbeat';
  payload: any;
}
