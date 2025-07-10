// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import { Message } from "../../types/types";
import { UserMessage } from "./messages/UserMessage";
import { AIMessage } from "./messages/AIMessage";
// Import as components to be used directly, not lazy-loaded
import { LoadingMessage } from "./messages/LoadingMessage";
import { generateUUID } from "../../utils/uuid";
import { app } from "../../utils/comfyapp";
import { addNodeOnGraph } from "../../utils/graphUtils";
import { lazy, Suspense, useEffect, useLayoutEffect, useRef, useState } from "react";

// Define types for ext items to avoid implicit any
interface ExtItem {
  type: string;
  data?: any;
}

interface NodeMap {
    [key: string | number]: any;
}

interface NodeWithPosition {
    id: number;
    type: string;
    pos: [number, number];
}

const enum LoadMoreStatus {
    USED = 'used',
    NOT_USED = 'not_used'
}
interface LoadMoreButtonProps {
    id?: string
    buttonType?: 'loadmore';
    buttonStatus?: LoadMoreStatus
}

interface MessageListProps {
    messages: Message[];
    onOptionClick: (option: string) => void;
    latestInput: string;
    installedNodes: any[];
    onAddMessage: (message: Message) => void;
    loading?: boolean;
    isActive?: boolean;
}

const getAvatar = (name?: string) => {
    return `https://ui-avatars.com/api/?name=${name || 'User'}&background=random`;
};

type FinallyMessageProps = Message | LoadMoreButtonProps

// Use lazy loading for components that are conditionally rendered
const LazyWorkflowOption = lazy(() => import('./messages/WorkflowOption').then(m => ({ default: m.WorkflowOption })));
const LazyNodeSearch = lazy(() => import('./messages/NodeSearch').then(m => ({ default: m.NodeSearch })));
const LazyDownstreamSubgraphs = lazy(() => import('./messages/DownstreamSubgraphs').then(m => ({ default: m.DownstreamSubgraphs })));
const LazyNodeInstallGuide = lazy(() => import('./messages/NodeInstallGuide').then(m => ({ default: m.NodeInstallGuide })));

// 默认显示3轮回答，也就是找到列表最后的3条role是ai的数据
const DEFAULT_COUNT = 3;

