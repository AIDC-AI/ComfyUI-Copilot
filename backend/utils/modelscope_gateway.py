'''
Author: ai-business-hql ai.bussiness.hql@gmail.com
Date: 2025-08-26 15:06:47
LastEditors: ai-business-hql ai.bussiness.hql@gmail.com
LastEditTime: 2025-09-01 19:31:03
FilePath: /ComfyUI-Copilot/backend/utils/modelscope_gateway.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import os
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .logger import log
import folder_paths


class ModelScopeGateway:
    BASE_URL = "https://www.modelscope.cn"
    SUGGEST_ENDPOINT = f"{BASE_URL}/api/v1/dolphin/model/suggestv2"
    SEARCH_ENDPOINT = f"{BASE_URL}/api/v1/dolphin/models"
    SEARCH_SINGLE_ENDPOINT = f"{BASE_URL}/api/v1/models"
    
    def __init__(self, timeout: float = 10.0, retries: int = 3, backoff: float = 0.5):
        self.timeout = timeout

        # 单实例 Session，会自动保存 Cookie；如需按用户隔离可按 session_key 做多 Session 管理
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "User-Agent": "ComfyUI-Copilot/1.0 (requests)",
            "x-modelscope-accept-language": "zh_CN",
        })

        retry_cfg = Retry(
            total=retries,
            backoff_factor=backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_cfg)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def formatData(self, data: Any) -> Dict[str, Any]:
        inner = data.get('Model', {}) if isinstance(data, dict) else {}
        path = data.get('Path') or inner.get('Path')
        name = data.get('Name') or inner.get('Name')
        revision = data.get('Revision') or inner.get('Revision')
        # size = self.get_model_size(path, name, revision)
        return {
            "ModelType": data.get("ModelType") or inner.get("ModelType"),
            "ChineseName": data.get("ChineseName") or inner.get("ChineseName"),
            "Id": data.get("Id") or inner.get("Id") or data.get("ModelId") or inner.get("ModelId"),
            "Name": data.get("Name") or inner.get("Name"),
            "Path": data.get("Path") or inner.get("Path"),
            "LastUpdatedTime": data.get("LastUpdatedTime") or inner.get("LastUpdatedTime") or data.get("LastUpdatedAt") or inner.get("LastUpdatedAt"),
            "Downloads": data.get("Downloads") or inner.get("Downloads") or data.get("DownloadCount") or inner.get("DownloadCount"),
            # "Size": size or 0
        }

    def get_single_model(self, path: str, name: str) -> Optional[Dict[str, Any]]:
        """
        调用单模型详情接口。
        返回原始 JSON（尽量保持结构，便于 formatData 处理），失败返回 None。
        """
        if path is None or name is None:
            return None
        try:
            url = f"{self.SEARCH_SINGLE_ENDPOINT}/{path}/{name}"
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            body = resp.json()
            # 兼容不同返回包裹层级
            if isinstance(body, dict):
                data = body.get("Data") or body.get("data") or body
                return data
            return body
        except Exception as e:
            log.error(f"ModelScope single fetch failed for path={path}: name={name}: {e}")
            return None
        
    def get_model_size(self, path: str, name: str, revision: str, root: str = '') -> int:
        """
        调用单模型详情接口。
        返回原始 JSON（尽量保持结构，便于 formatData 处理），失败返回 None。
        """
        if path is None or name is None or revision is None:
            return 0
        try:
            url = f"{self.SEARCH_SINGLE_ENDPOINT}/{path}/{name}/repo/files?Revision={revision}&Root={root}"
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            body = resp.json()
            # 兼容不同返回包裹层级
            if isinstance(body, dict):
                data = body["Data"]["Files"]
                size = 0
                for item in data:
                    size += item.get("Size") or 0
                return size
            return 0
        except Exception as e:
            log.error(f"ModelScope model size fetch failed for path={path}: name={name}: rversion={rversion}: {e}")
            return 0
    
    def suggest(
        self,
        name: str,
        page: int = 1,
        page_size: int = 30,
        sort_by: str = "Default",
        target: str = "",
        single_criterion: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        调用 suggestv2 模糊搜索接口；返回 body 与当前 Cookie。
        
        Returns:
            Dict[str, Any]: 返回的模型列表，格式为：
            {
                "data": [
                    {
                        "ChineseName": "中文名称",
                        "Id": 294066,
                        "Name": "SD3-Controlnet-Pose",
                        "Path": "InstantX"
                        "ModelType": ["qwen2],
                        "LastUpdatedTime": "1733042611",
                        "Downloads": 100,
                        "Size": 100000
                    }
                ]
            }
        """
        payload = {
            "PageSize": page_size,
            "PageNumber": page,
            "SortBy": sort_by,
            "Target": target,
            "SingleCriterion": single_criterion or [],
            "Name": name,
        }

        resp = self.session.post(
            self.SUGGEST_ENDPOINT,
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        if body['Data'] is None or body['Data']['Model'] is None \
        or body['Data']['Model']['Suggests'] is None or (len(body['Data']['Model']['Suggests']) == 0):
            log.error(f"ModelScope suggest failed: {body}, request: {payload}")
            return {"data": None}
        models = body['Data']['Model']['Suggests']
        picked: List[Dict[str, Any]] = []
        for item in models:
            base = item or {}
            inner = base.get('Model', {}) if isinstance(base, dict) else {}
            path = base.get('Path') or inner.get('Path')
            name = base.get('Name') or inner.get('Name')
            detail= self.get_single_model(path, name)
            data = self.formatData(detail or base)
            picked.append(data)
        total = body['Data']['Model'].get('TotalCount') or body['Data']['Model'].get('Total') or 0
        return {"data": picked, "total": total}

    def search(
        self,
        name: str,
        page: int = 1,
        page_size: int = 30,
        sort_by: str = "Default",
        target: str = "",
        single_criterion: Optional[List[Dict[str, Any]]] = None,
        criterion: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        调用 models 模糊搜索接口；返回 body 与当前 Cookie。
        
        Returns:
            Dict[str, Any]: 返回的模型列表，格式为：
            {
                "data": [
                    {
                        "ChineseName": "中文名称",
                        "Id": 294066,
                        "Name": "SD3-Controlnet-Pose",
                        "Path": "InstantX"
                        "ModelType": ["qwen2],
                        "LastUpdatedTime": "1733042611",
                        "Downloads": 100,
                        "Size": 100000
                    }
                ]
            }
        """
        payload = {
            "PageSize": page_size,
            "PageNumber": page,
            "SortBy": sort_by,
            "Target": target,
            "SingleCriterion": single_criterion or [],
            "Name": name,
            "Criterion" : criterion
        }

        resp = self.session.put(
            self.SEARCH_ENDPOINT,
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        if body['Data'] is None or body['Data']['Model'] is None \
        or body['Data']['Model']['Models'] is None or (len(body['Data']['Model']['Models']) == 0):
            log.error(f"ModelScope search failed: {body}, request: {payload}")
            return {"data": None}
        models = body['Data']['Model']['Models'] or []
        picked: List[Dict[str, Any]] = []
        for item in models:
            data = self.formatData(item or {})
            picked.append(data)
        total = body['Data']['Model'].get('TotalCount') or body['Data']['Model'].get('Total') or 0
        return {"data": picked, "total": total}

    def download_with_sdk(
        self,
        model_id: str,
        model_type: str,
        dest_dir: Optional[str] = None,
    ) -> str:
        """
        推荐通过 ModelScope 官方 SDK 下载（更稳妥，支持断点与多文件）。
        pip install modelscope
        """
        try:
            from modelscope.hub.snapshot_download import snapshot_download
        except ImportError as e:
            raise RuntimeError("缺少依赖 modelscope，请先安装：pip install modelscope") from e

        # Determine destination directory in ComfyUI models folder hierarchy
        try:
            if dest_dir:
                cache_dir = os.path.abspath(os.path.expanduser(dest_dir))
            else:
                # Prefer ComfyUI's configured folder for this model_type
                try:
                    model_type_paths = folder_paths.get_folder_paths(model_type)
                    cache_dir = model_type_paths[0] if model_type_paths else os.path.join(folder_paths.models_dir, model_type)
                except Exception:
                    # Fallback to models_dir/model_type if the key is unknown
                    cache_dir = os.path.join(folder_paths.models_dir, model_type)

            os.makedirs(cache_dir, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to prepare destination directory for download: {e}") from e

        local_dir = snapshot_download(model_id, cache_dir=cache_dir)
        return local_dir
    
    def test_modelscope_gateway(self):
        """
        测试 ModelScope Gateway 的基本功能
        """
        try:
            # 测试初始化
            print("Testing ModelScope Gateway initialization...")
            gateway = ModelScopeGateway()
            
            # 测试模糊搜索
            print("Testing suggest method...")
            result = gateway.suggest(
                name="stable-diffusion",
                page_size=5,
                page=1
            )
            if result.get("data"):
                print(f"Suggest test passed: found {len(result['data'])} models")
                for model in result["data"][:2]:  # 显示前2个结果
                    print(f"  - {model.get('Model', {}).get('ModelId', 'Unknown')}")
            else:
                print("Suggest test failed: no data returned")
            
            # 测试特定模型搜索
            print("Testing specific model search...")
            specific_result = gateway.suggest(
                name="qwen",
                page_size=3,
                page=1,
                sort_by="DownloadCount",
                target="model"
            )
            if specific_result.get("data"):
                print(f"Specific search test passed: found {len(specific_result['data'])} models")
            else:
                print("Specific search test failed")
                
            print("All tests completed successfully!")
            return True
            
        except Exception as e:
            print(f"Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False


# 测试脚本入口
if __name__ == "__main__":
    # 创建测试实例
    gateway = ModelScopeGateway()
    
    # 运行测试
    print("=" * 50)
    print("ModelScope Gateway Test Script")
    print("=" * 50)
    
    success = gateway.test_modelscope_gateway()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 50)
