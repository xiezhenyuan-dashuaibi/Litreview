import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { AppState, Paper, SummaryResult, ClusterScheme } from '../types';

const initialState: AppState = {
  system: {
    isInitialized: false,
    workingDirectory: '',
    apiKey: '',
    accessKeyId: '',
    secretAccessKey: '',
    sessionId: ''
  },
  upload: {
    taskId: '',
    files: [],
    progress: 0,
    status: 'idle',
    extractPath: ''
  },
  summary: {
    status: 'idle',
    progress: 0,
    total: 0,
    completed: 0,
    failed: 0,
    results: []
  },
  cluster: {
    schemes: [],
    selectedScheme: '',
    status: 'idle',
    graphData: null
  },
  generate: {
    status: 'idle',
    content: '',
    progress: 0
  }
};

type Action = 
  | { type: 'SYSTEM_INIT'; payload: { apiKey: string; workingDirectory: string; sessionId: string; accessKeyId?: string; secretAccessKey?: string } }
  | { type: 'UPLOAD_START'; payload: { files: File[] } }
  | { type: 'UPLOAD_PROGRESS'; payload: { progress: number } }
  | { type: 'UPLOAD_COMPLETE'; payload: { taskId: string; extractPath: string } }
  | { type: 'SUMMARY_START'; payload: { total: number } }
  | { type: 'SUMMARY_PROGRESS'; payload: { completed: number; failed: number; currentFile?: string } }
  | { type: 'SUMMARY_COMPLETE'; payload: { results: SummaryResult[] } }
  | { type: 'CLUSTER_START' }
  | { type: 'CLUSTER_COMPLETE'; payload: { schemes: ClusterScheme[]; graphData?: any } }
  | { type: 'CLUSTER_SELECT_SCHEME'; payload: { schemeId: string } }
  | { type: 'GENERATE_START' }
  | { type: 'GENERATE_PROGRESS'; payload: { progress: number; content: string; currentSection?: string } }
  | { type: 'GENERATE_COMPLETE'; payload: { content: string } }
  | { type: 'GENERATE_RESET' }
  | { type: 'RESET' };

function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SYSTEM_INIT':
      return {
        ...state,
        system: {
          isInitialized: true,
          workingDirectory: action.payload.workingDirectory,
          apiKey: action.payload.apiKey,
          accessKeyId: action.payload.accessKeyId || '',
          secretAccessKey: action.payload.secretAccessKey || '',
          sessionId: action.payload.sessionId
        }
      };

    case 'UPLOAD_START':
      return {
        ...state,
        upload: {
          ...state.upload,
          files: action.payload.files,
          status: 'uploading',
          progress: 0
        }
      };

    case 'UPLOAD_PROGRESS':
      return {
        ...state,
        upload: {
          ...state.upload,
          progress: action.payload.progress
        }
      };

    case 'UPLOAD_COMPLETE':
      return {
        ...state,
        upload: {
          ...state.upload,
          taskId: action.payload.taskId,
          status: 'completed',
          progress: 100,
          extractPath: action.payload.extractPath
        }
      };

    case 'SUMMARY_START':
      return {
        ...state,
        summary: {
          ...state.summary,
          status: 'processing',
          total: action.payload.total,
          progress: 0
        }
      };

    case 'SUMMARY_PROGRESS':
      return {
        ...state,
        summary: {
          ...state.summary,
          completed: action.payload.completed,
          failed: action.payload.failed,
          progress: Math.round((action.payload.completed / state.summary.total) * 100)
        }
      };

    case 'SUMMARY_COMPLETE':
      return {
        ...state,
        summary: {
          ...state.summary,
          status: 'completed',
          results: action.payload.results,
          progress: 100
        }
      };

    case 'CLUSTER_START':
      return {
        ...state,
        cluster: {
          ...state.cluster,
          status: 'processing'
        }
      };

    case 'CLUSTER_COMPLETE':
      return {
        ...state,
        cluster: {
          ...state.cluster,
          status: 'completed',
          schemes: action.payload.schemes,
          graphData: action.payload.graphData
        }
      };

    case 'CLUSTER_SELECT_SCHEME':
      return {
        ...state,
        cluster: {
          ...state.cluster,
          selectedScheme: action.payload.schemeId
        }
      };

    case 'GENERATE_START':
      return {
        ...state,
        generate: {
          ...state.generate,
          status: 'generating',
          progress: 0,
          content: ''
        }
      };

    case 'GENERATE_PROGRESS':
      return {
        ...state,
        generate: {
          ...state.generate,
          progress: action.payload.progress,
          content: action.payload.content,
          // 如果 payload 中有值则更新，否则保持原样（防止闪烁）
          currentSection: action.payload.currentSection || state.generate.currentSection
        }
      };

    case 'GENERATE_COMPLETE':
      return {
        ...state,
        generate: {
          ...state.generate,
          status: 'completed',
          content: action.payload.content,
          progress: 100
        }
      };

    case 'GENERATE_RESET':
      return {
        ...state,
        generate: {
          ...state.generate,
          status: 'idle',
          content: '',
          progress: 0
        }
      };

    case 'RESET':
      return initialState;

    default:
      return state;
  }
}

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<Action>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
