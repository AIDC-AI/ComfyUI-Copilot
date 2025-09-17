import { app } from "../../../utils/comfyapp";
import { ChatResponse, Workflow } from "../../../types/types";
import { WorkflowChatAPI } from "../../../apis/workflowChatApi";
import { generateUUID } from "../../../utils/uuid";
import { useEffect, useState } from "react";
import { Tooltip } from 'antd';
import { ACCEPT_EVENT } from "../../ui/StartPopView";
interface WorkflowOptionProps {
    content: string;
    name?: string;
    avatar: string;
    latestInput: string;
    installedNodes: any[];
    onAddMessage?: (message: any) => void;
}

interface NodeInfo {
    name: string;
    github_url: string;
    [key: string]: any;
}

export function WorkflowOption({ content, name = 'Assistant', avatar, latestInput, installedNodes, onAddMessage }: WorkflowOptionProps) {
    // const response = JSON.parse(content) as ChatResponse;
    // const workflows = response.ext?.find(item => item.type === 'workflow')?.data || [];
    const [loadingWorkflows, setLoadingWorkflows] = useState<Record<string, boolean>>({});
    const [response, setResponse] = useState<ChatResponse | null>(null);
    const [workflows, setWorkflows] = useState<Workflow[]>([]);

    useEffect(() => {
        const _response = JSON.parse(content) as ChatResponse;
        setResponse(_response);
        setWorkflows(_response.ext?.find(item => item.type === 'workflow')?.data || []);
    }, [content])

    const handleAcceptWorkflow = async (workflow: Workflow) => {
        if (!workflow.id) {
            console.error('No workflow id provided');
            return;
        }

        // 将workflow.id转换为字符串，确保可以作为对象的键
        const workflowId = String(workflow.id);

        // 防止重复点击
        if (loadingWorkflows[workflowId]) {
            return;
        }

        // 设置当前工作流为加载状态
        setLoadingWorkflows(prev => ({
            ...prev,
            [workflowId]: true
        }));

        // 发送埋点事件
        WorkflowChatAPI.trackEvent({
            event_type: 'workflow_accept',
            message_type: 'workflow',
            message_id: response?.message_id,
            data: {
                workflow_id: workflow.id,
                workflow_name: workflow.name
            }
        });

        // 发送accept事件，每日首次accept会弹出star框
        window.dispatchEvent(new CustomEvent(ACCEPT_EVENT, {

        }));
        
        try {
            // 获取优化后的工作流
            const optimizedResult = await WorkflowChatAPI.getOptimizedWorkflow(
                workflow.id,
                latestInput
            );

            // 加载优化后的工作流
            if (optimizedResult.workflow) {
                // 检查是否需要安装节点
                const nodeTypes = new Set<string>();
                if(optimizedResult.workflow.nodes) {
                    for (const node of optimizedResult.workflow.nodes) {
                        nodeTypes.add(node.type);
                    }
                } else {
                    for (const node of Object.values(optimizedResult.workflow)) {
                        nodeTypes.add((node as any).class_type);
                    }
                }
                
                const missingNodeTypes = Array.from(nodeTypes).filter(
                    type => !installedNodes.includes(type)
                );
                
                console.log('[WorkflowOption] Missing node types:', missingNodeTypes);

                if (missingNodeTypes.length > 0) {
                    try {
                        console.log('[WorkflowOption] Fetching info for missing nodes');
                        const nodeInfos = await WorkflowChatAPI.batchGetNodeInfo(missingNodeTypes);
                        console.log('[WorkflowOption] Received node infos:', nodeInfos);
                        
                        const messageContent = {
                            text: ``,
                            ext: [{
                                type: 'node_install_guide',
                                data: nodeInfos.map((info: NodeInfo) => ({
                                    name: info.name,
                                    repository_url: info.github_url
                                }))
                            }]
                        };

                        const aiMessage = {
                            id: generateUUID(),
                            role: 'ai',
                            content: JSON.stringify(messageContent),
                            format: 'markdown',
                            name: 'Assistant',
                            metadata: {
                                pendingWorkflow: optimizedResult.workflow,
                                optimizedParams: optimizedResult.optimized_params
                            }
                        };

                        onAddMessage?.(aiMessage);
                    } catch (error) {
                        console.error('[WorkflowOption] Error fetching node info:', error);
                        alert('Error checking required nodes. Please try again.');
                    } finally {
                        // 无论成功或失败，重置加载状态
                        setLoadingWorkflows(prev => ({
                            ...prev,
                            [workflowId]: false
                        }));
                    }
                    return;
                }

                // 如果所有节点都已安装，直接加载工作流
                loadWorkflow(optimizedResult.workflow, optimizedResult.optimized_params);
            }
        } catch (error) {
            console.error('Failed to optimize workflow:', error);
            alert('Failed to optimize workflow. Please try again.');
        } finally {
            // 无论成功或失败，重置加载状态
            setLoadingWorkflows(prev => ({
                ...prev,
                [workflowId]: false
            }));
        }
    };

    const loadWorkflow = (workflow: any, optimizedParams: any[]) => {
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

        // 应用优化后的参数 [节点id，节点名称，参数id，参数名称，参数默认值]
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
    };
    
    const loadWorkflowItem = (workflow: Workflow, index: number) => {
        const workflowId = workflow.id ? String(workflow.id) : '';
        return (
            <div key={index} className="flex items-center gap-4 p-4 rounded-lg border border-gray-200 hover:bg-gray-50">
                {workflow.image && (
                    <img
                        src={workflow.image}
                        alt={workflow.name}
                        className="w-14 h-14 object-cover rounded-lg"
                        onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.onerror = null; // 防止循环触发
                            target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='56' viewBox='0 0 56 56' fill='none'%3E%3Crect width='56' height='56' fill='%23F3F4F6'/%3E%3Cpath d='M28 28C30.2091 28 32 26.2091 32 24C32 21.7909 30.2091 20 28 20C25.7909 20 24 21.7909 24 24C24 26.2091 25.7909 28 28 28Z' fill='%239CA3AF'/%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M18.7253 37.6307C19.8278 35.1533 22.6897 33.6 26 33.6H30C33.3103 33.6 36.1722 35.1533 37.2747 37.6307C37.6419 38.4561 37.0611 39.2 36.1694 39.2H19.8306C18.9389 39.2 18.3581 38.4561 18.7253 37.6307Z' fill='%239CA3AF'/%3E%3C/svg%3E";
                        }}
                    />
                )}
                <div className="flex-1 break-words flex flex-col h-[4.5rem] justify-between">
                    <div>
                        <h3 className="font-medium text-sm line-clamp-2 h-10 overflow-hidden">{workflow.name}</h3>
                    </div>
                    <div className="flex justify-between items-center mt-1">
                        {workflow.description && (
                            <div className="relative group">
                                <div className="w-5 h-5 flex items-center justify-center text-gray-500 cursor-help">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
                                    </svg>
                                </div>
                                <div className="absolute bottom-full left-0 mb-2 hidden group-hover:!block">
                                    <div className="bg-gray-900 text-white text-xs rounded-md py-2 px-3 min-w-[400px] whitespace-normal break-words">
                                        {workflow.description}
                                    </div>
                                </div>
                            </div>
                        )}
                        <button
                            onClick={() => handleAcceptWorkflow(workflow)}
                            disabled={loadingWorkflows[workflowId]}
                            className={`px-3 py-1.5 ${loadingWorkflows[workflowId] 
                                ? 'bg-gray-400 cursor-not-allowed' 
                                : 'bg-blue-500 hover:bg-blue-600'} text-white rounded-md transition-colors text-xs`}
                        >
                            {loadingWorkflows[workflowId] ? 'Loading...' : 'Accept'}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const loadWorkflowItemV2 = (workflow: Workflow, index: number) => {
        const workflowId = workflow.id ? String(workflow.id) : '';
        const isAIGenerated = workflow?.source === 'AI Generated'
        return (
            <div 
                key={index} 
                className={`relative flex flex-col items-center gap-4 p-2 rounded-lg border ${isAIGenerated ? 'shadow-[0_0_12px_2px_#3b82f6] shadow-[0_0_0_4px_rgba(59,130,246,0.15)]' : 'border-gray-200'} hover:bg-gray-50`}
            >
                {
                    isAIGenerated && <div className='absolute left-1/2 top-[-12px] -translate-x-1/2 rounded-lg flex bg-white'>
                        <svg viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="25237" width="24" height="24"><path d="M938.656 256A170.656 170.656 0 0 0 768 85.344H256A170.656 170.656 0 0 0 85.344 256v512A170.656 170.656 0 0 0 256 938.656h512A170.656 170.656 0 0 0 938.656 768V256zM256 170.656h512l6.368 0.256A85.344 85.344 0 0 1 853.312 256v512l-0.224 6.4A85.344 85.344 0 0 1 768 853.312H256l-6.336-0.256A85.344 85.344 0 0 1 170.656 768V256l0.224-6.368A85.344 85.344 0 0 1 256 170.656z" p-id="25238" fill="#1296db"></path><path d="M633.12 718.464h-95.392l-34.368-95.68h-160.288l-34.336 95.68H213.344l154.56-419.808h110.656l154.56 419.808z m-209.888-333.888l-61.056 177.696h120.192l-59.136-177.696z" p-id="25239" fill="#1296db"></path><path d="M682.656 298.656m0 0l85.344 0q0 0 0 0l0 426.656q0 0 0 0l-85.344 0q0 0 0 0l0-426.656q0 0 0 0Z" p-id="25240" fill="#1296db"></path></svg>
                    </div>
                }
                <div className='flex flex-row'>
                    <h3 className="flex-1 font-medium text-sm line-clamp-2 break-all h-10 overflow-hidden">{workflow.name}</h3>
                    <div className='flex items-start'>
                        {workflow.description && <Tooltip
                            arrow={false}
                            placement="top" 
                            title={<div className="bg-gray-900 text-white text-xs rounded-md py-2 px-3 min-w-[400px] whitespace-normal break-words">
                                {workflow.description}
                            </div>}
                        >
                            <div className="w-5 h-5 flex items-center justify-center text-gray-500 cursor-help">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
                                </svg>
                            </div>
                        </Tooltip>}
                    </div>
                </div>
                <div className='aspect-[3/4] rounded-lg overflow-hidden flex-1 w-full'>
                    {
                        !!workflow.image ? <img
                            src={workflow.image}
                            alt={workflow.name}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.onerror = null; // 防止循环触发
                                target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='56' height='56' viewBox='0 0 56 56' fill='none'%3E%3Crect width='56' height='56' fill='%23F3F4F6'/%3E%3Cpath d='M28 28C30.2091 28 32 26.2091 32 24C32 21.7909 30.2091 20 28 20C25.7909 20 24 21.7909 24 24C24 26.2091 25.7909 28 28 28Z' fill='%239CA3AF'/%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M18.7253 37.6307C19.8278 35.1533 22.6897 33.6 26 33.6H30C33.3103 33.6 36.1722 35.1533 37.2747 37.6307C37.6419 38.4561 37.0611 39.2 36.1694 39.2H19.8306C18.9389 39.2 18.3581 38.4561 18.7253 37.6307Z' fill='%239CA3AF'/%3E%3C/svg%3E";
                            }}
                        /> : <div className="w-full h-full flex items-center justify-center">
                            <svg viewBox="0 0 1026 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="1875" width="98" height="98"><path d="M0.003166 0v1024h1024V0H0.003166z m962.692789 61.286783v566.902743l-120.857537-118.426494-186.638683 137.466255-287.435012-237.138993L61.28995 705.410873V61.286783h901.406005zM61.28995 962.692788v-172.195431l309.661685-298.34406 282.164349 232.746773 183.104479-134.89221 126.49592 123.962734v248.722194H61.28995z" fill="#8a8a8a" p-id="1876"></path><path d="M757.03794 397.199641h0.960159c63.411392 0 118.263062-53.605506 119.733945-117.057756 1.470883-63.901686-51.337895-119.958663-115.321296-122.410134l-4.330933-0.081716c-31.011112 0-61.817935 13.1358-84.555332 36.016199-22.635252 22.819112-35.505476 53.666793-35.301187 84.616619 0.490294 63.942544 54.892529 118.406065 118.814644 118.916788z m-39.999841-160.346653a59.570753 59.570753 0 0 1 42.900748-17.875312h0.143003c30.214384 1.164449 57.098853 29.621945 56.38384 59.734184-0.694584 30.47996-28.00806 57.200998-58.447162 57.200998v30.643391l-0.449436-30.643391c-30.132668-0.245147-57.773007-27.926344-57.997726-58.079442-0.122574-14.749686 6.230823-29.683232 17.466733-40.980428z" fill="#8a8a8a" p-id="1877"></path></svg>
                        </div>
                    }
                </div>
                <button
                    onClick={() => handleAcceptWorkflow(workflow)}
                    disabled={loadingWorkflows[workflowId]}
                    className={`w-full px-3 py-1 ${loadingWorkflows[workflowId] 
                        ? 'bg-[#d2d2d2] cursor-not-allowed' 
                        : 'bg-[#ffffff] hover:bg-[#eee]'} text-black rounded-lg text-xs`}
                >
                    {loadingWorkflows[workflowId] ? 'Loading...' : 'Accept'}
                </button>
            </div>
        );
    }

    return (
        // <BaseMessage avatar={avatar} name={name}>
            <div className="space-y-3 flex justify-center">
                {workflows.length > 0 && (
                    <div className="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-4">
                        {workflows.map((workflow: Workflow, index: number) => loadWorkflowItemV2(workflow, index))}
                    </div>
                )}
            </div>
        // </BaseMessage>
    );
} 