// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

// Interface for generated images
export interface GeneratedImage {
  url: string;
  params: { [key: string]: any };
}

// Interface for parameter debug interface props
export interface ParameterDebugInterfaceProps {
  selectedNodes: any[];
  visible: boolean;
  onClose?: () => void;
}

// Interface for dropdown state
export interface DropdownState {
  isOpen: boolean;
  x: number;
  y: number;
}

// Interface for mapping widget parameters
export interface WidgetParamConf {
  [key: string]: any;
}