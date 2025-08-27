// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import { ChangeEvent, KeyboardEvent, useState, useRef, useEffect, useLayoutEffect, ReactNode, forwardRef, useImperativeHandle } from 'react';
import { SendIcon, ImageIcon, PlusIcon, XIcon, StopIcon } from './Icons';
import React from 'react';
import { WorkflowChatAPI } from '../../apis/workflowChatApi';
import { generateUUID } from '../../utils/uuid';
import { Portal } from './Portal';
import ImageLoading from '../ui/Image-Loading';
import { useChatContext } from '../../context/ChatContext';
import RewriteExpertModal from './RewriteExpertModal';

// Debug icon component
const DebugIcon = ({ className }: { className: string }) => (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M20 8h-2.81c-.45-.78-1.07-1.45-1.82-1.96L17 4.41 15.59 3l-2.17 2.17C12.96 5.06 12.49 5 12 5s-.96.06-1.42.17L8.41 3 7 4.41l1.63 1.63C7.88 6.55 7.26 7.22 6.81 8H4v2h2.09c-.05.33-.09.66-.09 1v1H4v2h2v1c0 .34.04.67.09 1H4v2h2.81c1.04 1.79 2.97 3 5.19 3s4.15-1.21 5.19-3H20v-2h-2.09c.05-.33.09-.66.09-1v-1h2v-2h-2v-1c0-.34-.04-.67-.09-1H20V8zm-6 8h-4v-2h4v2zm0-4h-4v-2h4v2z"/>
    </svg>
);

const ExpertIcon = ({ className }: { className: string }) => (
    <svg className={className} viewBox="0 0 1024 1024" fill="currentColor">
        <path d="M512.82 958.87c-25.38 0-49.1-12-63.45-32.21l-20.95-29.43a8 8 0 0 0-6.41-2.79l-319.1 1.72C46.17 896.16 0 852 0 797.7V165.3c0-54.3 46.17-98.45 102.91-98.45l256.13-1.72c50 0 97.12 18.21 132.6 51.28A182.32 182.32 0 0 1 512.9 140a184.56 184.56 0 0 1 21.06-23.31c35.55-33.21 82.65-51.51 132.63-51.51h254.7c56.74 0 102.91 44.17 102.91 98.46V796c0 54.29-46.17 98.45-102.91 98.45H603.63a8 8 0 0 0-6.42 2.79l-20.94 29.43c-14.35 20.16-38.07 32.2-63.45 32.2z m-409.91-822c-18.15 0-32.91 12.76-32.91 28.45V797.7c0 15.69 14.76 28.46 32.91 28.46l319.1-1.72c25.38 0 49.1 12 63.45 32.2l20.94 29.44c1.84 2.58 5.38 2.79 6.42 2.79s4.57-0.21 6.41-2.79l21-29.44c14.35-20.16 38.06-32.2 63.45-32.2h317.61c18.15 0 32.91-12.76 32.91-28.45v-632.4c0-15.69-14.76-28.46-32.91-28.46h-254.7c-65.49 0-118.77 48.76-118.77 108.68v461a35 35 0 1 1-70 0v-461c0-28.76-12-55.82-33.9-76.19-22.48-21-52.62-32.49-84.88-32.49z">
        </path>
        <path d="M362.52 330.46H197.37a35 35 0 0 1 0-70h165.15a35 35 0 0 1 0 70zM298.32 482.71h-101a35 35 0 0 1 0-70h101a35 35 0 0 1 0 70zM828.16 330.46H663.02a35 35 0 0 1 0-70h165.14a35 35 0 0 1 0 70zM828.16 482.71H727.21a35 35 0 0 1 0-70h100.95a35 35 0 0 1 0 70z">
        </path>
    </svg>
);
interface ChatInputProps {
    input: string;
    loading: boolean;
    onChange: (event: ChangeEvent<HTMLTextAreaElement>) => void;
    onSend: () => void;
    onKeyPress: (event: KeyboardEvent) => void;
    onUploadImages: (files: FileList) => void;
    uploadedImages: UploadedImage[];
    onRemoveImage: (imageId: string) => void;
    selectedModel: string;
    onModelChange: (model: string) => void;
    onStop?: () => void;
    onAddDebugMessage?: (message: any) => void;
}

