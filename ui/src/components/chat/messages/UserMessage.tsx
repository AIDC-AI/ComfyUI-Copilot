
// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import { BaseMessage } from './BaseMessage';
import { InformationCircleIcon } from '@heroicons/react/24/outline';
import { useState } from 'react';

interface UserMessageProps {
    content: string;
    trace_id?: string;
}

export function UserMessage({ content, trace_id }: UserMessageProps) {
    const [showTooltip, setShowTooltip] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopyTraceId = async () => {
        if (trace_id) {
            await navigator.clipboard.writeText(trace_id);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    return (
        <BaseMessage name="User" isUser={true}>
            <div className="w-full rounded-lg border border-gray-700 p-4 text-gray-700 text-sm break-words relative">
                <p className="whitespace-pre-wrap leading-snug">{content}</p>
                {trace_id && (
                    <div 
                        className="absolute bottom-1 right-1.5 cursor-pointer opacity-40 hover:opacity-100 transition-opacity"
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
        </BaseMessage>
    );
} 