import { MemoizedReactMarkdown } from "../../components/markdown";
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeExternalLinks from 'rehype-external-links';
import { useMemo, useState } from "react";
import { ChatResponse } from "../../types/types";
import { WorkflowChatAPI } from "../../apis/workflowChatApi";
import { LazyLoadImage } from 'react-lazy-load-image-component';

interface IProps {
  response: ChatResponse;
  specialClass?: string;
}

const Markdown = ({ response, specialClass }: IProps) => {
  const text = useMemo(() => response?.text || '', [response]);
  const [copied, setCopied] = useState(false);

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
        ${specialClass || ''}`
      }
      components={{
        p: ({ children }) => {
          return <p className="!my-0.5 leading-relaxed text-xs">{children}</p>
        },
        strong: ({ children }) => {
          return <strong className='text-gray-900'>{children}</strong>
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
              <code className='text-xs bg-gray-100 text-gray-900 rounded px-1'>{children}</code>
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
          return <pre className='text-xs bg-gray-100 text-gray-800 rounded p-2 overflow-x-auto'>{children}</pre>
        },
        img: ({ node, ...props }) => {
          let isGif = false;
          const srcStrs = props.src?.split('?');
          if (srcStrs && srcStrs.length > 0) {
            isGif = srcStrs[0]?.endsWith('.gif') || srcStrs[0]?.endsWith('.webp');
          }
          return (<div className={`${isGif ? '' : 'w-1/2'} mx-auto`}>
            <LazyLoadImage 
              {...props}
              effect="opacity"
              className="w-full h-auto"
              onError={(e) => {
                console.warn('Image failed to load:', props.src, 'Error:', e);
                e.currentTarget.style.opacity = '0';
              }}
            />
          </div>)
        },
        a: ({ href, children }) => {
          let messageType = 'markdown';
          let messageId = null;
          try {
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
}

export default Markdown;