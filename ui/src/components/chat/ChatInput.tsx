// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import { ChangeEvent, KeyboardEvent, useState, useRef, useEffect, useLayoutEffect, ReactNode, forwardRef, useImperativeHandle } from 'react';
import { SendIcon, ImageIcon, XIcon, StopIcon } from './Icons';
import { WorkflowChatAPI } from '../../apis/workflowChatApi';
import { generateUUID } from '../../utils/uuid';
import ImageLoading from '../ui/Image-Loading';
import { useChatContext } from '../../context/ChatContext';
import RewriteExpertModal from './RewriteExpertModal';
import ButtonWithModal from '../ui/ButtonWithModal';
import { UploadedImage } from '../../types/types';
import ImageUploadModal from './ImageUploadModal';
import PackageDownloadModal from './ModelDownloadModal';
import { getLocalStorage, LocalStorageKeys, setLocalStorage } from '../../utils/localStorageManager';

// Debug icon component
const DebugIcon = ({ className }: { className: string }) => (
    <svg className={className} viewBox="0 0 1024 1024" fill="currentColor">
        <path d="M928 576h-96.32V365.333333l86.826667-86.613333c12.48-12.48 12.48-32.746667 0.106666-45.226667-12.586667-12.586667-32.853333-12.48-45.333333-0.106666L786.453333 320H237.226667l-86.933334-86.613333c-12.48-12.48-32.746667-12.48-45.226666 0.106666-12.48 12.48-12.48 32.746667 0.106666 45.226667l87.146667 86.933333V576H96c-17.706667 0-32 14.293333-32 32s14.293333 32 32 32h96.32v29.653333c-0.213333 1.493333-0.32 2.986667-0.32 4.48 0 50.24 13.546667 97.493333 37.546667 138.986667l-92.053334 92.16c-12.48 12.48-12.48 32.746667 0 45.226667 6.293333 6.293333 14.4 9.386667 22.613334 9.386666s16.426667-3.093333 22.613333-9.386666l85.12-85.226667c58.773333 64.106667 146.346667 104.96 244.16 104.96 97.813333 0 185.493333-40.853333 244.16-104.96l85.226667 85.333333c6.293333 6.293333 14.4 9.386667 22.613333 9.386667s16.426667-3.093333 22.613333-9.386667c12.48-12.48 12.48-32.746667 0-45.226666l-92.16-92.266667c23.893333-41.493333 37.44-88.746667 37.44-138.986667 0-1.493333-0.106667-2.986667-0.32-4.48V640H928c17.706667 0 32-14.293333 32-32s-14.293333-32-32-32zM543.573333 904.533333c0.32-1.706667 0.426667-3.413333 0.426667-5.226666V544c0-17.706667-14.293333-32-32-32s-32 14.293333-32 32v355.413333c0 1.813333 0.106667 3.52 0.426667 5.226667-124.8-13.973333-222.08-109.76-224.426667-226.133333 0.213333-1.386667 0.32-2.773333 0.32-4.16V384h511.36v290.24c0 1.386667 0.106667 2.773333 0.213333 4.16-2.24 116.373333-99.52 212.16-224.32 226.133333z">
        </path>
        <path d="M352 256h320c10.24 0 19.733333-4.8 25.813333-13.013333 5.973333-8.213333 7.786667-18.773333 4.8-28.48C674.453333 124.48 597.76 64 512 64c-85.866667 0-162.453333 60.48-190.506667 150.506667-3.093333 9.706667-1.28 20.266667 4.8 28.48 5.973333 8.213333 15.466667 13.013333 25.706667 13.013333z m160-128c43.84 0 84.48 24.533333 110.08 64H401.92c25.6-39.466667 66.24-64 110.08-64z">
        </path>
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

const PackageIcon = ({ className }: { className: string }) => (
    <svg className={className} viewBox="0 0 1024 1024" fill="currentColor">
        <path d="M820.376748 284.430361v228.885113a20.509419 20.509419 0 0 0 41.018838 0V249.974538a19.689042 19.689042 0 0 0-2.871319-9.434333v-2.050942a21.739984 21.739984 0 0 0-5.332449-5.332448L423.314402 2.630948a20.509419 20.509419 0 0 0-20.09923 0L10.254709 232.336438a13.946405 13.946405 0 0 0-4.92226 4.92226v2.461131a16.407535 16.407535 0 0 0-5.332449 10.254709v533.244886a8.203767 8.203767 0 0 0 2.46113 2.871319l2.871319 2.871319 392.960462 229.295301a20.09923 20.09923 0 0 0 20.099231 0l196.890419-100.085964a20.919607 20.919607 0 0 0 8.203768-27.892809 20.509419 20.509419 0 0 0-27.89281-8.613956l-164.075349 87.780312v-243.651894l189.917217-102.136905a20.509419 20.509419 0 0 0 11.075086-18.048289V383.695948zM41.018837 287.30168l184.17458 105.8286V615.452379l2.461131 3.281507a11.075086 11.075086 0 0 0 3.281507 2.871319l157.512335 91.882196v252.676038L41.018837 762.710006z m351.941625 210.016448v172.279117l-126.748207-75.88485v-176.381L394.191028 492.395867a22.150172 22.150172 0 0 0-1.230566 3.281507z m20.919608-41.018838l-137.413106-82.037675 146.43725-85.72937L574.263724 369.339355z m0-410.188374l382.295564 205.094187L615.282561 347.189183l-182.944015-98.855399a20.509419 20.509419 0 0 0-20.09923 0L235.448127 351.701255 61.118068 249.974538z m180.072696 549.242233l-159.973466 86.139559v-185.815334-3.691695l160.383654-86.139559zM1066.489773 841.876362a20.509419 20.509419 0 0 0-29.123375 0l-98.035021 95.984079v-229.295301a20.509419 20.509419 0 0 0-41.018837 0v229.295301l-95.98408-95.984079a20.509419 20.509419 0 0 0-29.123375 0 20.509419 20.509419 0 0 0 0 28.713186l131.26028 131.26028a20.919607 20.919607 0 0 0 28.713186 0l131.26028-131.26028a20.509419 20.509419 0 0 0 2.050942-28.713186z">
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

export interface ChatInputRef {
    refreshModels: () => void;
}

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
    const [models, setModels] = useState<{label: ReactNode; name: string; image_enable: boolean }[]>([]);

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

    const updateModels = (list: {label: string; name: string; image_enable: boolean }[]) => {
        const selectedModel = getLocalStorage(LocalStorageKeys.MODELS_POP_VIEW_SELECTED);
        // 之前记录的能在列表中找到，使用之前的记录。否则使用列表第一项重置
        if (selectedModel && list.findIndex(model => model.name === selectedModel) !== -1) {
            onModelChange(selectedModel)
        } else {
            onModelChange(list[0].name)
        }
        setLocalStorage(LocalStorageKeys.MODELS_POP_VIEW_LIST, JSON.stringify(list));
        setModels([...list,
            {
                "label": "reload",
                "name": "reload",
                "image_enable": true
            }
        ]);
    }

    // Function to load models from API
    const loadModels = async () => {
        try {
            const result = await WorkflowChatAPI.listModels();
            updateModels(result.models);
        } catch (error) {
            console.error('Failed to load models:', error);
            // Fallback to default models if API fails
            const list = [
                {
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
                },
                {
                    "label": "reload",
                    "name": "reload",
                    "image_enable": true
                }
            ]
            updateModels(list);
        }
    };

    // Expose refreshModels method to parent component
    useImperativeHandle(ref, () => ({
        refreshModels: loadModels
    }), []);

    // Load models on component mount
    useEffect(() => {
        // 1天之内不再重新获取models
        const currentTime = new Date().getTime()
        const time = getLocalStorage(LocalStorageKeys.MODELS_POP_VIEW_TIME);
        // 一天之内使用当前缓存
        if (!!Number(time) && currentTime - Number(time) < 1000 * 60 * 60 * 24) {
            const list = getLocalStorage(LocalStorageKeys.MODELS_POP_VIEW_LIST);
            if (!!list) {
                updateModels(JSON.parse(list));
            }
            return;
        }
        setLocalStorage(LocalStorageKeys.MODELS_POP_VIEW_TIME, new Date().getTime().toString());
        loadModels();
    }, []);

    const handleDebugClick = () => {
        WorkflowChatAPI.trackEvent({
            event_type: 'debug_icon_click',
            message_type: 'debug',
            data: {}
        })
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

    const handleModelSelected = (value: string) => {
        if (value === 'reload') {
            loadModels();
        } else {
            onModelChange(value);
        }
    }

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
                <ButtonWithModal 
                    buttonClass="rounded-md bg-white border-none 
                                hover:!bg-gray-100"
                    buttonContent={<PackageIcon className="h-5 w-5" />}
                    onOpen={() => {
                        WorkflowChatAPI.trackEvent({
                            event_type: 'model_download_icon_click',
                            message_type: 'ui',
                            data: {}
                        })
                    }}
                    renderModal={(onClose) => <PackageDownloadModal onClose={onClose} />}
                />
                <ButtonWithModal
                    buttonClass="rounded-md bg-white border-none 
                                hover:!bg-gray-100"
                    buttonContent={<ExpertIcon className="h-5 w-5" />}
                    renderModal={(onClose) => <RewriteExpertModal onClose={onClose} />}
                />
                <button
                    onClick={handleDebugClick}
                    className="rounded-md bg-white border-none 
                                hover:!bg-gray-100"
                >
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
                    onChange={(e) => handleModelSelected(e.target.value)}
                    className="px-1.5 py-0.5 text-xs rounded-md 
                             border border-gray-200 bg-white text-gray-700
                             focus:outline-none focus:ring-2 focus:ring-blue-500
                             focus:border-transparent hover:bg-gray-50
                             transition-colors border-0"
                >
                    {models?.map((model) => (
                        <option value={model.name} key={model.name}>{model.label}</option>
                    ))}
                </select>

                {/* Upload image button */}
                <ButtonWithModal 
                    buttonClass={`p-1.5 text-gray-500 bg-white border-none
                        hover:!bg-gray-100 hover:!text-gray-600 
                        transition-all duration-200 outline-none
                        ${!models?.find(model => model.name === selectedModel)?.image_enable ? 'opacity-50 cursor-not-allowed' : ''}`}
                    buttonContent={<ImageIcon className="h-4 w-4" />}
                    renderModal={(onClose) => <ImageUploadModal 
                        onUploadImages={onUploadImages}
                        uploadedImages={uploadedImages}
                        onRemoveImage={onRemoveImage}
                        onClose={onClose}
                    />}
                />
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
        </div>
    );
});

ChatInput.displayName = 'ChatInput'; 