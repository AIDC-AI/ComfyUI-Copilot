import { X } from "lucide-react";
import React, { useEffect } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string; // 可选：自定义内容区样式
  overlayClassName?: string; // 可选：自定义遮罩样式
  autoClose?: boolean; // 可选：是否自动关闭
}

const Modal: React.FC<ModalProps> = ({
  open,
  onClose,
  children,
  className = "",
  overlayClassName = "",
  autoClose = true,
}) => {
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (open && autoClose) {
      timer = setTimeout(() => {
        onClose();
      }, 3000);
    }

    return () => clearTimeout(timer);
  }, [open, autoClose]);

  if (!open) return null;

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/40 ${overlayClassName}`}
      onClick={onClose}
    >
      <div
        className={`relative bg-white rounded-lg shadow-lg p-6 min-w-[300px] max-w-full ${className}`}
        onClick={e => e.stopPropagation()} // 阻止冒泡，点击内容区不关闭
      >
        <button
          className="absolute top-2 right-4 bg-transparent border-none text-gray-400 hover:text-gray-600"
          onClick={onClose}
          aria-label="Close"
        >
          <X size={16}/>
        </button>
        {children}
      </div>
    </div>
  );
};

export default Modal;