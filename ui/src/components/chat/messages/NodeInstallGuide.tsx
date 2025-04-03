/*
 * @Author: 晴知 qingli.hql@alibaba-inc.com
 * @Date: 2024-12-26 17:16:51
 * @LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
 * @LastEditTime: 2025-02-26 14:14:07
 * @FilePath: /comfyui_copilot/ui/src/components/chat/messages/NodeInstallGuide.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import React from 'react';

interface NodeInstallGuideProps {
    content: string;
    onLoadSubgraph?: () => void;
}

export function NodeInstallGuide({ content, onLoadSubgraph }: NodeInstallGuideProps) {
    const response = JSON.parse(content);
    const nodeInfos = response.ext?.find((item: { type: string }) => item.type === 'node_install_guide')?.data || [];
    
    const uniqueNodeInfos = nodeInfos.reduce((acc: any[], node) => {
        if (!acc.some(n => n.name === node.name)) {
            acc.push(node);
        }
        return acc;
    }, []);

    return (
        <div>
            <p>在加载graph到画布前，以下节点有待安装，请跳转到对应的github安装节点：</p>
            <div className="grid grid-cols-2 gap-3">
                {uniqueNodeInfos.map((node: any, index: number) => (
                    <div 
                        key={index}
                        className="w-full p-3 bg-white rounded-lg border border-gray-200 
                                 hover:shadow-sm transition-all duration-200"
                    >
                        <div className="flex flex-col">
                            <h3 className="text-[12px] font-medium text-gray-800 mb-4">
                                {node.name}
                            </h3>
                            <div className="flex justify-end">
                                {node.repository_url ? (
                                    <a
                                        href={node.repository_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="px-2 py-1 bg-white text-gray-900 rounded-md 
                                                 border border-gray-900 hover:bg-gray-100 
                                                 transition-colors text-[10px] flex items-center gap-1"
                                    >
                                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                        </svg>
                                        Download
                                    </a>
                                ) : (
                                    <a
                                        href={`https://www.google.com/search?q=${encodeURIComponent(node.name + ' comfyui custom node')}`}
                                        target="_blank"
                                        rel="noopener noreferrer" 
                                        className="px-2 py-1 bg-gray-100 text-gray-500 rounded-md
                                                 border border-gray-300 text-[10px] flex items-center gap-1"
                                    >
                                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 21h7a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v11m0 5l4.879-4.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242z" />
                                        </svg>
                                        Search on Google
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
            <p className="mt-4"></p>
            <p>安装完成后，请点击继续加载graph按钮，将graph加载到画布中：</p>
            <div className="mt-4">
                <button
                    className="px-3 py-2 bg-blue-500 text-white rounded-md 
                             hover:bg-blue-600 transition-colors text-xs block mx-auto"
                    onClick={onLoadSubgraph}
                >
                    继续加载graph
                </button>
            </div>
        </div>
    );
} 