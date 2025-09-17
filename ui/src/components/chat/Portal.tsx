// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import { ReactNode, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

interface PortalProps {
    children: ReactNode;
    container?: HTMLElement;
    className?: string;
}

export function Portal({ children, container = document.body, className = '' }: PortalProps) {
    const [mounted, setMounted] = useState(false);
    console.log('container-->', container)
    useEffect(() => {
        setMounted(true);
        return () => setMounted(false);
    }, []);

    if (!mounted) {
        return null;
    }

    // 创建一个包装器来应用样式
    const portalContent = (
        <div 
            className={`fixed inset-0 ${className}`}
            style={{
                zIndex: 9999
            }}
        >
            {children}
        </div>
    );

    return createPortal(portalContent, container);
} 