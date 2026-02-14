// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.
// Copyright (C) 2025 ComfyUI-Copilot Authors
// Licensed under the MIT License.

import React, { useEffect, useState, useCallback } from 'react'
import { BaseMessage } from './BaseMessage';
import { ChatResponse } from "../../../types/types";
import { useRef } from "react";
import Markdown from '../../ui/Markdown';
import { WorkflowChatAPI } from '../../../apis/workflowChatApi';
import { Volume2, Square, Loader2 } from 'lucide-react';

interface AIMessageProps {
  content: string;
  name?: string;
  avatar: string;
  format?: string;
  onOptionClick?: (option: string) => void;
  extComponent?: React.ReactNode;
  metadata?: any;
  finished?: boolean;
  debugGuide?: boolean;
}

// Card component for node explanation intent
const NodeExplainCard = ({ content }: { content: React.ReactNode }) => {
  return (
    <div className="rounded-lg shadow-sm">
      <div className="flex items-center mb-1">
        <div className="rounded-full mr-1">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-base font-bold">Node Usage Guide</h3>
      </div>
      <div className="markdown-content">
        {content}
      </div>
    </div>
  );
};

// Card component for node parameters intent
const NodeParamsCard = ({ content }: { content: React.ReactNode }) => {
  return (
    <div className="rounded-lg border border-green-200 bg-green-50 p-1 shadow-sm">
      <div className="flex items-center mb-1">
        <div className="bg-green-100 rounded-full p-1 mr-1">
          <svg className="h-4 w-4 text-green-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <h3 className="text-sm font-medium text-green-800">Node Parameter Reference</h3>
      </div>
      <div className="markdown-content text-green-900">
        {content}
      </div>
    </div>
  );
};

// Cache voice capability check so we don't call API per message
let _voiceCapCache: { tts: boolean } | null = null;
let _voiceCapPromise: Promise<{ tts: boolean }> | null = null;

function useVoiceAvailable(): boolean {
  const [available, setAvailable] = useState(_voiceCapCache?.tts ?? false);
  useEffect(() => {
    if (_voiceCapCache !== null) {
      setAvailable(_voiceCapCache.tts);
      return;
    }
    if (!_voiceCapPromise) {
      _voiceCapPromise = WorkflowChatAPI.voiceCapabilities().then(cap => {
        _voiceCapCache = { tts: cap.tts };
        return _voiceCapCache;
      }).catch(() => {
        _voiceCapCache = { tts: false };
        return _voiceCapCache;
      });
    }
    _voiceCapPromise.then(cap => setAvailable(cap.tts));
  }, []);
  return available;
}

// TTS playback button for AI messages
const TTSButton = ({ text }: { text: string }) => {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleClick = useCallback(async () => {
    setError(null);

    // If already playing, stop
    if (playing && audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
      setPlaying(false);
      return;
    }

    if (!text || text.trim().length === 0) return;
    setLoading(true);

    try {
      const blob = await WorkflowChatAPI.textToSpeech(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        URL.revokeObjectURL(url);
        audioRef.current = null;
        setPlaying(false);
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        audioRef.current = null;
        setPlaying(false);
      };

      await audio.play();
      setPlaying(true);
    } catch (err: any) {
      const msg = err?.message || String(err);
      console.error('TTS playback failed:', msg);
      // Detect terms acceptance error and show actionable alert
      if (msg.includes('terms') || msg.includes('model_terms_required')) {
        setError('terms_required');
      } else {
        setError(msg.length > 80 ? msg.slice(0, 77) + '...' : msg);
        setTimeout(() => setError(null), 6000);
      }
    } finally {
      setLoading(false);
    }
  }, [text, playing]);

  return (
    <div className="relative inline-block">
      <button
        onClick={handleClick}
        disabled={loading}
        className={`p-1 rounded-md hover:!text-gray-600 hover:!bg-gray-100 
                   border-none bg-transparent transition-all duration-200 cursor-pointer 
                   disabled:opacity-50 disabled:cursor-wait ${error ? 'text-red-400' : 'text-gray-400'}`}
        title={error || (playing ? 'Stop audio' : 'Read aloud')}
      >
        {loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : playing ? (
          <Square className="h-3.5 w-3.5 text-red-500" />
        ) : (
          <Volume2 className="h-3.5 w-3.5" />
        )}
      </button>
      {error && error === 'terms_required' ? (
        <div className="absolute bottom-full right-0 mb-1 px-2 py-1.5 text-xs bg-amber-50 border border-amber-300 rounded shadow-sm z-50 flex items-center gap-1.5 whitespace-nowrap">
          <span className="text-amber-700">Accept Groq model terms first</span>
          <a
            href="https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english"
            target="_blank"
            rel="noopener noreferrer"
            className="px-1.5 py-0.5 bg-amber-600 text-white rounded text-xs font-medium hover:!bg-amber-700 no-underline"
            onClick={() => setTimeout(() => setError(null), 500)}
          >
            Open ↗
          </a>
          <button onClick={() => setError(null)} className="text-amber-400 hover:!text-amber-600 bg-transparent border-none cursor-pointer text-xs p-0">✕</button>
        </div>
      ) : error ? (
        <div className="absolute bottom-full right-0 mb-1 px-2 py-1 text-xs text-red-600 bg-red-50 border border-red-200 rounded shadow-sm whitespace-nowrap max-w-[280px] truncate z-50">
          {error}
        </div>
      ) : null}
    </div>
  );
};