export function MessageList({ messages, latestInput, onOptionClick, installedNodes, onAddMessage, loading, isActive }: MessageListProps) {
    const [currentIndex, setCurrentIndex] = useState<number>(0)
    const [currentMessages, setCurrentMessages] = useState<FinallyMessageProps[]>([])

    const scrollRef = useRef<HTMLDivElement>(null)
    const lastMessagesCount = useRef<number>(0)
    const currentScrollHeight = useRef<number>(0) 
    const isLoadHistory = useRef<boolean>(false)

    const onFinishLoad = () => {
        if (!!scrollRef?.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }

    // 渲染对应的消息组件
    const renderMessage = (message: Message) => {
        // 移除频繁的日志输出
        // console.log('[MessageList] Rendering message:', message);
        
        if (message.role === 'user') {
            return <UserMessage 
                key={message.id} 
                content={message.content} 
                trace_id={message.trace_id} 
            />;
        }

        if (message.role === 'ai' || message.role === 'tool') {
            const avatar = getAvatar(message.role);
            
            try {
                const response = JSON.parse(message.content);
                // 移除频繁的日志输出
                // console.log('[MessageList] Parsed message content:', response);
                
                // 获取扩展类型
                const workflowExt = response.ext?.find((item: ExtItem) => item.type === 'workflow');
                const nodeExt = response.ext?.find((item: ExtItem) => item.type === 'node');
                const downstreamSubgraphsExt = response.ext?.find((item: ExtItem) => item.type === 'downstream_subgraph_search');
                const nodeInstallGuideExt = response.ext?.find((item: ExtItem) => item.type === 'node_install_guide');
                
                // 移除频繁的日志输出
                // console.log('[MessageList] Found extensions:', {
                //     workflowExt,
                //     nodeExt,
                //     nodeRecommendExt,
                //     downstreamSubgraphsExt,
                //     nodeInstallGuideExt
                // });

                // 根据扩展类型添加对应组件
                let ExtComponent = null;
                if (workflowExt) {
                    ExtComponent = (
                        <Suspense fallback={<div>Loading...</div>}>
                            <LazyWorkflowOption
                                content={message.content}
                                name={message.name}
                                avatar={avatar}
                                latestInput={latestInput}
                                installedNodes={installedNodes}
                                onAddMessage={onAddMessage}
                                onFinishLoad={onFinishLoad}
                            />
                        </Suspense>
                    );
                } else if (nodeExt) {
                    ExtComponent = (
                        <Suspense fallback={<div>Loading...</div>}>
                            <LazyNodeSearch
                                content={message.content}
                                name={message.name}
                                avatar={avatar}
                                installedNodes={installedNodes}
                                onFinishLoad={onFinishLoad}
                            />
                        </Suspense>
                    );
                } else if (downstreamSubgraphsExt) {
                    const dsExtComponent = (
                        <Suspense fallback={<div>Loading...</div>}>
                            <LazyDownstreamSubgraphs
                                content={message.content}
                                name={message.name}
                                avatar={avatar}
                                onAddMessage={onAddMessage}
                                onFinishLoad={onFinishLoad}
                            />
                        </Suspense>
                    );
                    
                    // If this is specifically from an intent button click (not regular message parsing)
                    if (message.metadata?.intent === 'downstream_subgraph_search') {
                        // Return the AIMessage with the extComponent
                        return (
                            <AIMessage 
                                key={message.id}
                                content={message.content}
                                name={message.name}
                                avatar={avatar}
                                format={message.format}
                                onOptionClick={onOptionClick}
                                extComponent={dsExtComponent}
                                metadata={message.metadata}
                            />
                        );
                    }
                    
                    // For normal detection from ext, use the ExtComponent directly
                    ExtComponent = dsExtComponent;
                } else if (nodeInstallGuideExt) {
                    ExtComponent = (
                        <Suspense fallback={<div>Loading...</div>}>
                            <LazyNodeInstallGuide
                                content={message.content}
                                onLoadSubgraph={() => {
                                    if (message.metadata?.pendingSubgraph) {
                                        const selectedNode = Object.values(app.canvas.selected_nodes)[0] as any;
                                        if (selectedNode) {
                                            // 直接调用 DownstreamSubgraphs 中的 loadSubgraphToCanvas
                                            const node = message.metadata.pendingSubgraph;
                                            const nodes = node.json.nodes;
                                            const links = node.json.links;
                                            
                                            const entryNode = nodes.find((n: any) => n.id === 0);
                                            const entryNodeId = entryNode?.id;

                                            const nodeMap: NodeMap = {};
                                            if (entryNodeId) {
                                                nodeMap[entryNodeId] = selectedNode;
                                            }
                                            
                                            // 创建其他所有节点
                                            app.canvas.emitBeforeChange();
                                            try {
                                                for (const node of nodes as NodeWithPosition[]) {
                                                    if (node.id !== entryNodeId) {
                                                        const posEntryOld = entryNode?.pos || [0, 0];
                                                        const posEntryNew = selectedNode._pos || [0, 0];
                                                        const nodePosNew = [
                                                            node.pos[0] + posEntryNew[0] - posEntryOld[0], 
                                                            node.pos[1] + posEntryNew[1] - posEntryOld[1]
                                                        ];
                                                        nodeMap[node.id] = addNodeOnGraph(node.type, {pos: nodePosNew});
                                                    }
                                                }
                                            } finally {
                                                app.canvas.emitAfterChange();
                                            }

                                            // 处理所有连接
                                            for (const link of links) {
                                                const origin_node = nodeMap[link['origin_id']];
                                                const target_node = nodeMap[link['target_id']];
                                                
                                                if (origin_node && target_node) {
                                                    origin_node.connect(
                                                        link['origin_slot'], 
                                                        target_node, 
                                                        link['target_slot']
                                                    );
                                                }
                                            }
                                        } else {
                                            alert("Please select a upstream node first before adding a subgraph.");
                                        }
                                    } else if (message.metadata?.pendingWorkflow) {
                                        const workflow = message.metadata.pendingWorkflow;
                                        const optimizedParams = message.metadata.optimizedParams;
                                       
                                        // 支持不同格式的工作流
                                        if(workflow.nodes) {
                                            app.loadGraphData(workflow);
                                        } else {
                                            app.loadApiJson(workflow);
                                            // 获取所有节点，并且优化排布
                                            const node_ids = Object.keys(workflow);
                                            
                                            // 获取第一个节点作为基准位置
                                            const firstNodeId = Object.keys(app.graph._nodes_by_id)[0];
                                            const firstNode = app.graph._nodes_by_id[firstNodeId];
                                            const base_x = firstNode ? firstNode.pos[0] : 0;
                                            const base_y = firstNode ? firstNode.pos[1] : 0;
                                            
                                            // 布局参数
                                            const base_size_x = 250;
                                            const base_size_y = 60;
                                            const param_y = 20;
                                            const align = 60;
                                            const align_y = 50;
                                            const max_size_y = 1000;
                                            
                                            let last_start_x = base_x;
                                            let last_start_y = base_y;
                                            let tool_size_y = 0;
                                            
                                            for(const node_id of node_ids) {
                                                const node = app.graph._nodes_by_id[node_id];
                                                if(node) {
                                                    // 检查是否需要换列
                                                    if (tool_size_y > max_size_y) {
                                                        last_start_x += base_size_x + align;
                                                        tool_size_y = 0;
                                                        last_start_y = base_y;
                                                    }

                                                    // 根据参数计算节点的高度
                                                    const inputCount = node.inputs ? node.inputs.length : 0;
                                                    const outputCount = node.outputs ? node.outputs.length : 0;
                                                    const widgetCount = node.widgets ? node.widgets.length : 0;
                                                    const param_count = Math.max(inputCount, outputCount) + widgetCount;
                                                    
                                                    const size_y = param_y * param_count + base_size_y;
                                                    
                                                    // 设置节点大小和位置
                                                    node.size[0] = base_size_x;
                                                    node.size[1] = size_y;
                                                    node.pos[0] = last_start_x;
                                                    node.pos[1] = last_start_y;

                                                    tool_size_y += size_y + align_y;
                                                    last_start_y += size_y + align_y;
                                                }
                                            }
                                        }
                                        
                                        // 应用优化参数
                                        for (const [nodeId, nodeName, paramIndex, paramName, value] of optimizedParams) {
                                            const widgets = app.graph._nodes_by_id[nodeId].widgets;
                                            for (const widget of widgets) {
                                                if (widget.name === paramName) {
                                                    widget.value = value;
                                                }
                                            }
                                        }
                                        app.graph.setDirtyCanvas(false, true);
                                        // Add success message
                                        const successMessage = {
                                            id: generateUUID(),
                                            role: 'tool',
                                            content: JSON.stringify({
                                                text: 'The workflow has been successfully loaded to the canvas',
                                                ext: []
                                            }),
                                            format: 'markdown',
                                            name: 'Assistant'
                                        };
                                        onAddMessage?.(successMessage);
                                    }
                                }}
                                onFinishLoad={onFinishLoad}
                            />
                        </Suspense>
                    );
                }

                // 如果有response.text，使用AIMessage渲染
                if (response.text || ExtComponent) {
                    return (
                        <AIMessage 
                            key={message.id}
                            content={message.content}
                            name={message.name}
                            avatar={avatar}
                            format={message.format}
                            onOptionClick={onOptionClick}
                            extComponent={ExtComponent}
                            metadata={message.metadata}
                        />
                    );
                }

                // 如果没有response.text但有扩展组件，直接返回扩展组件
                if (ExtComponent) {
                    return ExtComponent;
                }

                // 默认返回AIMessage
                return (
                    <AIMessage 
                        key={message.id}
                        content={message.content}
                        name={message.name}
                        avatar={avatar}
                        format={message.format}
                        onOptionClick={onOptionClick}
                        metadata={message.metadata}
                    />
                );
            } catch (error) {
                console.error('[MessageList] Error parsing message content:', error);
                // 如果解析JSON失败,使用AIMessage
                console.error('解析JSON失败', message.content);
                return (
                    <AIMessage 
                        key={message.id}
                        content={message.content}
                        name={message.name}
                        avatar={avatar}
                        format={message.format}
                        onOptionClick={onOptionClick}
                        metadata={message.metadata}
                    />
                );
            }
        }

        return null;
    }

    const renderLoadMore = (message: LoadMoreButtonProps) => {
        const isNotUsed = message?.buttonStatus === LoadMoreStatus.NOT_USED
        return <div 
            key={message.id}
            className='flex justify-center items-center'
        >
            {
                isNotUsed ? <button 
                    className='w-full h-[24px] text-gray-700 text-xs bg-gray-50 hover:!bg-gray-200 px-2 py-1 rounded-md'
                    onClick={handleLoadMore}
                >
                    Load more
                </button> : <div className='w-full h-[24px] bg-transparent' />
            }
        </div>
    }

    function isLoadMoreButtonProps(item: any): item is LoadMoreButtonProps {
        return item && typeof item === 'object' && item.buttonType === 'loadmore';
    }

    const handleLoadMore = () => {
        isLoadHistory.current = true;
        setCurrentIndex(index => index + 1);
    }

    useEffect(() => {
        let list: FinallyMessageProps[] = []
        if (lastMessagesCount.current > 0 && lastMessagesCount.current < messages.length) {
            list = messages.slice(lastMessagesCount.current)
            if (messages[lastMessagesCount.current].role === 'user') {
                list.unshift({  
                    id: `${messages[lastMessagesCount.current].id}_loadmore`,
                    buttonType: 'loadmore',
                    buttonStatus: LoadMoreStatus.USED
                })
            }
            setCurrentMessages(pre => [...pre, ...list]);
        } else {
            let count = 0;
            let endIndex = messages?.length
            for (let i = messages?.length - 1; i >= 0; i--) {
                if (messages[i].role === 'ai' || i === 0) {
                    if (count > DEFAULT_COUNT + currentIndex) {
                        list.unshift({
                            id: `${messages[i].id}_loadmore`,
                            buttonType: 'loadmore',
                            buttonStatus: LoadMoreStatus.NOT_USED
                        })
                        break;
                    } else {
                        count++;    
                        if (list?.length > 0) {
                            list.unshift({
                                id: `${messages[i].id}_loadmore`,
                                buttonType: 'loadmore',
                                buttonStatus: LoadMoreStatus.USED
                            })
                        }
                        list = [
                            ...messages?.slice(Math.min(endIndex, i === 0 ? i : i + 1), endIndex + 1), 
                            ...list
                        ];
                        endIndex = i;
                    }
                }
            }
            setCurrentMessages(list)
        }
        lastMessagesCount.current = messages.length
    }, [messages, currentIndex])

    useLayoutEffect(() => {
        if (!!scrollRef?.current) {
            if (isLoadHistory.current) {
                // 加载历史数据需要修改scrolltop保证当前视图不变
                scrollRef.current.scrollTop = scrollRef.current.scrollHeight - currentScrollHeight.current
                isLoadHistory.current = false
            } else {
                scrollRef.current.scrollTop = scrollRef.current.scrollHeight
            }
            currentScrollHeight.current = scrollRef.current.scrollHeight
        }
    }, [currentMessages])

    return (
        <div 
            className='flex-1 flex-col overflow-y-auto p-4 h-0'
            ref={scrollRef} 
            style={{
                display: isActive ? 'block' : 'none',
            }}
        >
            {
                currentMessages?.map((message) => !!message && (isLoadMoreButtonProps(message) ? renderLoadMore(message as LoadMoreButtonProps) : renderMessage(message as Message)))
            }
            {loading && <LoadingMessage />}
        </div>
    );
} 