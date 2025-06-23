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
import React, { lazy, Suspense } from "react";

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

interface MessageListProps {
    messages: Message[];
    onOptionClick: (option: string) => void;
    latestInput: string;
    installedNodes: any[];
    onAddMessage: (message: Message) => void;
    loading?: boolean;
}

const getAvatar = (name?: string) => {
    return `https://ui-avatars.com/api/?name=${name || 'User'}&background=random`;
};

// Use lazy loading for components that are conditionally rendered
const LazyWorkflowOption = lazy(() => import('./messages/WorkflowOption').then(m => ({ default: m.WorkflowOption })));
const LazyNodeSearch = lazy(() => import('./messages/NodeSearch').then(m => ({ default: m.NodeSearch })));
const LazyDownstreamSubgraphs = lazy(() => import('./messages/DownstreamSubgraphs').then(m => ({ default: m.DownstreamSubgraphs })));
const LazyNodeInstallGuide = lazy(() => import('./messages/NodeInstallGuide').then(m => ({ default: m.NodeInstallGuide })));
const LazyDebugGuide = lazy(() => import('./messages/DebugGuide').then(m => ({ default: m.DebugGuide })));

export function MessageList({ messages, latestInput, onOptionClick, installedNodes, onAddMessage, loading }: MessageListProps) {
    // 使用useMemo缓存renderMessage函数
    const renderMessage = React.useMemo(() => (message: Message) => {
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
                
                // 检查是否是工作流成功加载的消息
                const isWorkflowSuccessMessage = response.text === 'The workflow has been successfully loaded to the canvas';
                
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
                            />
                        </Suspense>
                    );
                } else if (isWorkflowSuccessMessage) {
                    // 使用DebugGuide组件来处理工作流成功加载的消息
                    ExtComponent = (
                        <Suspense fallback={<div>Loading...</div>}>
                            <LazyDebugGuide
                                content={message.content}
                                name={message.name}
                                avatar={avatar}
                                onAddMessage={onAddMessage}
                            />
                        </Suspense>
                    );
                }

                // 如果是工作流成功消息，直接返回DebugGuide组件
                if (isWorkflowSuccessMessage && ExtComponent) {
                    return ExtComponent;
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
    }, [installedNodes, onOptionClick, onAddMessage, latestInput]); // Added dependencies that are used inside the function

    // 使用useMemo缓存消息列表
    const messageElements = React.useMemo(() => 
        messages?.map(renderMessage),
        [messages, renderMessage]
    );

    return (
        <div className="flex flex-col gap-4 w-full">
            {messageElements}
            {loading && <LoadingMessage />}
        </div>
    );
} 