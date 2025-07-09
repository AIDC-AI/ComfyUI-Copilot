// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// 定义事件常量
const COPILOT_EVENTS = {
    EXPLAIN_NODE: 'copilot:explain-node',
    TOOLBOX_USAGE: 'copilot:toolbox-usage',
    TOOLBOX_PARAMETERS: 'copilot:toolbox-parameters',
    TOOLBOX_DOWNSTREAMNODES: 'copilot:toolbox-downstreamnodes',
};

const COPILOT_TOOLBOX_IDS = {
    USAGE: 'Copilot.Toolbox.Usage',
    PARAMETERS: 'Copilot.Toolbox.Parameters',
    DOWNSTREAMNODES: 'Copilot.Toolbox.DownstreamNodes'
}

function addExtraMenuOptions(nodeType, nodeData, app) {
    const original_getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
    nodeType.prototype.getExtraMenuOptions = function (_, options) {
        original_getExtraMenuOptions?.apply(this, arguments);
        options.push({
            content: "Explain with Copilot",
            callback: async () => {
                const nodeTypeUniqueId = nodeType?.comfyClass;
                // 触发自定义事件
                window.dispatchEvent(new CustomEvent(COPILOT_EVENTS.EXPLAIN_NODE, {
                    detail: { nodeType: nodeTypeUniqueId }
                }));
            }
        })
    }
}

app.registerExtension({
    name: "ComfyUI-Copilot-Bridge",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        addExtraMenuOptions(nodeType, nodeData, app);
    },
    commands: [
        {
            id: COPILOT_TOOLBOX_IDS.USAGE,
            label: "Usage",
            icon: 'pi pi-info-circle',
            function: () => {
                window.dispatchEvent(new CustomEvent(COPILOT_EVENTS.TOOLBOX_USAGE, {
                    
                }));
            }
        },
        {
            id: COPILOT_TOOLBOX_IDS.PARAMETERS,
            label: 'Parameters',
            icon: 'pi pi-objects-column',
            function: () => {
                window.dispatchEvent(new CustomEvent(COPILOT_EVENTS.TOOLBOX_PARAMETERS, {
                    
                }));
            }
        },
        {
            id: COPILOT_TOOLBOX_IDS.DOWNSTREAMNODES,
            label: 'Downstream Nodes',
            icon: 'pi pi-arrow-circle-right',
            function: () => {
                window.dispatchEvent(new CustomEvent(COPILOT_EVENTS.TOOLBOX_DOWNSTREAMNODES, {

                }));
            }
        }
    ],
    // Return an array of command IDs to show in the selection toolbox
    // when an item is selected
    getSelectionToolboxCommands: (selectedItem) => [COPILOT_TOOLBOX_IDS.USAGE, COPILOT_TOOLBOX_IDS.PARAMETERS, COPILOT_TOOLBOX_IDS.DOWNSTREAMNODES]
})