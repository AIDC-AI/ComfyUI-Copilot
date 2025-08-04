/**
 * ComfyUI API Format to Workflow Format Converter
 * 
 * This utility converts API format (execution format) workflows to the standard
 * ComfyUI workflow format, enabling proper handling of missing nodes and 
 * automatic node installation suggestions.
 * 
 * For types:
 * npm install @comfyorg/comfyui-frontend-types
 */

import type { LGraph } from '@comfyorg/litegraph';
import type { 
  ComfyWorkflowJSON, 
  ComfyApiWorkflow,
  ComfyApp 
} from '@comfyorg/comfyui-frontend-types';

// Assuming these are available in the global scope when running as an extension
declare const LiteGraph: any;
declare const app: ComfyApp;

/**
 * 优化节点布局，基于WorkflowOption.tsx的逻辑
 * @param workflow - 工作流对象
 */
function optimizeNodeLayout(workflow: ComfyWorkflowJSON): void {
  const nodes = workflow.nodes;
  if (!nodes || nodes.length === 0) return;

  // 布局参数
  const base_size_x = 250;
  const base_size_y = 60;
  const param_y = 20;
  const align = 60;
  const align_y = 50;
  const max_size_y = 1000;
  
  // 起始位置
  const base_x = 100;
  const base_y = 100;
  
  let last_start_x = base_x;
  let last_start_y = base_y;
  let tool_size_y = 0;
  
  for (const node of nodes) {
    // 检查是否需要换列
    if (tool_size_y > max_size_y) {
      last_start_x += base_size_x + align;
      tool_size_y = 0;
      last_start_y = base_y;
    }

    // 根据参数计算节点的高度
    const inputCount = node.inputs ? node.inputs.length : 0;
    const outputCount = node.outputs ? node.outputs.length : 0;
    const widgetCount = node.widgets_values ? node.widgets_values.length : 0;
    const param_count = Math.max(inputCount, outputCount) + widgetCount;
    
    const size_y = param_y * param_count + base_size_y;
    
    // 设置节点大小和位置
    node.size = [base_size_x, size_y];
    node.pos = [last_start_x, last_start_y];

    tool_size_y += size_y + align_y;
    last_start_y += size_y + align_y;
  }
}

/**
 * Converts ComfyUI API format to workflow format with proper missing node handling.
 * 
 * This version handles both existing and missing node types by creating
 * placeholder nodes when necessary.
 * 
 * @param apiData - The workflow in API/execution format
 * @returns The workflow in standard ComfyUI format
 * 
 * @example
 * ```typescript
 * const apiWorkflow = {
 *   "1": {
 *     "class_type": "KSampler",
 *     "inputs": {
 *       "seed": 12345,
 *       "model": ["2", 0],
 *       "positive": ["3", 0]
 *     }
 *   }
 * };
 * 
 * const workflow = apiToWorkflow(apiWorkflow);
 * app.loadGraphData(workflow);
 * ```
 */
