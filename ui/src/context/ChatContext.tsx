// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.
import { createContext, useContext, useReducer, Dispatch, useRef, useEffect, useState } from 'react';
import { Message } from '../types/types';
import { app } from '../utils/comfyapp';
import { ConfigProvider } from 'antd';
import useDarkMode from '../hooks/useDarkTheme';

// Add tab type definition
export type TabType = 'chat' | 'parameter-debug';

// Interface for tracking ParameterDebugInterface screen state
export interface ScreenState {
  currentScreen: number;
  isProcessing: boolean;
  isCompleted: boolean;
}

interface DownloadProgress {
  id: string;
  percentage: number;
  status: string;
}

interface ChatState {
  messages: Message[];
  selectedNode: any | null;
  installedNodes: any[];
  loading: boolean;
  sessionId: string | null;
  showChat: boolean;
  activeTab: TabType;
  screenState: ScreenState | null; // Add screen state
}

type ChatAction = 
  | { type: 'SET_MESSAGES'; payload: Message[] }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_MESSAGE'; payload: Message }
  | { type: 'SET_SELECTED_NODE'; payload: any }
  | { type: 'SET_INSTALLED_NODES'; payload: any[] }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_SESSION_ID'; payload: string }
  | { type: 'SET_SHOW_CHAT'; payload: boolean }
  | { type: 'SET_ACTIVE_TAB'; payload: TabType }
  | { type: 'SET_SCREEN_STATE'; payload: ScreenState | null } // Add action for setting screen state
  | { type: 'CLEAR_MESSAGES' }

const initialState: ChatState = {
  messages: [],
  selectedNode: Object.keys(app?.canvas?.selected_nodes ?? {})?.length ? Object.values(app?.canvas?.selected_nodes) : null,
  installedNodes: [],
  loading: false,
  sessionId: null,
  showChat: false,
  activeTab: 'chat',
  screenState: null, // Initialize as null
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'SET_MESSAGES':
      return { ...state, messages: action.payload };
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'UPDATE_MESSAGE':
      return {
        ...state,
        messages: state.messages.map(msg => 
          msg.id === action.payload.id && !msg.finished ? action.payload : msg
        )
      };
    case 'SET_SELECTED_NODE':
      return { ...state, selectedNode: action.payload };
    case 'SET_INSTALLED_NODES':
      return { ...state, installedNodes: action.payload };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    case 'SET_SHOW_CHAT':
      return { ...state, showChat: action.payload };
    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };
    case 'SET_SCREEN_STATE':
      return { ...state, screenState: action.payload };
    case 'CLEAR_MESSAGES':
      return { ...state, messages: [] };
    default:
      return state;
  }
}

const ChatContext = createContext<{
  state: ChatState;
  dispatch: Dispatch<ChatAction>;
  showcasIng: React.MutableRefObject<boolean>;
  abortControllerRef: React.RefObject<AbortController | null>;
  modelDownloadMap: Record<string, DownloadProgress>;
  addDownloadId: (id: string | string[]) => void;
}>({ state: initialState, dispatch: () => null, showcasIng: {current: false}, abortControllerRef: {current: null}, modelDownloadMap: {}, addDownloadId: () => {} });

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  const showcasIng = useRef<boolean>(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [modelDownloadMap, setModelDownloadMap] = useState<Record<string, DownloadProgress>>({});
  const currentDownloadingId = useRef<string[]>([]);

  // const isDark = app.extensionManager.setting.get('Comfy.ColorPalette') === 'dark';

  const getProgress = async (id: string) => {
    const response = await fetch(`/api/download-progress/${id}`)
    const res = await response.json()
    return res.data || null
  }

  const isDark = useDarkMode()
  
  // 轮询下载进度
  const modelDownloadPolling = async () => {
    if (currentDownloadingId?.current?.length > 0) {
      const responses = await Promise.all(currentDownloadingId?.current?.map(id => getProgress(id)))
      let map: Record<string, DownloadProgress> = {}
      responses?.forEach((response) => {
        if (!!response) {
          map[response.id] = {
            id: response.id,
            percentage: response.percentage,
            status: response.status
          }
          if (response.status === 'completed' || response.status === 'failed') {
            currentDownloadingId?.current?.splice(currentDownloadingId?.current?.indexOf(response.id), 1)
          }
        }
      })
      setModelDownloadMap(map)
      if (currentDownloadingId?.current?.length > 0) {
        setTimeout(() => {
          modelDownloadPolling()
        }, 2000)
      }
    } 
  }

  // 新增id到下载id列表，开始轮询
  const addDownloadId = (id: string | string[]) => {
    if (Array.isArray(id)) {
      currentDownloadingId.current.push(...id)
    } else {
      currentDownloadingId.current.push(id)
    }
    modelDownloadPolling()
  }

  // 获取当前正在下载的列表
  const getDownloadProgress = async () => {
    const response = await fetch('/api/download-progress')
    const res = await response.json()
    if (res?.data?.downloads?.length > 0) {
      addDownloadId(res.data.downloads)
    }
  }

  useEffect(() => {
    getDownloadProgress()
  }, [])

  // Update localStorage cache when messages or sessionId changes
  useEffect(() => {
    if (state.sessionId && state.messages.length > 0) {
      localStorage.setItem(`messages_${state.sessionId}`, JSON.stringify(state.messages));
    }
  }, [state.messages, state.sessionId]);

  // useEffect(() => {
  //   console.log('--->', app.extensionManager.setting.get('Comfy.ColorPalette'))
  // }, [app.extensionManager.setting.get('Comfy.ColorPalette')])

  return (
    <ConfigProvider
      theme={{
        token: {
          colorBgContainer: isDark ? '#18181b' : '#fff',
          colorBgElevated: isDark ? '#18181b' : '#fff',
          colorText: isDark ? 'rgba(255,255,255,0.88)' : 'rgba(0,0,0,0.88)',
          colorTextDescription: isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)',
          colorTextPlaceholder: isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.25)',
        },
        components: {
          Select: {
            optionSelectedBg: isDark ? '#333' : '#e6f4ff',
            optionActiveBg: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)'
          },
          Table: {
            borderColor: isDark ? '#666' : '#f0f0f0',
            headerBg: isDark ? '#333' : '#fafafa',
            headerColor: isDark ? '#fff' : '#18181b',
            rowHoverBg: isDark ? '#333' : '#fafafa',
          },
          Pagination: {
            itemBg: isDark ? 'rgb(24, 24, 27)' : '#fff',  
            itemActiveBg: isDark ? 'rgb(24, 24, 27)' : '#fff',  
            colorText: isDark ? 'rgba(255,255,255,0.88)' : 'rgba(0,0,0,0.88)',
            colorBgTextHover: isDark ? '#555' : 'rgba(0,0,0,0.06)',
            colorPrimary: isDark ? '#aaa' : '#1677ff',
            colorPrimaryHover: isDark ? '#999' : '#4096ff',
          },
          Form: {
            labelColor: isDark ? 'rgba(255,255,255,0.88)' : 'rgba(0,0,0,0.88)'
          },
          Button: {
            primaryShadow: isDark ? '0 2px 0 rgba(5,145,255,0.1)' : '0 2px 0 rgba(5,145,255,0.1)',
          }
        }
      }}
    >
      <ChatContext.Provider value={{ state, dispatch, showcasIng, abortControllerRef, modelDownloadMap, addDownloadId }}>
        {children}
      </ChatContext.Provider>
    </ConfigProvider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
} 