export function AIMessage({ content, name = 'Assistant', avatar, format, onOptionClick, extComponent, metadata, finished, debugGuide }: AIMessageProps) {
  const markdownWrapper = useRef<HTMLDivElement | null>(null)
  const voiceAvailable = useVoiceAvailable();

  const renderContent = () => {
    try {
      const response = JSON.parse(content) as ChatResponse;
      const guides = response.ext?.find(item => item.type === 'guides')?.data || [];
      
      // 检查是否有实时更新的ext数据
      const hasWorkflowUpdate = response.ext?.some(item => item.type === 'workflow_update');
      const hasParamUpdate = response.ext?.some(item => item.type === 'param_update');

      // Check if this is a special message type based on intent metadata
      if (metadata?.intent) {
        const intent = metadata.intent;
        
        // Render different card styles based on intent
        // Only handle node_explain and node_params with card styles
        if (intent === 'node_explain') {
          return (
            <NodeExplainCard 
              content={<Markdown response={response || {}} />}
            />
          );
        } else if (intent === 'node_params') {
          return (
            <NodeParamsCard 
              content={<Markdown response={response || {}} />}
            />
          );
        }
        // The downstream_subgraph_search intent is handled by the extComponent in MessageList.tsx
        // and doesn't need special card rendering here
      }

      // Default rendering for regular conversation messages
      return (
        <div className="space-y-3">
          {format === 'markdown' && response.text ? (
            <div ref={markdownWrapper as React.RefObject<HTMLDivElement>}>
              <Markdown response={response || {}} />
            </div>
          ) : response.text ? (
            <p className="whitespace-pre-wrap text-left">
              {response.text}
            </p>
          ) : null}

          {guides.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {guides.map((guide: string, index: number) => (
                <button
                  key={index}
                  className="px-3 py-1.5 text-gray-700 rounded-md hover:!bg-gray-50 transition-colors text-[12px] w-[calc(50%-0.25rem)] border border-gray-700"
                  onClick={() => onOptionClick?.(guide)}
                >
                  {guide}
                </button>
              ))}
            </div>
          )}

          {extComponent}
        </div>
      );
    } catch {
      return <p className="whitespace-pre-wrap text-left">{content}</p>;
    }
  };

  // Extract plain text for TTS from message content
  const getPlainText = (): string => {
    try {
      const response = JSON.parse(content) as ChatResponse;
      return response.text || '';
    } catch {
      return content || '';
    }
  };

  return (
    <BaseMessage name={name}>
      <div className="w-full rounded-lg bg-gray-50 p-4 text-gray-900 text-sm break-words overflow-hidden">
        {renderContent()}
        {debugGuide && !finished && (
            <div className="flex items-center gap-2 text-blue-500 text-sm">
                <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                Analyzing workflow...
            </div>
        )}
        
        {/* 显示实时更新状态 */}
        {(() => {
          try {
            const response = JSON.parse(content) as ChatResponse;
            const hasWorkflowUpdate = response.ext?.some(item => item.type === 'workflow_update');
            const hasParamUpdate = response.ext?.some(item => item.type === 'param_update');
            
            if (!finished && (hasWorkflowUpdate || hasParamUpdate)) {
              return (
                <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-2 text-green-700 text-sm">
                    <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="font-medium">
                      {hasWorkflowUpdate ? 'Workflow Updated' : 'Parameters Updated'}
                    </span>
                  </div>
                  <div className="text-xs text-green-600 mt-1">
                    Changes have been applied to the canvas. Debug process continues...
                  </div>
                </div>
              );
            }
          } catch (error) {
            // Ignore parsing errors
          }
          return null;
        })()}

        {/* TTS read-aloud button — only show when message is finished and voice is available */}
        {finished && voiceAvailable && getPlainText().length > 0 && (
          <div className="mt-2 flex justify-end border-t border-gray-100 pt-1">
            <TTSButton text={getPlainText()} />
          </div>
        )}
      </div>
    </BaseMessage>
  );
} 