export function apiToWorkflow(apiData: ComfyApiWorkflow): ComfyWorkflowJSON {
  // Pre-allocate arrays based on expected size
  const nodeCount = Object.keys(apiData).length;
  const nodes: ComfyWorkflowJSON['nodes'] = [];
  const links: ComfyWorkflowJSON['links'] = [];
  
  // Maps for efficient lookups
  const nodeIdToIndex = new Map<string | number, number>();
  const nodeIndexToOutputs = new Map<number, number>();
  
  let linkId = 0;
  let maxNodeId = 0;
  
  // First pass: Create node structures
  let nodeIndex = 0;
  for (const [id, data] of Object.entries(apiData)) {
    const numericId = isNaN(+id) ? nodeIndex : +id;
    if (typeof numericId === 'number' && numericId > maxNodeId) {
      maxNodeId = numericId;
    }
    
    // Check if node type exists
    const nodeTypeExists = data.class_type in LiteGraph.registered_node_types;
    
    // Create node structure (position and size will be optimized later)
    const node: ComfyWorkflowJSON['nodes'][0] = {
      id: numericId,
      type: data.class_type,
      pos: [0, 0], // Temporary position, will be set by optimizeNodeLayout
      size: [210, 58], // Temporary size, will be set by optimizeNodeLayout
      flags: {},
      order: nodeIndex,
      mode: nodeTypeExists ? 0 : 4, // Mode 4 for missing nodes
      inputs: [],
      outputs: [],
      properties: {},
      widgets_values: []
    };
    
    // Add title if provided
    if (data._meta?.title) {
      node.title = data._meta.title;
    }
    
    // Store mapping
    nodeIdToIndex.set(id, nodeIndex);
    nodes.push(node);
    nodeIndex++;
  }
  
  // Second pass: Process inputs and create widget values/connections
  nodeIndex = 0;
  for (const [id, data] of Object.entries(apiData)) {
    const node = nodes[nodeIndex];
    const nodeTypeExists = data.class_type in LiteGraph.registered_node_types;
    
    // Separate widget values from connections
    const widgetInputs: Record<string, any> = {};
    const connectionInputs: Array<{name: string; value: [string, number]}> = [];
    
    for (const [inputName, inputValue] of Object.entries(data.inputs ?? {})) {
      if (Array.isArray(inputValue) && inputValue.length === 2 && 
          typeof inputValue[1] === 'number') {
        connectionInputs.push({ name: inputName, value: inputValue as [string, number] });
      } else {
        widgetInputs[inputName] = inputValue;
      }
    }
    
    // Process widget values
    if (nodeTypeExists) {
      // For existing nodes, get widget order from node definition
      const nodeType = LiteGraph.registered_node_types[data.class_type];
      try {
        const tempNode = new nodeType();
        if (tempNode.widgets) {
          for (const widget of tempNode.widgets) {
            if (widgetInputs.hasOwnProperty(widget.name)) {
              const value = widgetInputs[widget.name];
              node.widgets_values.push(
                value && typeof value === 'object' && '__value__' in value
                  ? value.__value__
                  : value
              );
              delete widgetInputs[widget.name];
            }
          }
        }
        // Clean up temp node - remove from any graph context
        tempNode.graph = null;
        tempNode.widgets = null;
        tempNode.inputs = null;
        tempNode.outputs = null;
      } catch (e) {
        // Fallback if node construction fails
      }
    }
    
    // Add any remaining widget values (for missing nodes or unmatched widgets)
    for (const [name, value] of Object.entries(widgetInputs)) {
      node.widgets_values.push(
        value && typeof value === 'object' && '__value__' in value
          ? value.__value__
          : value
      );
    }
    
    // Process connections
    for (const { name, value: [sourceId, sourceSlot] } of connectionInputs) {
      const sourceIndex = nodeIdToIndex.get(sourceId);
      if (sourceIndex === undefined) continue;
      
      const sourceNode = nodes[sourceIndex];
      
      // Create the link as an array [id, origin_id, origin_slot, target_id, target_slot, type]
      const currentLinkId = linkId++;
      const linkArray = [
        currentLinkId,
        sourceNode.id,
        sourceSlot,
        node.id,
        node.inputs.length,
        "unknown"  // Type will be determined later from node definitions
      ];
      links.push(linkArray);
      
      // Add input to target node
      node.inputs.push({
        name: name,
        type: "unknown",  // Type will be inferred from connections
        link: currentLinkId
      });
      
      // Ensure source node has enough outputs
      const currentOutputs = nodeIndexToOutputs.get(sourceIndex) ?? 0;
      if (sourceSlot >= currentOutputs) {
        for (let i = currentOutputs; i <= sourceSlot; i++) {
          sourceNode.outputs.push({
            name: `${sourceNode.type}_${i}`,
            type: "unknown",
            links: [],
            slot_index: i
          });
        }
        nodeIndexToOutputs.set(sourceIndex, sourceSlot + 1);
      }
      
      // Add link to source output
      sourceNode.outputs[sourceSlot].links!.push(currentLinkId);
    }
    
    nodeIndex++;
  }
  
  // Clear temporary maps
  nodeIdToIndex.clear();
  nodeIndexToOutputs.clear();
  
  // Create final workflow
  const workflow: ComfyWorkflowJSON = {
    last_node_id: maxNodeId + 1,
    last_link_id: linkId,
    nodes: nodes,
    links: links,
    groups: [],
    config: {},
    extra: {},
    version: 0.4
  };
  
  // 应用优化的节点布局
  optimizeNodeLayout(workflow);
  
  return workflow;
}