export interface UploadedImage {
    id: string;
    file: File;
    preview: string;
    url: string;
}

export interface ChatInputRef {
    refreshModels: () => void;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const SUPPORTED_FORMATS = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

export const ChatInput = forwardRef<ChatInputRef, ChatInputProps>(({ 
    input, 
    loading, 
    onChange, 
    onSend, 
    onKeyPress, 
    onUploadImages,
    uploadedImages,
    onRemoveImage,
    selectedModel,
    onModelChange,
    onStop,
    onAddDebugMessage,
}, ref) => {
    const { state, dispatch } = useChatContext();
    const { messages } = state;
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [showRewriteExpertModal, setShowRewriteExpertModal] = useState(false);
    const [models, setModels] = useState<{
        label: ReactNode; name: string; image_enable: boolean 
}[]>([]);

    const fileInputRef = React.useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // 精确监听 textarea 的 scrollHeight 变化（处理 flex 布局）
    useEffect(() => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        const updateScrollHeight = () => {
            // 使用 requestAnimationFrame 确保布局完成
            requestAnimationFrame(() => {
                // 临时保存原始样式
                const originalStyle = textarea.style.cssText;
                
                // 强制重新计算
                textarea.style.height = 'auto';
                textarea.style.minHeight = 'auto';
                
                // 恢复原始样式
                textarea.style.cssText = originalStyle;
            });
        };

        const resizeObserver = new ResizeObserver(updateScrollHeight);
        resizeObserver.observe(textarea);

        // 监听内容变化
        const mutationObserver = new MutationObserver(updateScrollHeight);
        mutationObserver.observe(textarea, {
            childList: true,
            subtree: true,
            characterData: true
        });

        // 初始计算
        updateScrollHeight();

        return () => {
            resizeObserver.disconnect();
            mutationObserver.disconnect();
        };
    }, []);

    // Auto-resize textarea based on content - 使用 useLayoutEffect 防止闪烁
    useLayoutEffect(() => {
        if (textareaRef.current) {
            // Reset height to auto to get the correct scrollHeight
            textareaRef.current.style.height = 'auto';
            // Set the height to scrollHeight to fit all content
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 400)}px`;
        }
    }, [input]);

    // Function to load models from API
    const loadModels = async () => {
        try {
            const result = await WorkflowChatAPI.listModels();
            setModels(result.models);
        } catch (error) {
            console.error('Failed to load models:', error);
            // Fallback to default models if API fails
            setModels([{
                "label": "gemini-2.5-flash",
                "name": "gemini-2.5-flash",
                "image_enable": true
            },
            {
                "label": "gpt-4.1-mini",
                "name": "gpt-4.1-mini-2025-04-14-GlobalStandard",
                "image_enable": true,
            },
            {
                "label": "gpt-4.1",
                "name": "gpt-4.1-2025-04-14-GlobalStandard",
                "image_enable": true,
            }]);
        }
    };

    // Expose refreshModels method to parent component
    useImperativeHandle(ref, () => ({
        refreshModels: loadModels
    }), []);

    // Load models on component mount
    useEffect(() => {
        loadModels();
    }, []);

    const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        if (event.target.files) {
            if (uploadedImages?.length >= 3) {
                alert('You can only upload up to 3 images');
                return;
            }

            const invalidFiles: string[] = [];
            const validFiles: File[] = [];

            Array.from(event.target.files).forEach(file => {
                if (!SUPPORTED_FORMATS.includes(file.type)) {
                    invalidFiles.push(`${file.name} (unsupported format)`);
                } else if (file.size > MAX_FILE_SIZE) {
                    invalidFiles.push(`${file.name} (exceeds 5MB)`);
                } else {
                    validFiles.push(file);
                }
            });

            if (invalidFiles.length > 0) {
                alert(`The following files couldn't be uploaded:\n${invalidFiles.join('\n')}`);
            }

            if (uploadedImages?.length + validFiles.length > 3) {
                alert('You can only upload up to 3 images');
                return;
            }

            if (validFiles.length > 0) {
                const dataTransfer = new DataTransfer();
                validFiles.forEach(file => dataTransfer.items.add(file));
                onUploadImages(dataTransfer.files);
            }
        }
    };

    const handleDebugClick = () => {
        if (onAddDebugMessage) {
            if (messages?.[0]?.role === 'showcase') {
                dispatch({ type: 'CLEAR_MESSAGES' });
            }
            const debugMessage = {
                id: generateUUID(),
                role: 'ai' as const,
                content: JSON.stringify({
                    text: "Would you like me to help you debug the current workflow on the canvas?",
                    ext: []
                }),
                format: 'debug_guide' as const,
                name: 'Assistant'
            };
            onAddDebugMessage(debugMessage);
        }
    };

    return (
        <div className={`relative ${uploadedImages.length > 0 ? 'mt-12' : ''}`}>
            {/* 已上传图片预览 */}
            {uploadedImages.length > 0 && (
                <div className="absolute -top-10 left-0 grid grid-cols-3 gap-2 w-1/2">
                    {uploadedImages.map(image => (
                        <div key={image.id} className="relative group">
                            <img 
                                src={image.preview} 
                                alt="uploaded" 
                                className="w-full h-12 object-contain"
                            />
                            {
                                !!image?.url && image?.url !== '' ?  <button
                                    onClick={() => onRemoveImage(image.id)}
                                    className="absolute -top-1 -right-1 bg-white border-none text-gray-500 rounded-full p-0.5
                                             opacity-0 group-hover:!opacity-100 transition-opacity"
                                >
                                    <XIcon className="w-3 h-3" />
                                </button> : <ImageLoading />
                            }
                        </div>
                    ))}
                </div>
            )}

            <div className="w-full flex flex-row justify-end p-1 gap-2">
                <button
                    type="button"
                    onClick={() => setShowRewriteExpertModal(true)}
                    className="rounded-md bg-white border-none 
                                hover:!bg-gray-100
                                transition-all duration-200 active:scale-95"
                    title="Debug workflow">
                    <ExpertIcon className="h-5 w-5" />
                </button>
                <button
                    type="button"
                    onClick={handleDebugClick}
                    className="rounded-md bg-white border-none 
                                hover:!bg-gray-100
                                transition-all duration-200 active:scale-95
                                animate-breathe-green"
                    title="Debug workflow">
                    <DebugIcon className="h-5 w-5" />
                </button>
            </div>

            <textarea
                ref={textareaRef}
                onChange={onChange}
                onKeyDown={(e: KeyboardEvent) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        if (e.nativeEvent.isComposing) {
                            return;
                        }
                        e.preventDefault();
                        if (input.trim() !== '') {
                            onSend();
                        }
                    }
                    onKeyPress(e);
                }}
                value={input}
                placeholder="Type your message..."
                className="w-full min-h-[80px] max-h-[400px] resize-none rounded-md border 
                         border-gray-200 px-3 py-2 pr-12 pb-10 text-[14px] shadow-sm 
                         focus:outline-none focus:ring-2 focus:ring-blue-500 
                         focus:border-transparent bg-white transition-all 
                         duration-200 text-gray-700 overflow-y-auto"
                style={{ height: '80px' }}
            />

            {/* Bottom toolbar */}
            <div className="absolute bottom-2 left-3 right-12 flex items-center gap-2 
                          bg-white border-t border-gray-100 pt-1">
                {/* Model selector dropdown */}
                <select
                    value={selectedModel}
                    onChange={(e) => onModelChange(e.target.value)}
                    className="px-1.5 py-0.5 text-xs rounded-md 
                             border border-gray-200 bg-white text-gray-700
                             focus:outline-none focus:ring-2 focus:ring-blue-500
                             focus:border-transparent hover:bg-gray-50
                             transition-colors border-0"
                >
                    {models.map((model) => (
                        <option value={model.name} key={model.name}>{model.label}</option>
                    ))}
                </select>

                {/* Upload image button */}
                <button
                    type="button"
                    onClick={() => setShowUploadModal(true)}
                    disabled={!models.find(model => model.name === selectedModel)?.image_enable}
                    className={`p-1.5 text-gray-500 bg-white border-none
                             hover:!bg-gray-100 hover:!text-gray-600 
                             transition-all duration-200 outline-none
                             ${!models.find(model => model.name === selectedModel)?.image_enable ? 'opacity-50 cursor-not-allowed' : ''}`}>
                    <ImageIcon className="h-4 w-4" />
                </button>
            </div>

            {/* Send button */}
            <button
                type="submit"
                onClick={loading ? onStop : onSend}
                disabled={loading ? false : input.trim() === ''}
                className="absolute bottom-3 right-3 p-2 rounded-md text-gray-500 bg-white border-none 
                         hover:!bg-gray-100 hover:!text-gray-600 disabled:opacity-50 
                         transition-all duration-200 active:scale-95">
                {loading ? (
                    <StopIcon className="h-5 w-5 text-red-500 hover:text-red-600" />
                ) : (
                    <SendIcon className="h-5 w-5 group-hover:translate-x-1" />
                )}
            </button>

            {/* Debug button */}
            {/* <button
                type="button"
                onClick={handleDebugClick}
                className="absolute bottom-3 right-14 p-2 rounded-md text-gray-500 bg-white border-none 
                         hover:bg-gray-100 hover:text-gray-600 
                         transition-all duration-200 active:scale-95"
                title="Debug workflow">
                <DebugIcon className="h-5 w-5" />
            </button> */}
            {
                showRewriteExpertModal && <RewriteExpertModal onClose={() => setShowRewriteExpertModal(false)} />
            }
            {/* 上传图片模态框 */}
            {showUploadModal && (
                <Portal>
                    <div 
                        id="comfyui-copilot-modal" 
                        className="fixed inset-0 bg-[rgba(0,0,0,0.5)] flex items-center justify-center"
                        style={{
                            backgroundColor: 'rgba(0,0,0,0.5)'
                        }}
                    >
                        <div className="bg-white rounded-lg p-6 w-96 relative">
                            <button 
                                onClick={() => setShowUploadModal(false)}
                                className="absolute top-2 right-2 bg-white border-none text-gray-500 hover:!text-gray-700"
                            >
                                <XIcon className="w-5 h-5" />
                            </button>
                            
                            <h3 className="text-lg text-gray-800 font-medium mb-4">Upload Images</h3>
                            
                            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8
                                        flex flex-col items-center justify-center gap-4
                                        hover:!border-blue-500 transition-colors cursor-pointer"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <PlusIcon className="w-8 h-8 text-gray-400" />
                                <div className="text-center">
                                    <p className="text-sm text-gray-500 mb-2">
                                        Click to upload images or drag and drop
                                    </p>
                                    <p className="text-xs text-gray-400">
                                        Supported formats: JPG, PNG, GIF, WebP
                                    </p>
                                    <p className="text-xs text-gray-400">
                                        Max file size: 5MB, Max 3 images
                                    </p>
                                </div>
                            </div>

                            <input
                                ref={fileInputRef}
                                type="file"
                                multiple
                                accept={SUPPORTED_FORMATS.join(',')}
                                onChange={handleFileChange}
                                className="hidden"
                            />

                            {/* 预览区域 */}
                            {uploadedImages.length > 0 && (
                                <div className="mt-4 grid grid-cols-3 gap-2">
                                    {uploadedImages.map(image => (
                                        <div key={image.id} className="relative group">
                                            <img 
                                                src={image.preview} 
                                                alt="preview" 
                                                className="w-full h-20 object-contain"
                                            />
                                            {
                                                !!image?.url && image?.url !== '' ? <button
                                                    onClick={() => onRemoveImage(image.id)}
                                                    className="absolute -top-1 -right-1 bg-white border-none text-gray-500 rounded-full p-0.5
                                                            opacity-0 group-hover:!opacity-100 transition-opacity"
                                                >
                                                    <XIcon className="w-3 h-3" />
                                                </button> : <ImageLoading />
                                            }
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="mt-4 flex justify-end gap-2">
                                <button
                                    onClick={() => setShowUploadModal(false)}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 
                                            bg-white border border-gray-300 rounded-md 
                                            hover:!bg-gray-50"
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                </Portal>
            )}
        </div>
    );
});

ChatInput.displayName = 'ChatInput'; 