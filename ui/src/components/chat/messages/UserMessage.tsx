
// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import { BaseMessage } from './BaseMessage';
import { InformationCircleIcon } from '@heroicons/react/24/outline';
import { useEffect, useState } from 'react';
import RestoreCheckpoint from '../../ui/RestoreCheckpoint';

interface ExtItem {
    type: string;
    data?: any;
}

interface UserMessageProps {
    content: string;
    trace_id?: string;
    ext?: ExtItem[];
    finished?: boolean;
}

export function UserMessage({ content, trace_id, ext, finished }: UserMessageProps) {
    const [showTooltip, setShowTooltip] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopyTraceId = async () => {
        if (trace_id) {
            await navigator.clipboard.writeText(trace_id);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const [checkpointId, setChekpointId] = useState<number | null>(null);
    const [images, setImages] = useState<any[]>([])

    // Check if there's a checkpoint in ext data for workflow_update or param_update
    // let checkpointId: number | null = null;
    // let images: any[] = [];
    useEffect(() => {
        console.log(`[UserMessage] checkpointId:`, checkpointId);
    }, [checkpointId])
    useEffect(() => {
        // 添加调试日志
        console.log(`[UserMessage] Received ext data:`, ext);
        if (ext) {        
            // Look for workflow_rewrite_checkpoint or debug_checkpoint related to workflow updates
            const checkpointExt = ext.find((item) => 
                item.type === 'workflow_rewrite_checkpoint' || 
                (item.type === 'debug_checkpoint' && item.data?.checkpoint_type === 'workflow_rewrite_start')
            );
            
            console.log(`[UserMessage] Found checkpoint ext:`, checkpointExt);
            
            if (checkpointExt && checkpointExt.data && checkpointExt.data.checkpoint_id) {
                // checkpointId = checkpointExt.data.checkpoint_id;
                setChekpointId(checkpointExt.data.checkpoint_id)
                console.log(`[UserMessage] Extracted checkpoint ID:`, checkpointExt.data.checkpoint_id);
            }
            
            const hasImages = ext.some((item) => item.type === 'img');
            if (hasImages) {
                let _images: any[] = []
                ext.filter((item) => item.type === 'img').forEach((item) => _images = _images.concat(item.data));
                setImages(_images)
            }
            // If we have workflow/param updates but no checkpoint, we could show a message about it
            // But for now, we only show restore button if we have a checkpoint
        }
    }, [ext, finished])

    return (
        <BaseMessage name="User" isUser={true}>
            <div className="w-full rounded-lg border border-gray-700 p-4 text-gray-700 text-sm break-words">
                {
                    images.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-2">
                            {images.map((image) => (
                                <img src={image.url} alt={image.name} className="w-16 h-16 object-cover" />
                            ))}
                        </div>
                    )
                }
                <p className="whitespace-pre-wrap leading-snug">{content}</p>
                
                {/* Bottom right icons container */}
                <div className="flex justify-end">
                    <div className="flex items-center space-x-1 -mb-2">
                        {/* Restore checkpoint icon */}
                        {checkpointId && (
                            <RestoreCheckpoint 
                                checkpointId={checkpointId} 
                                onRestore={() => {
                                    console.log('Workflow restored from user message checkpoint');
                                }}
                                title={`Restore to version before this request (Checkpoint ${checkpointId})`}
                            />
                        )}
                        
                        {/* Trace ID icon */}
                        {trace_id && (
                            <div 
                                className="cursor-pointer opacity-40 hover:opacity-100 transition-opacity"
                                onMouseEnter={() => setShowTooltip(true)}
                                onMouseLeave={() => setShowTooltip(false)}
                                onClick={handleCopyTraceId}
                            >
                                <InformationCircleIcon className="h-3.5 w-3.5 text-gray-500 hover:!text-gray-700" />
                                
                                {/* Tooltip */}
                                {showTooltip && (
                                    <div className="absolute right-0 -top-6 bg-gray-700 text-white text-[10px] py-0.5 px-1.5 rounded shadow-sm whitespace-nowrap">
                                        {copied ? 'Copied!' : `Copy trace ID`}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </BaseMessage>
    );
} 