/**
 * Adds ComfyUI Registry metadata to nodes for automatic installation suggestions.
 * 
 * This is OPTIONAL. When a node is missing, ComfyUI will:
 * - Use the provided cnr_id if you specify it for precise matching
 * - Otherwise use fuzzy searching to find node packs containing nodes with matching names
 * 
 * You can find node pack IDs at https://registry.comfy.org/
 * 
 * @param workflow - The workflow to enhance with registry metadata
 * @param nodeMetadata - Mapping of node types to their registry metadata
 * 
 * @example
 * ```typescript
 * // Optional: Only needed if you want specific node pack suggestions
 * const nodeMetadata = {
 *   "WanVideoTextEmbedBridge": {
 *     cnr_id: "ComfyUI-WanVideoWrapper",  // Node pack ID from registry
 *     ver: "d20baf00247fd06553fdc9253e18732244e54172"  // Optional specific version
 *   },
 *   "MyCustomNode": {
 *     cnr_id: "my-node-pack"  // Will suggest this specific pack
 *   }
 *   // Nodes without metadata will use fuzzy search
 * };
 * 
 * addCNRMetadata(workflow, nodeMetadata);
 * ```
 */
export function addCNRMetadata(
  workflow: ComfyWorkflowJSON, 
  nodeMetadata: Record<string, { cnr_id: string; ver?: string }>
): void {
  for (const node of workflow.nodes) {
    const metadata = nodeMetadata[node.type];
    if (metadata) {
      // Initialize properties if not exists
      if (!node.properties) {
        node.properties = {};
      }
      
      // Add CNR metadata
      node.properties.cnr_id = metadata.cnr_id;
      if (metadata.ver) {
        node.properties.ver = metadata.ver;
      }
      
      // Preserve the original node type for reference
      node.properties["Node name for S&R"] = node.type;
    }
  }
}

/**
 * Converts API format to workflow format and loads it with proper missing node handling.
 * 
 * This is the main entry point for extension authors who want to load LLM-generated
 * workflows that are in API format.
 * 
 * @param apiData - The workflow in API format
 * @param fileName - Optional filename for the workflow
 * @param nodeMetadata - Optional registry metadata for specific node pack suggestions
 * 
 * @example
 * ```typescript
 * // Simple usage - will use fuzzy search for missing nodes
 * loadApiWorkflowWithMissingNodes(llmGeneratedWorkflow);
 * 
 * // With specific node pack suggestions (optional)
 * const metadata = {
 *   "CustomNode": { cnr_id: "my-custom-nodes", ver: "1.0.0" }
 * };
 * loadApiWorkflowWithMissingNodes(llmGeneratedWorkflow, "LLM Generated", metadata);
 * ```
 */
export function loadApiWorkflowWithMissingNodes(
  apiData: ComfyApiWorkflow, 
  fileName: string = "API Workflow",
  nodeMetadata?: Record<string, { cnr_id: string; ver?: string }>
): void {
  // Convert API format to workflow format
  const workflow = apiToWorkflow(apiData);
  
  // Add CNR metadata if provided
  if (nodeMetadata) {
    addCNRMetadata(workflow, nodeMetadata);
  }
  
  // Load using the standard workflow loader which handles missing nodes properly
  app.loadGraphData(workflow, true, true, fileName, {
    showMissingNodesDialog: true,
    showMissingModelsDialog: true
  });
}

// ============================================================================
// USAGE EXAMPLES
// ============================================================================

/**
 * Example 1: Basic API format workflow
 */
