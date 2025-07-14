/*
 * @Author: ai-business-hql ai.bussiness.hql@gmail.com
 * @Date: 2025-03-20 15:15:20
 * @LastEditors: ai-business-hql qingli.hql@alibaba-inc.com
 * @LastEditTime: 2025-05-14 20:48:24
 * @FilePath: /comfyui_copilot/ui/src/workflowChat/workflowChat.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import { ChangeEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { Message } from "../types/types";
import { WorkflowChatAPI } from "../apis/workflowChatApi";
import { ChatHeader } from "../components/chat/ChatHeader";
import { ChatInput } from "../components/chat/ChatInput";
import { SelectedNodeInfo } from "../components/chat/SelectedNodeInfo";
import { MessageList } from "../components/chat/MessageList";
import { generateUUID } from "../utils/uuid";
import { getInstalledNodes } from "../apis/comfyApiCustom";
import { UploadedImage } from '../components/chat/ChatInput';
import React from "react";
import { debounce } from "lodash";
import { useChatContext } from '../context/ChatContext';
import { useMousePosition } from '../hooks/useMousePosition';
import { useNodeSelection } from '../hooks/useNodeSelection';
import { MemoizedReactMarkdown } from "../components/markdown";
import remarkGfm from 'remark-gfm';
import rehypeExternalLinks from 'rehype-external-links';

// Define the Tab type - We should import this from context to ensure consistency
import type { TabType } from '../context/ChatContext';
import { ParameterDebugInterface } from "../components/debug/ParameterDebugInterfaceV2";
import { COPILOT_EVENTS } from "../constants/events";
import { app } from "../utils/comfyapp";

interface WorkflowChatProps {
    onClose?: () => void;
    visible?: boolean;
    triggerUsage?: boolean;
    onUsageTriggered?: () => void;
}

const enum DispatchEventType {
    NONE = 'None',
    USAGE = 'Usage',
    PARAMETERS = 'Parameters',
    DOWNSTREAM_NODES = 'DownstreamNodes'
}

// 优化公告组件样式 - 更加美观和专业，支持Markdown
const Announcement = ({ message, onClose }: { message: string, onClose: () => void }) => {
    if (!message) return null;
    
    return (
        <div 
            className="bg-gradient-to-r from-gray-50 to-gray-100 
            border border-gray-300 px-2 py-1 mt-2 ml-2 mr-2 relative shadow-sm rounded-sm"
        >
            <div className="flex items-center">
                <div className="flex-shrink-0 mr-1">
                    <svg className="w-3.5 h-3.5 text-gray-700" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"></path>
                    </svg>
                </div>
                <div className="text-gray-700 font-medium leading-relaxed pr-6 markdown-content" style={{ fontSize: '11px' }}>
                    <MemoizedReactMarkdown
                        rehypePlugins={[
                            [rehypeExternalLinks, { target: '_blank', rel: ['noopener', 'noreferrer'] }]
                        ]}
                        remarkPlugins={[remarkGfm]}
                        className="prose !text-[11px] prose-a:text-gray-700 prose-a:underline prose-a:font-medium hover:prose-a:text-gray-800"
                        components={{
                            a: ({ node, ...props }) => (
                                <a {...props} className="text-gray-700 underline hover:text-gray-800 transition-colors" style={{ fontSize: '11px' }} />
                            ),
                            p: ({ children }) => (
                                <span className="inline" style={{ fontSize: '11px' }}>{children}</span>
                            ),
                            // Add explicit styling for all text elements
                            span: ({ children }) => (
                                <span style={{ fontSize: '11px' }}>{children}</span>
                            ),
                            li: ({ children }) => (
                                <li style={{ fontSize: '11px' }}>{children}</li>
                            ),
                            ul: ({ children }) => (
                                <ul style={{ fontSize: '11px' }}>{children}</ul>
                            ),
                            ol: ({ children }) => (
                                <ol style={{ fontSize: '11px' }}>{children}</ol>
                            )
                        }}
                    >
                        {message}
                    </MemoizedReactMarkdown>
                </div>
            </div>
            <button 
                onClick={onClose}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-700 hover:text-gray-800 transition-colors p-1 rounded-full hover:bg-gray-800"
                aria-label="Close announcement"
            >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
    );
};

// Parameter Debug Tab Component
const ParameterDebugTab = () => {
    const { state, dispatch } = useChatContext();
    const { selectedNode, screenState } = state;
    const selectedNodes = selectedNode ? selectedNode : [];
    
    // const ParameterDebugInterface = React.lazy(() => 
    //   import("../components/debug/ParameterDebugInterfaceV2").then(module => ({
    //       default: module.ParameterDebugInterface
    //   }))
    // );
    
    const handleCloseParameterDebug = () => {
        // Clear selected nodes and screen state
        dispatch({ type: 'SET_SELECTED_NODE', payload: null });
        dispatch({ type: 'SET_SCREEN_STATE', payload: null });
        // 同时清除localStorage中保存的状态
        localStorage.removeItem("screenState");
    };
    
    return (
        <div className="flex-1 flex flex-col overflow-y-auto">
            <ParameterDebugInterface 
                selectedNodes={selectedNodes} 
                visible={true} 
                onClose={handleCloseParameterDebug}
            />
        </div>
    );
};

// Tab component
const TabButton = ({ 
    active, 
    onClick, 
    children 
}: { 
    active: boolean; 
    onClick: () => void; 
    children: React.ReactNode 
}) => (
    <button
        onClick={onClick}
        className={`px-4 py-2 font-medium text-xs transition-colors duration-200 border-b-2 ${
            active 
                ? "text-[#71A3F2] border-[#71A3F2]" 
                : "text-gray-600 border-transparent hover:!text-[#71A3F2] hover:!border-[#71A3F2]"
        }`}
    >
        {children}
    </button>
);

export default function WorkflowChat({ onClose, visible = true, triggerUsage = false, onUsageTriggered }: WorkflowChatProps) {
    const { state, dispatch } = useChatContext();
    const { messages, installedNodes, loading, sessionId, selectedNode, activeTab, guiding } = state;
    const messageDivRef = useRef<HTMLDivElement>(null);
    const [input, setInput] = useState<string>('');
    const [latestInput, setLatestInput] = useState<string>('');
    const [width, setWidth] = useState(window.innerWidth / 3);
    const [isResizing, setIsResizing] = useState(false);
    const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
    const [selectedModel, setSelectedModel] = useState<string>("gpt-4o-mini");
    const [height, setHeight] = useState<number>(window.innerHeight);
    const [topPosition, setTopPosition] = useState<number>(0);
    // 添加公告状态
    const [announcement, setAnnouncement] = useState<string>('');
    const [showAnnouncement, setShowAnnouncement] = useState<boolean>(false);
    // 添加 AbortController 引用
    const abortControllerRef = useRef<AbortController | null>(null);
    const currentSelectedNode = useRef<any>(selectedNode)
    const [dispatchEventType, setDispatchEventType] = useState<DispatchEventType>(DispatchEventType.NONE);
    // 使用自定义 hooks，只在visible为true且activeTab为chat时启用
    useMousePosition(visible && activeTab === 'chat');
    useNodeSelection(visible);

    // 使用自定义 hooks

    // useEffect(() => {
    //     if (messageDivRef.current) {
    //         messageDivRef.current.scrollTop = messageDivRef.current.scrollHeight
    //     }
    // }, [messages])

    useEffect(() => {
        switch(dispatchEventType) {
            case DispatchEventType.USAGE:
                onUsage()
            break;
            case DispatchEventType.PARAMETERS:
                onParameters()
            break;
            case DispatchEventType.DOWNSTREAM_NODES:
                onDownstreamNodes();
            break;
        }
        setDispatchEventType(DispatchEventType.NONE)
    }, [dispatchEventType])

    useEffect(() => {
        if (activeTab !== 'chat') return;
        
        const fetchInstalledNodes = async () => {
            const nodes = await getInstalledNodes();
            console.log('[WorkflowChat] Received installed nodes:', nodes.length);
            dispatch({ type: 'SET_INSTALLED_NODES', payload: nodes });
        };
        fetchInstalledNodes();
    }, [activeTab]);

    const showGuide = () => {
        dispatch({ type: 'SET_GUIDING', payload: true });
        dispatch({ type: 'SET_MESSAGES', payload: [
            {
                id: generateUUID(),
                role: 'question_title',
                content: ''
            }
        ]})
    }

    // 获取历史消息
    const fetchMessages = async (sid: string) => {
        try {
            const data = await WorkflowChatAPI.fetchMessages(sid);
            if (data?.length > 0) {
                dispatch({ type: 'SET_MESSAGES', payload: data });
            } else {
                showGuide()
            }
            // Note: The localStorage cache is already updated in the fetchMessages API function
        } catch (error) {
            console.error('Error fetching messages:', error);
        }
    };

    useEffect(() => {
        if (activeTab !== 'chat') return;
        
        let sid = localStorage.getItem("sessionId");
        if (sid) {
            dispatch({ type: 'SET_SESSION_ID', payload: sid });
            fetchMessages(sid);
        } else {
            sid = generateUUID();
            dispatch({ type: 'SET_SESSION_ID', payload: sid });
            localStorage.setItem("sessionId", sid);
        }
    }, [activeTab]);

    // 添加保存和恢复activeTab的逻辑
    useEffect(() => {
        // 从localStorage恢复activeTab状态
        const savedTab = localStorage.getItem("activeTab") as TabType;
        if (savedTab) {
            dispatch({ type: 'SET_ACTIVE_TAB', payload: savedTab });
        }
        
        // 从localStorage恢复screenState状态（如果存在）
        const savedScreenState = localStorage.getItem("screenState");
        if (savedScreenState) {
            dispatch({ type: 'SET_SCREEN_STATE', payload: JSON.parse(savedScreenState) });
        }

        const onToolBoxUsage = () => {
            setDispatchEventType(DispatchEventType.USAGE);
        }

        const onToolBoxParameters = () => {
            setDispatchEventType(DispatchEventType.PARAMETERS);
        }

        const onToolBoxDownstreamNodes = () => {
            setDispatchEventType(DispatchEventType.DOWNSTREAM_NODES);
        }

        window.addEventListener(COPILOT_EVENTS.TOOLBOX_USAGE, onToolBoxUsage);
        window.addEventListener(COPILOT_EVENTS.TOOLBOX_PARAMETERS, onToolBoxParameters);
        window.addEventListener(COPILOT_EVENTS.TOOLBOX_DOWNSTREAMNODES, onToolBoxDownstreamNodes);

        return () => {
            window.removeEventListener(COPILOT_EVENTS.TOOLBOX_USAGE, onToolBoxUsage);
            window.removeEventListener(COPILOT_EVENTS.TOOLBOX_PARAMETERS, onToolBoxParameters);
            window.removeEventListener(COPILOT_EVENTS.TOOLBOX_DOWNSTREAMNODES, onToolBoxDownstreamNodes);
        }
    }, []);
    
    // 当activeTab变化时保存到localStorage
    useEffect(() => {
        localStorage.setItem("activeTab", activeTab);
    }, [activeTab]);
    
    // 当screenState变化时保存到localStorage
    useEffect(() => {
        if (state.screenState) {
            localStorage.setItem("screenState", JSON.stringify(state.screenState));
        }
    }, [state.screenState]);

    // 使用防抖处理宽度调整
    const handleMouseMoveForResize = React.useCallback((e: MouseEvent) => {
        if (!isResizing) return;
        
        const newWidth = window.innerWidth - e.clientX;
        const clampedWidth = Math.min(
            Math.max(300, newWidth),
            window.innerWidth * 0.8
        );
        
        setWidth(clampedWidth);
    }, [isResizing]);

    const debouncedHandleMouseMoveForResize = React.useMemo(
        () => debounce(handleMouseMoveForResize, 16),
        [handleMouseMoveForResize]
    );

    useEffect(() => {
        if (isResizing) {
            document.addEventListener('mousemove', debouncedHandleMouseMoveForResize);
            document.addEventListener('mouseup', handleMouseUp);
        }

        return () => {
            document.removeEventListener('mousemove', debouncedHandleMouseMoveForResize);
            document.removeEventListener('mouseup', handleMouseUp);
            debouncedHandleMouseMoveForResize.cancel();
        };
    }, [isResizing, debouncedHandleMouseMoveForResize]);

    const handleMessageChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
        setInput(event.target.value);
    }

    const handleStop = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
            dispatch({ type: 'SET_LOADING', payload: false });
        }
    }

    const handleSendMessage = async () => {
        if (guiding) {
            dispatch({ type: 'SET_GUIDING', payload: false });
            dispatch({ type: 'CLEAR_MESSAGES' });
        }
        dispatch({ type: 'SET_LOADING', payload: true });
        if ((input.trim() === "" && !selectedNode) || !sessionId) return;
        setLatestInput(input);
        
        const traceId = generateUUID();

        const userMessage: Message = {
            id: generateUUID(),
            role: "user",
            content: input,
            trace_id: traceId,
        };

        dispatch({ type: 'ADD_MESSAGE', payload: userMessage });
        setInput("");

        // 创建新的 AbortController
        abortControllerRef.current = new AbortController();

        try {
            const modelExt = { type: "model_select", data: [selectedModel] };
            let aiMessageId = generateUUID(); // 生成一个固定的消息ID
            let isFirstResponse = true;

            for await (const response of WorkflowChatAPI.streamInvokeServer(
                sessionId, 
                input, 
                uploadedImages.map(img => img.file),
                null,
                modelExt,
                traceId,
                abortControllerRef.current.signal
            )) {
                const aiMessage: Message = {
                    id: aiMessageId,
                    role: "ai",
                    content: JSON.stringify(response),
                    format: response.format,
                    finished: response.finished,
                    name: "Assistant"
                };

                if (isFirstResponse) {
                    dispatch({ type: 'ADD_MESSAGE', payload: aiMessage });
                    isFirstResponse = false;
                } else {
                    dispatch({ type: 'UPDATE_MESSAGE', payload: aiMessage });
                    // Update localStorage cache
                    const updatedMessages = state.messages.map(msg => 
                        msg.id === aiMessage.id && !msg.finished ? aiMessage : msg
                    );
                    updateMessagesCache(updatedMessages);
                }

                if (response.finished) {
                    dispatch({ type: 'SET_LOADING', payload: false });
                    abortControllerRef.current = null;
                }
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                // 用户主动中断，不显示错误
                console.log('User aborted the request');
            } else {
                console.error('Error sending message:', error);
            }
            dispatch({ type: 'SET_LOADING', payload: false });
            abortControllerRef.current = null;
        } finally {
            setUploadedImages([]);
        }
    };

    const handleSendMessageWithContent = async (content: string) => {
        if (!sessionId) return;
        dispatch({ type: 'SET_LOADING', payload: true });
        setLatestInput(content);
        
        const traceId = generateUUID();

        const userMessage: Message = {
            id: generateUUID(),
            role: "user",
            content: content,
            trace_id: traceId,
        };

        dispatch({ type: 'ADD_MESSAGE', payload: userMessage });

        // 创建新的 AbortController
        abortControllerRef.current = new AbortController();

        try {
            const modelExt = { type: "model_select", data: [selectedModel] };
            let aiMessageId = generateUUID();
            let isFirstResponse = true;

            for await (const response of WorkflowChatAPI.streamInvokeServer(
                sessionId, 
                content, 
                uploadedImages.map(img => img.file),
                null,
                modelExt,
                traceId,
                abortControllerRef.current.signal
            )) {
                const aiMessage: Message = {
                    id: aiMessageId,
                    role: "ai",
                    content: JSON.stringify(response),
                    format: response.format,
                    finished: response.finished,
                    name: "Assistant"
                };

                if (isFirstResponse) {
                    dispatch({ type: 'ADD_MESSAGE', payload: aiMessage });
                    isFirstResponse = false;
                } else {
                    dispatch({ type: 'UPDATE_MESSAGE', payload: aiMessage });
                    // Update localStorage cache
                    const updatedMessages = state.messages.map(msg => 
                        msg.id === aiMessage.id && !msg.finished ? aiMessage : msg
                    );
                    updateMessagesCache(updatedMessages);
                }

                if (response.finished) {
                    dispatch({ type: 'SET_LOADING', payload: false });
                    abortControllerRef.current = null;
                }
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                // 用户主动中断，不显示错误
                console.log('User aborted the request');
            } else {
                console.error('Error sending message:', error);
            }
            dispatch({ type: 'SET_LOADING', payload: false });
            abortControllerRef.current = null;
        } finally {
            setUploadedImages([]);
        }
    };

    const handleKeyPress = (event: KeyboardEvent) => {
        if (event.metaKey && event.key === "Enter") {
            handleSendMessage();
        }
    }

    const handleClearMessages = () => {
        dispatch({ type: 'CLEAR_MESSAGES' });
        // Remove old session data
        const oldSessionId = state.sessionId;
        if (oldSessionId) {
            localStorage.removeItem(`messages_${oldSessionId}`);
        }
        localStorage.removeItem("sessionId");
        
        // Create new session
        const newSessionId = generateUUID();
        dispatch({ type: 'SET_SESSION_ID', payload: newSessionId });
        localStorage.setItem("sessionId", newSessionId);
        setTimeout(() => {
            showGuide()
        }, 500)
    };

    const avatar = (name?: string) => {
        return `https://ui-avatars.com/api/?name=${name || 'User'}&background=random`;
    }

    const handleClose = () => {
        onClose?.();
    };

    const handleOptionClick = (option: string) => {
        setInput(option);
    };

    const handleSendMessageWithIntent = async (intent: string, ext?: any) => {
        if (!sessionId || !selectedNode) return;
        dispatch({ type: 'SET_LOADING', payload: true });

        const nodeName = selectedNode[0].comfyClass || selectedNode[0].type;

        const traceId = generateUUID();
        const userMessage: Message = {
            id: generateUUID(),
            role: "user",
            content: nodeName,
            trace_id: traceId,
        };

        dispatch({ type: 'ADD_MESSAGE', payload: userMessage });

        // 创建新的 AbortController
        abortControllerRef.current = new AbortController();

        try {
            let aiMessageId = generateUUID();
            let isFirstResponse = true;

            for await (const response of WorkflowChatAPI.streamInvokeServer(
                sessionId, 
                nodeName,
                [], 
                intent, 
                ext,
                traceId,
                abortControllerRef.current.signal
            )) {
                const aiMessage: Message = {
                    id: aiMessageId,
                    role: "ai",
                    content: JSON.stringify(response),
                    format: response.format,
                    finished: response.finished,
                    name: "Assistant",
                };
                if (intent && intent !== '') {
                    aiMessage.metadata = {
                        intent: intent
                    }
                }

                if (isFirstResponse) {
                    dispatch({ type: 'ADD_MESSAGE', payload: aiMessage });
                    isFirstResponse = false;
                } else {
                    dispatch({ type: 'UPDATE_MESSAGE', payload: aiMessage });
                    // Update localStorage cache
                    const updatedMessages = state.messages.map(msg => 
                        msg.id === aiMessage.id && !msg.finished ? aiMessage : msg
                    );
                    updateMessagesCache(updatedMessages);
                }

                if (response.finished) {
                    dispatch({ type: 'SET_LOADING', payload: false });
                    abortControllerRef.current = null;
                }
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                // 用户主动中断，不显示错误
                console.log('User aborted the request');
            } else {
                console.error('Error sending message:', error);
            }
            dispatch({ type: 'SET_LOADING', payload: false });
            abortControllerRef.current = null;
        }
    };

    const onUsage = () => {
        handleSendMessageWithContent(`Reply in ${navigator.language} language: How does the ${selectedNode?.[0]?.type} node work? I need its official usage guide.`)
    }

    const onParameters = () => {
        handleSendMessageWithContent(`Reply in ${navigator.language} language: Show me the technical specifications for the ${selectedNode?.[0].type} node's inputs and outputs.`)
    }

    const getDownstreamSubgraphExt = () => {
        const nodeTypeSet = new Set<string>();
        
        function findUpstreamNodes(node: any, depth: number) {
            if (!node || depth >= 1) return;
            
            if (node.inputs) {
                for (const input of Object.values(node.inputs)) {
                    const linkId = (input as any).link;
                    if (linkId && app.graph.links[linkId]) {
                        const originId = app.graph.links[linkId].origin_id;
                        const originNode = app.graph._nodes_by_id[originId];
                        if (originNode) {
                            nodeTypeSet.add(originNode.type);
                            findUpstreamNodes(originNode, depth + 1);
                        }
                    }
                }
            }
        }
    
        if (!!selectedNode[0]) {
            findUpstreamNodes(selectedNode[0], 0);
            return [{"type": "upstream_node_types", "data": Array.from(nodeTypeSet)}];
        }
    
        return null;
    }

    const onDownstreamNodes = () => {
        handleSendMessageWithIntent('downstream_subgraph_search', getDownstreamSubgraphExt())
    }

    // Utility function to update localStorage cache for messages
    const updateMessagesCache = (messages: Message[]) => {
        if (state.sessionId) {
            localStorage.setItem(`messages_${state.sessionId}`, JSON.stringify(messages));
        }
    };

    const handleAddMessage = (message: Message) => {
        console.log('[WorkflowChat] Adding new message:', message);
        const updatedMessages = [...state.messages, message];
        dispatch({ type: 'ADD_MESSAGE', payload: message });
        
        // Update the localStorage cache with the new message
        updateMessagesCache(updatedMessages);
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        setIsResizing(true);
        e.preventDefault();
    };

    const handleMouseUp = () => {
        setIsResizing(false);
    };

    const handleUploadImages = (files: FileList) => {
        const newImages = Array.from(files).map(file => ({
            id: Math.random().toString(36).substr(2, 9),
            file,
            preview: URL.createObjectURL(file)
        }));
        setUploadedImages(prev => [...prev, ...newImages]);
    };

    const handleRemoveImage = (imageId: string) => {
        setUploadedImages(prev => {
            const newImages = prev.filter(img => img.id !== imageId);
            return newImages;
        });
    };

    React.useEffect(() => {
        return () => {
            uploadedImages.forEach(image => URL.revokeObjectURL(image.preview));
        };
    }, [uploadedImages]);

    useEffect(() => {
        if (triggerUsage && onUsageTriggered && activeTab === 'chat') {
            handleSendMessageWithIntent('node_explain');
            onUsageTriggered();
        }
    }, [triggerUsage, activeTab]);

    // 获取公告内容
    useEffect(() => {
        if (!visible || activeTab !== 'chat') return;
        
        const fetchAnnouncement = async () => {
            try {
                // 检查今天是否已经显示过公告
                const today = new Date().toDateString();
                const lastShownDate = localStorage.getItem('announcementLastShownDate');
                
                // 如果今天没有显示过公告，则显示
                if (lastShownDate !== today) {
                    const message = await WorkflowChatAPI.fetchAnnouncement();
                    if (message && message.trim() !== '') {
                        setAnnouncement(message);
                        setShowAnnouncement(true);
                        // 记录今天的日期
                        localStorage.setItem('announcementLastShownDate', today);
                    }
                }
            } catch (error) {
                console.error('Error fetching announcement:', error);
            }
        };
        
        fetchAnnouncement();
    }, [visible, activeTab]);

    // 关闭公告
    const handleCloseAnnouncement = () => {
        setShowAnnouncement(false);
    };

    // Handle tab change
    const handleTabChange = (tab: TabType) => {
        dispatch({ type: 'SET_ACTIVE_TAB', payload: tab });
    };

    // Initialize the parameter debug tab component with lazy loading
    const parameterDebugTabComponent = React.useMemo(() => (
        <ParameterDebugTab />
    ), []);

    if (!visible) return null;

    return (
        <div 
            className="flex flex-col h-full w-full bg-white relative"
            style={{ 
                display: visible ? 'flex' : 'none'
            }}
        >
            <div
                className="absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-gray-300"
            />
            
            <div className="flex h-full flex-col">
                <ChatHeader 
                    onClose={onClose}
                    onClear={handleClearMessages}
                    hasMessages={messages.length > 0}
                    title={`ComfyUI-Copilot`}
                />
                
                {/* Tab navigation */}
                <div className="flex border-b border-gray-200 mt-2">
                    <TabButton 
                        active={activeTab === 'chat'}
                        onClick={() => handleTabChange('chat')}
                    >
                        Chat
                    </TabButton>
                    <TabButton 
                        active={activeTab === 'parameter-debug'}
                        onClick={() => handleTabChange('parameter-debug')}
                    >
                        GenLab
                    </TabButton>
                </div>
                
                {/* 将公告移到 ChatHeader 下方和Tab导航下方 */}
                {showAnnouncement && announcement && activeTab === 'chat' && (
                    <Announcement 
                        message={announcement} 
                        onClose={handleCloseAnnouncement} 
                    />
                )}
                
                {/* Tab content - Both tabs are mounted but only the active one is displayed */}
                {/* <div 
                    className='flex-1 overflow-y-auto p-4 scroll-smooth h-0'
                    style={{ display: activeTab === 'chat' ? 'block' : 'none' }}
                    ref={messageDivRef}
                > */}
                    <MessageList 
                        messages={messages}
                        latestInput={latestInput}
                        onOptionClick={handleOptionClick}
                        installedNodes={installedNodes}
                        onAddMessage={handleAddMessage}
                        loading={loading}
                        isActive={activeTab === 'chat'}
                    />
                {/* </div> */}

                <div 
                    className="border-t px-4 py-3 border-gray-200 bg-white sticky bottom-0"
                    style={{ display: activeTab === 'chat' ? 'block' : 'none' }}
                >
                    {/* {selectedNode && (
                        <SelectedNodeInfo 
                            nodeInfo={selectedNode}
                            onSendWithIntent={handleSendMessageWithIntent}
                            loading={loading}
                            onSendWithContent={handleSendMessageWithContent}
                        />
                    )} */}

                    <ChatInput 
                        input={input}
                        loading={loading}
                        onChange={handleMessageChange}
                        onSend={handleSendMessage}
                        onKeyPress={handleKeyPress}
                        onUploadImages={handleUploadImages}
                        uploadedImages={uploadedImages}
                        onRemoveImage={handleRemoveImage}
                        selectedModel={selectedModel}
                        onModelChange={setSelectedModel}
                        onStop={handleStop}
                    />
                </div>

                {/* ParameterDebugTab - Always mounted but conditionally displayed */}
                <div 
                    className="flex-1 flex flex-col h-0"
                    style={{ display: activeTab === 'parameter-debug' ? 'flex' : 'none' }}
                >
                    {parameterDebugTabComponent}
                </div>
            </div>
        </div>
    );
}