// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.
// Copyright (C) 2025 ComfyUI-Copilot Authors
// Licensed under the MIT License.

import React from 'react'
import { MemoizedReactMarkdown } from "../../markdown";
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeExternalLinks from 'rehype-external-links';
import { BaseMessage } from './BaseMessage';
import { ChatResponse } from "../../../types/types";
import { useRef, useState } from "react";
import { WorkflowChatAPI } from "../../../apis/workflowChatApi";

interface AIMessageProps {
  content: string;
  name?: string;
  avatar: string;
  format?: string;
  onOptionClick?: (option: string) => void;
  extComponent?: React.ReactNode;
  metadata?: any;
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

export function AIMessage({ content, name = 'Assistant', avatar, format, onOptionClick, extComponent, metadata }: AIMessageProps) {
  const markdownWrapper = useRef<HTMLDivElement | null>(null)
  
  // Renders markdown content with customized styles and components
  const renderMarkdown = (text: string, specialClass?: string) => {
    return (
      <MemoizedReactMarkdown
        rehypePlugins={[
          [rehypeExternalLinks, { target: '_blank' }],
          rehypeKatex
        ]}
        remarkPlugins={[remarkGfm, remarkMath]}
        className={`prose prose-xs prose-neutral prose-a:text-accent-foreground/50 break-words [&>*]:!my-1 leading-relaxed text-xs text-gray-700
                  prose-headings:font-semibold
                  prose-h1:text-base
                  prose-h2:text-sm
                  prose-h3:text-xs
                  prose-h4:text-xs
                  prose-p:text-xs
                  prose-ul:text-xs
                  prose-ol:text-xs
                  prose-li:text-xs
                  prose-code:text-xs
                  prose-pre:text-xs
                  ${specialClass || ''}`}
        components={{
          p: ({ children }) => {
            return <p className="!my-0.5 leading-relaxed text-xs">{children}</p>
          },
          strong: ({ children }) => {
            return <strong className="text-gray-900">{children}</strong>
          },
          h1: ({ children }) => {
            return <h1 className="text-base font-semibold !my-1">{children}</h1>
          },
          h2: ({ children }) => {
            return <h2 className="text-sm font-semibold !my-1">{children}</h2>
          },
          h3: ({ children }) => {
            return <h3 className="text-xs font-semibold !my-1">{children}</h3>
          },
          h4: ({ children }) => {
            return <h4 className="text-xs font-semibold !my-1">{children}</h4>
          },
          table: ({ children }) => (
            <table className="border-solid border w-[100%] text-xs">{children}</table>
          ),
          th: ({ children }) => (
            <th className="border-solid border text-center pt-2 text-xs">{children}</th>
          ),
          td: ({ children }) => {
            if (Array.isArray(children) && children?.length > 0) {
              const list: any[] = [];
              const length = children.length;
              for (let i = 0; i < length; i++) {
                if (children[i] === '<br>') {
                  list.push(<br />)
                } else {
                  list.push(children[i])
                }
              }
              children = list;
            }
            return (
              <td className="border-solid border border-[#979797] text-center text-xs">{children}</td>
            )
          },
          code: ({ children }) => {
            const [copied, setCopied] = useState(false);
            
            const handleCopy = async () => {
              try {
                await navigator.clipboard.writeText(children as string);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              } catch (err) {
                console.error('Failed to copy text:', err);
              }
            };
            
            return (
              <span className="relative group inline-flex items-center">
                <code className="text-xs bg-gray-100 text-gray-900 rounded px-1">{children}</code>
                <button 
                  onClick={handleCopy}
                  className="absolute top-0 right-0 bg-gray-200 rounded p-1 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-300 z-10"
                  aria-label="Copy code"
                >
                  {copied ? (
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M8 2a1 1 0 000 2h2a1 1 0 100-2H8z" />
                      <path d="M3 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v6h-4.586l1.293-1.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L10.414 13H15v3a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" />
                    </svg>
                  )}
                </button>
              </span>
            );
          },
          pre: ({ children }) => {
            return <pre className="text-xs bg-gray-100 text-gray-800 rounded p-2 overflow-x-auto">{children}</pre>
          },
          img: ({ node, ...props }) => (
            <div className="w-1/2 mx-auto">
              <img
                {...props}
                loading="lazy"
                className="w-full h-auto block" 
                onError={(e) => {
                  console.warn('Image failed to load:', props.src, 'Error:', e);
                  e.currentTarget.style.opacity = '0';
                }}
              />
            </div>
          ),
          a: ({ href, children }) => {
            let messageType = 'markdown';
            let messageId = null;
            try {
              const response = JSON.parse(content);
              messageType = response.ext?.[0]?.type || 'markdown';
              messageId = response?.message_id;
            } catch (e) {
              console.error('Error parsing content:', e);
            }
            return (
              <a 
                href={href} 
                target="_blank" 
                rel="noopener noreferrer"
                onClick={() => {
                  WorkflowChatAPI.trackEvent({
                    event_type: 'markdown_link_click',
                    message_type: messageType,
                    message_id: messageId,
                    data: {
                      link_url: href,
                      link_text: children
                    }
                  });
                }}
              >
                {children}
              </a>
            );
          },
        }}
      >
        {text}
      </MemoizedReactMarkdown>
    );
  };

  const renderContent = () => {
    try {
      const response = JSON.parse(content) as ChatResponse;
      const guides = response.ext?.find(item => item.type === 'guides')?.data || [];

      // Check if this is a special message type based on intent metadata
      if (metadata?.intent) {
        const intent = metadata.intent;
        
        // Render different card styles based on intent
        // Only handle node_explain and node_params with card styles
        if (intent === 'node_explain') {
          return (
            <NodeExplainCard 
              content={renderMarkdown(response.text || '')}
            />
          );
        } else if (intent === 'node_params') {
          return (
            <NodeParamsCard 
              content={renderMarkdown(response.text || '')}
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
              {renderMarkdown(response.text)}
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
                  className="px-3 py-1.5 text-gray-700 rounded-md hover:!bg-gray-50 transition-colors text-[12px] w-[calc(50%-0.25rem)]"
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

  return (
    <BaseMessage name={name}>
      <div className="w-full rounded-lg bg-gray-50 p-4 text-gray-900 text-sm break-words overflow-hidden">
        {renderContent()}
      </div>
    </BaseMessage>
  );
} 