const exampleApiWorkflow: ComfyApiWorkflow = {
  "1": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "2": {
    "inputs": {
      "text": "a beautiful landscape",
      "clip": ["1", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "Positive Prompt"
    }
  },
  "3": {
    "inputs": {
      "text": "blurry, low quality",
      "clip": ["1", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "Negative Prompt"
    }
  },
  "4": {
    "inputs": {
      "seed": 12345,
      "steps": 20,
      "cfg": 7.5,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0,
      "model": ["1", 0],
      "positive": ["2", 0],
      "negative": ["3", 0],
      "latent_image": ["5", 0]
    },
    "class_type": "KSampler"
  },
  "5": {
    "inputs": {
      "width": 1024,
      "height": 1024,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
  }
};

/**
 * Example 2: Workflow with custom nodes and CNR metadata
 */
const customNodeWorkflow: ComfyApiWorkflow = {
  "1": {
    "inputs": {
      "text": "hello world"
    },
    "class_type": "CustomTextProcessor"
  },
  "2": {
    "inputs": {
      "image": ["1", 0],
      "strength": 0.8
    },
    "class_type": "CustomImageEnhancer"
  }
};

// CNR metadata for automatic installation suggestions
const customNodeMetadata = {
  "CustomTextProcessor": {
    cnr_id: "my-text-nodes",
    ver: "2.1.0"
  },
  "CustomImageEnhancer": {
    cnr_id: "my-image-nodes",
    ver: "1.5.3"
  }
};

/**
 * Example 3: How to use in your LLM extension
 */
export class LLMWorkflowExtension {
  async generateAndLoadWorkflow(prompt: string) {
    try {
      // 1. Generate workflow using your LLM (returns API format)
      const apiWorkflow = await this.callLLM(prompt);
      
      // 2. Define CNR metadata for any custom nodes your LLM might use
      const nodeMetadata = {
        "YourCustomNode": {
          cnr_id: "your-node-pack",
          ver: "latest"
        }
      };
      
      // 3. Load the workflow with proper missing node handling
      loadApiWorkflowWithMissingNodes(
        apiWorkflow,
        `LLM: ${prompt.substring(0, 50)}...`,
        nodeMetadata
      );
      
    } catch (error) {
      console.error("[LLM Extension] Failed to generate workflow:", error);
    }
  }
  
  private async callLLM(prompt: string): Promise<ComfyApiWorkflow> {
    // Your LLM API call here
    // Returns workflow in API format
    return {};
  }
}

/**
 * Example 4: Real-world example with WanVideo nodes
 * 
 * This shows how nodes with CNR metadata appear in the workflow format.
 * When these nodes are missing, ComfyUI will show installation suggestions.
 */
const simpleExample: ComfyWorkflowJSON = {
  "id": "00000000-0000-0000-0000-000000000000",
  "revision": 0,
  "last_node_id": 8,
  "last_link_id": 10,
  "nodes": [
    {
      "id": 1,
      "type": "CheckpointLoaderSimple",
      "pos": [
        687.7930297851562,
        -31.296039581298828
      ],
      "size": [
        315,
        98
      ],
      "flags": {},
      "order": 0,
      "mode": 0,
      "inputs": [],
      "outputs": [
        {
          "name": "MODEL",
          "type": "MODEL",
          "slot_index": 0,
          "links": [
            1,
            1
          ]
        },
        {
          "name": "CLIP",
          "type": "CLIP",
          "slot_index": 1,
          "links": [
            3,
            5,
            3,
            4
          ]
        },
        {
          "name": "VAE",
          "type": "VAE",
          "slot_index": 2,
          "links": [
            8,
            7
          ]
        }
      ],
      "properties": {
        "widget_ue_connectable": {},
        "Node name for S&R": "CheckpointLoaderSimple"
      },
      "widgets_values": [
        "flux1-dev-fp8.safetensors"
      ]
    },
    {
      "id": 2,
      "type": "CLIPTextEncode",
      "pos": [
        1114.2213134765625,
        -19.439258575439453
      ],
      "size": [
        425.27801513671875,
        180.6060791015625
      ],
      "flags": {
        "collapsed": true
      },
      "order": 3,
      "mode": 0,
      "inputs": [
        {
          "name": "clip",
          "type": "CLIP",
          "link": 4
        }
      ],
      "outputs": [
        {
          "name": "CONDITIONING",
          "type": "CONDITIONING",
          "slot_index": 0,
          "links": [
            6,
            5
          ]
        }
      ],
      "properties": {
        "widget_ue_connectable": {},
        "Node name for S&R": "CLIPTextEncode"
      },
      "widgets_values": [
        ""
      ]
    },
    {
      "id": 3,
      "type": "SaveImage",
      "pos": [
        1891.88720703125,
        -318.9201354980469
      ],
      "size": [
        427.60394287109375,
        432.4823303222656
      ],
      "flags": {},
      "order": 4,
      "mode": 0,
      "inputs": [
        {
          "name": "images",
          "type": "IMAGE",
          "link": 8
        }
      ],
      "outputs": [],
      "properties": {
        "widget_ue_connectable": {},
        "Node name for S&R": "SaveImage"
      },
      "widgets_values": [
        "ComfyUI"
      ]
    },
    {
      "id": 4,
      "type": "FluxGuidance",
      "pos": [
        1531.7930908203125,
        -315.2960510253906
      ],
      "size": [
        315,
        58
      ],
      "flags": {},
      "order": 5,
      "mode": 0,
      "inputs": [
        {
          "name": "conditioning",
          "type": "CONDITIONING",
          "link": 10
        }
      ],
      "outputs": [
        {
          "name": "CONDITIONING",
          "type": "CONDITIONING",
          "slot_index": 0,
          "links": [
            10,
            9
          ]
        }
      ],
      "properties": {
        "widget_ue_connectable": {},
        "Node name for S&R": "FluxGuidance"
      },
      "widgets_values": [
        3.5
      ]
    },
    {
      "id": 5,
      "type": "KSampler",
      "pos": [
        1532.7786865234375,
        -191.07691955566406
      ],
      "size": [
        315,
        262
      ],
      "flags": {},
      "order": 7,
      "mode": 0,
      "inputs": [
        {
          "name": "model",
          "type": "MODEL",
          "link": 1
        },
        {
          "name": "positive",
          "type": "CONDITIONING",
          "link": 9
        },
        {
          "name": "negative",
          "type": "CONDITIONING",
          "link": 5
        },
        {
          "name": "latent_image",
          "type": "LATENT",
          "link": 2
        }
      ],
      "outputs": [
        {
          "name": "LATENT",
          "type": "LATENT",
          "slot_index": 0,
          "links": [
            7,
            6
          ]
        }
      ],
      "properties": {
        "widget_ue_connectable": {},
        "Node name for S&R": "KSampler"
      },
      "widgets_values": [
        156680208700286,
        "randomize",
        20,
        1,
        "deis",
        "simple",
        1
      ]
    },
    {
      "id": 6,
      "type": "VAEDecode",
      "pos": [
        1641.7930908203125,
        134.70396423339844
      ],
      "size": [
        210,
        46
      ],
      "flags": {},
      "order": 6,
      "mode": 0,
      "inputs": [
        {
          "name": "samples",
          "type": "LATENT",
          "link": 6
        },
        {
          "name": "vae",
          "type": "VAE",
          "link": 7
        }
      ],
      "outputs": [
        {
          "name": "IMAGE",
          "type": "IMAGE",
          "slot_index": 0,
          "links": [
            9,
            8
          ]
        }
      ],
      "properties": {
        "widget_ue_connectable": {},
        "Node name for S&R": "VAEDecode"
      }
    },
    {
      "id": 7,
      "type": "EmptyLatentImage",
      "pos": [
        1126.6373291015625,
        96.14139556884766
      ],
      "size": [
        315,
        106
      ],
      "flags": {},
      "order": 1,
      "mode": 0,
      "inputs": [],
      "outputs": [
        {
          "name": "LATENT",
          "type": "LATENT",
          "slot_index": 0,
          "links": [
            2,
            2
          ]
        }
      ],
      "properties": {
        "widget_ue_connectable": {},
        "Node name for S&R": "EmptyLatentImage"
      },
      "widgets_values": [
        512,
        512,
        1
      ]
    },
    {
      "id": 8,
      "type": "CLIPTextEncode",
      "pos": [
        1075.120849609375,
        -315.2674865722656
      ],
      "size": [
        422.84503173828125,
        164.31304931640625
      ],
      "flags": {},
      "order": 2,
      "mode": 0,
      "inputs": [
        {
          "name": "clip",
          "type": "CLIP",
          "link": 3
        }
      ],
      "outputs": [
        {
          "name": "CONDITIONING",
          "type": "CONDITIONING",
          "slot_index": 0,
          "links": [
            11,
            10
          ]
        }
      ],
      "properties": {
        "widget_ue_connectable": {},
        "Node name for S&R": "CLIPTextEncode"
      },
      "widgets_values": [
        "beautiful scenery nature glass bottle landscape, , purple galaxy bottle,"
      ]
    }
  ],
  "links": [
    [
      1,
      1,
      0,
      5,
      0,
      "MODEL"
    ],
    [
      2,
      7,
      0,
      5,
      3,
      "LATENT"
    ],
    [
      3,
      1,
      1,
      8,
      0,
      "CLIP"
    ],
    [
      4,
      1,
      1,
      2,
      0,
      "CLIP"
    ],
    [
      5,
      2,
      0,
      5,
      2,
      "CONDITIONING"
    ],
    [
      6,
      5,
      0,
      6,
      0,
      "LATENT"
    ],
    [
      7,
      1,
      2,
      6,
      1,
      "VAE"
    ],
    [
      8,
      6,
      0,
      3,
      0,
      "IMAGE"
    ],
    [
      9,
      4,
      0,
      5,
      1,
      "CONDITIONING"
    ],
    [
      10,
      8,
      0,
      4,
      0,
      "CONDITIONING"
    ]
  ],
  "groups": [],
  "config": {},
  "extra": {
    "ue_links": [],
    "ds": {
      "scale": 0.7247295000000004,
      "offset": [
        -330.427808521672,
        638.4239195808423
      ]
    },
    "frontendVersion": "1.22.2"
  },
  "version": 0.4
};