/*
 * @Author: ai-business-hql qingli.hql@alibaba-inc.com
 * @Date: 2025-02-17 20:53:45
 * @LastEditors: ai-business-hql qingli.hql@alibaba-inc.com
 * @LastEditTime: 2025-08-06 11:51:11
 * @FilePath: /comfyui_copilot/ui/src/utils/graphUtils.ts
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import LiteGraph from "../types/litegraph.d";
import { app } from "./comfyapp";
import { loadApiWorkflowWithMissingNodes } from "./comfyuiWorkflowApi2Ui";

export function addNodeOnGraph(type: string, options: any = {}) {
    const node = LiteGraph.createNode(type, "", options);

    // 只在没有指定位置时，才设置节点到中心位置
    if (!options.pos) {
        // 获取画布的可视区域大小
        const rect = app.canvas.canvas.getBoundingClientRect();

        // // 计算画布中心点
        // const centerX = (rect.width / 2) / app.canvas.ds.scale + (-app.canvas.ds.offset[0]) / app.canvas.ds.scale;
        // const centerY = (rect.height / 2) / app.canvas.ds.scale + (-app.canvas.ds.offset[1]) / app.canvas.ds.scale;
        // // 设置节点位置到画布中心
        // node.pos = [
        //     centerX - node.size[0] / 2,
        //     centerY - node.size[1] / 2
        // ]

        const areaX = app.canvas.visible_area?.[0] || 0;
        const areaY = app.canvas.visible_area?.[1] || 0;
        node.pos = [
            areaX + rect.width / app.canvas.ds.scale / 2 - node.size[0] / 2,
            areaY + rect.height / app.canvas.ds.scale / 2 - node.size[1] / 2
        ]
    }

    app.graph.add(node);
    return node;
}


export function applyNewWorkflow(workflow: any): boolean {
    try {
        console.log('[graphUtils] Applying new workflow to canvas...', workflow);

        // 确保app和graph对象存在
        if (!app || !app.graph) {
            console.error('[graphUtils] App or graph not available');
            return false;
        }

        // ui格式的工作流
        if (workflow.nodes) {
            console.log('[graphUtils] Loading UI format workflow with nodes:', workflow.nodes.length);
            app.loadGraphData(workflow);
        } else {
            // api格式的工作流
            console.log('[graphUtils] Loading API format workflow with node count:', Object.keys(workflow).length);
            // app.loadApiJson(workflow);
            loadApiWorkflowWithMissingNodes(workflow);
        }

        // 确保画布重新渲染
        if (app.graph) {
            app.graph.setDirtyCanvas(false, true);
            console.log('[graphUtils] Canvas marked as dirty for re-rendering');
        }

        console.log('[graphUtils] Workflow successfully applied to canvas');
        return true;
    } catch (error) {
        console.error('[graphUtils] Error applying new workflow:', error);
        return false;
    }
}

/**
 * 应用节点参数修改到画布
 * @param nodeParams - 节点参数对象，格式: { nodeId: { paramName: value } }
 * @returns 是否成功应用参数
 */
export function applyNodeParameters(nodeParams: Record<string, Record<string, any>>): boolean {
    try {
        if (!app.graph || !nodeParams) {
            console.warn('[graphUtils] Invalid graph or nodeParams');
            return false;
        }

        let hasChanges = false;

        // 遍历所有节点参数
        Object.entries(nodeParams).forEach(([nodeId, params]) => {
            // 获取节点
            const node = app.graph._nodes_by_id[nodeId];
            if (!node || !node.widgets) {
                console.warn(`[graphUtils] Node ${nodeId} not found or has no widgets`);
                return;
            }

            // 遍历节点参数
            Object.entries(params).forEach(([paramName, value]) => {
                // 在节点的widgets中查找对应的widget
                for (const widget of node.widgets) {
                    if (widget.name === paramName) {
                        // 设置widget的值
                        if (widget.value !== value) {
                            widget.value = value;
                            hasChanges = true;
                            console.log(`[graphUtils] Updated node ${nodeId}, parameter ${paramName} to:`, value);
                        }
                        break;
                    }
                }
            });
        });

        // 如果有修改，标记画布为dirty并触发重新渲染
        if (hasChanges) {
            app.graph.setDirtyCanvas(false, true);
            console.log('[graphUtils] Applied node parameters and marked canvas as dirty');
        }

        return hasChanges;
    } catch (error) {
        console.error('[graphUtils] Error applying node parameters:', error);
        return false;
    }
}

/**
 * 应用参数修改列表到画布
 * @param changes - 参数修改列表，每个元素包含 node_id, parameter, new_value
 * @returns 是否成功应用参数
 */
export function applyParameterChanges(changes: Array<{ node_id: string; parameter: string; new_value: any }>): boolean {
    try {
        if (!changes || changes.length === 0) {
            console.warn('[graphUtils] No changes to apply');
            return false;
        }

        // 将changes列表转换为nodeParams格式
        const nodeParams: Record<string, Record<string, any>> = {};

        changes.forEach(change => {
            if (!nodeParams[change.node_id]) {
                nodeParams[change.node_id] = {};
            }
            nodeParams[change.node_id][change.parameter] = change.new_value;
        });

        return applyNodeParameters(nodeParams);
    } catch (error) {
        console.error('[graphUtils] Error applying parameter changes:', error);
        return false;
    }
}

