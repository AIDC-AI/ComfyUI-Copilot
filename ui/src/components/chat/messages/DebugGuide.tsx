import { useEffect, useMemo, useState } from 'react';
import { BaseMessage } from './BaseMessage';
import { generateUUID } from '../../../utils/uuid';
import { queuePrompt } from '../../../utils/queuePrompt';
import { app } from '../../../utils/comfyapp';
import { WorkflowChatAPI } from '../../../apis/workflowChatApi';
import RestoreCheckpoint from '../../ui/RestoreCheckpoint';
import { useChatContext } from '../../../context/ChatContext';

interface DebugGuideProps {
    content: string;
    name?: string;
    avatar: string;
    onAddMessage?: (message: any) => void;
    onUpdateMessage?: (message: any) => void;
    messageId?: string;  // Add messageId prop to track the current message
}

export function DebugGuide({ content, name = 'Assistant', avatar, onAddMessage, onUpdateMessage, messageId }: DebugGuideProps) {
    const { dispatch, abortControllerRef } = useChatContext();
    const [isDebugging, setIsDebugging] = useState(false);
    const [streamingText, setStreamingText] = useState('');
    const [showStreamingMessage, setShowStreamingMessage] = useState(false);
    const [localCheckpointId, setLocalCheckpointId] = useState<number | null>(null);

    const response = useMemo(() => {
        try {
            let response = JSON.parse(content);
            return response;
        } catch (error) {
            console.error('Failed to parse message content:', error);
            return null;
        }
    }, [content])

    // Parse checkpointId from ext data (for persistence across page reloads)
    const persistedCheckpointId = useMemo(() => {
        if (!response || !response.ext) return null;
        
        const debugStartCheckpoint = response.ext.find((item: any) => 
            item.type === 'debug_start_checkpoint' || 
            (item.type === 'debug_checkpoint' && item.data?.checkpoint_type === 'debug_start')
        );
        
        if (debugStartCheckpoint && debugStartCheckpoint.data && debugStartCheckpoint.data.checkpoint_id) {
            return debugStartCheckpoint.data.checkpoint_id;
        }
        
        return null;
    }, [response]);

    // Use persisted checkpoint ID if available, otherwise use local state
    const checkpointId = persistedCheckpointId || localCheckpointId;

    const handleDebugClick = async () => {
        if (isDebugging) return;
        
        const messageId = generateUUID();
        const message = {
            id: messageId,
            role: 'ai' as const,
            content: JSON.stringify({
                text: '🔍 Starting workflow analysis...\n',
                ext: []
            }),
            format: 'markdown',
            name: 'Assistant',
            finished: false,
            debugGuide: true
        }
        onAddMessage?.(message);
        
        try {
            // track debug trigger event
            WorkflowChatAPI.trackEvent({
                event_type: 'debug_trigger',
                message_type: 'debug',
                message_id: messageId,
                data: {}
            });

            // Save checkpoint before debugging
            await saveCheckpointBeforeDebug();
            
            dispatch({ type: 'SET_LOADING', payload: true });
            
            await handleQueueError(messageId);
        } finally {
            setIsDebugging(false);
        }
    };

    const saveCheckpointBeforeDebug = async () => {
        try {
            const prompt = await app.graphToPrompt();
            const sessionId = localStorage.getItem("sessionId") || '';
            
            if (sessionId && prompt) {
                const checkpointData = await WorkflowChatAPI.saveWorkflowCheckpoint(
                    sessionId,
                    prompt.output, // API format
                    prompt.workflow, // UI format
                    'debug_start'
                );
                
                setLocalCheckpointId(checkpointData.version_id);
                console.log(`Saved debug start checkpoint: ${checkpointData.version_id}`);
                
                // Update the current debug guide message to include checkpoint_id in ext data
                if (onUpdateMessage && response) {
                    const updatedExt = [...(response.ext || [])];
                    
                    // Remove any existing debug_start_checkpoint
                    const filteredExt = updatedExt.filter((item: any) => 
                        item.type !== 'debug_start_checkpoint' && 
                        !(item.type === 'debug_checkpoint' && item.data?.checkpoint_type === 'debug_start')
                    );
                    
                    // Add new checkpoint data
                    filteredExt.push({
                        type: 'debug_start_checkpoint',
                        data: {
                            checkpoint_id: checkpointData.version_id,
                            checkpoint_type: 'debug_start'
                        }
                    });
                    
                    const updatedMessage = {
                        id: messageId || generateUUID(),
                        role: 'ai' as const,
                        content: JSON.stringify({
                            text: response.text,
                            ext: filteredExt
                        }),
                        format: 'debug_guide' as const,
                        name: 'Assistant'
                    };
                    
                    onUpdateMessage(updatedMessage);
                }
            }
        } catch (error) {
            console.error('Failed to save checkpoint before debug:', error);
            // Continue with debug even if checkpoint save fails
        }
    };

    const handleQueueError = async (messageId: string) => {
        try {
            // Get current workflow for context
            const prompt = await app.graphToPrompt();
            
            let accumulatedText = '';
            let finalExt: any = null;

            // 创建新的 AbortController
            if (!!abortControllerRef) {
                abortControllerRef.current = new AbortController();
            }

            // Use the streaming debug agent API
            for await (const result of WorkflowChatAPI.streamDebugAgent(prompt, abortControllerRef?.current?.signal || undefined)) {
                if (result.text) {
                    accumulatedText = result.text;
                    if (result.ext) {
                        finalExt = result.ext;
                    }
                    const message = {
                        id: messageId,
                        role: 'ai' as const,
                        content: JSON.stringify({
                            text: accumulatedText,
                            ext: finalExt || []
                        }),
                        format: 'markdown',
                        name: 'Assistant',
                        finished: false,
                        debugGuide: true
                    }
                    onUpdateMessage?.(message);
                }
            }

            onUpdateMessage?.({
                id: messageId,
                role: 'ai' as const,
                content: JSON.stringify({
                    text: accumulatedText,
                    ext: finalExt || []
                }),
                format: 'markdown',
                name: 'Assistant',
                finished: true,
                debugGuide: true
            });
            dispatch({ type: 'SET_LOADING', payload: false });
            abortControllerRef.current = null;
        } catch (error: unknown) {
            console.error('Error calling debug agent:', error);
            setShowStreamingMessage(false);
            const errorObj = error as any;
            const errorMessage = {
                id: messageId,
                role: 'ai' as const,
                content: JSON.stringify({
                    text: `I encountered an error while analyzing your workflow: ${errorObj.message || 'Unknown error'}`,
                    ext: []
                }),
                format: 'markdown',
                name: 'Assistant',
                finished: true
            };
            onUpdateMessage?.(errorMessage);
            dispatch({ type: 'SET_LOADING', payload: false });
            abortControllerRef.current = null;
        }
    };

    if (!response) return null;

    return (
        <BaseMessage name={name}>
            <div className='bg-gray-100 pt-4 px-4 pb-3 rounded-lg'>
                <div className="flex justify-between items-start">
                    <p className="text-gray-700 text-sm flex-1">
                        {response.text}
                    </p>
                </div>
                
                <div className="flex justify-end mt-4">
                    <button
                        onClick={handleDebugClick}
                        disabled={isDebugging}
                        className={`debug-btn bg-debug-btn text-sm text-[#fff] rounded-lg px-4 py-2 ${
                            isDebugging 
                                ? 'cursor-not-allowed' 
                                : 'cursor-pointer'
                        }`}
                    >
                        {isDebugging ? 'Analyzing...' : 'Debug Errors'}
                    </button>
                </div>

                <div className="flex justify-end mt-2"> 
                    {/* Restore checkpoint icon */}
                    {!!checkpointId && (
                        <div className="ml-2 flex-shrink-0">
                            <RestoreCheckpoint
                                checkpointId={checkpointId} 
                                onRestore={() => {
                                    console.log('Workflow restored from checkpoint');
                                }}
                            />
                        </div>
                    )}
                </div>
            </div>
        </BaseMessage>
    );
}
