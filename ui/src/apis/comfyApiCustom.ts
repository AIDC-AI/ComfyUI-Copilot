// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

import { api } from "../utils/comfyapp";
import type { ComfyApi } from "@comfyorg/comfyui-frontend-types";

type ObjectInfo = ReturnType<ComfyApi["getNodeDefs"]>;

export async function getObjectInfo(): Promise<ObjectInfo> {
  try {
    const response = await api.fetchApi("/object_info", { method: "GET" });
    return await response.json();
  } catch (error) {
    console.error("Error fetching object info:", error);
    throw error;
  }
}

export async function getInstalledNodes() {
  const objectInfos = await getObjectInfo();
  return Object.keys(objectInfos);
}
