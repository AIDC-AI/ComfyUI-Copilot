import threading
import asyncio
import time
import server
from aiohttp import web
import os
import shutil
from ..utils.logger import log
from ..utils.modelscope_gateway import ModelScopeGateway
import folder_paths


# 全局下载进度存储
download_progress = {}
download_lock = threading.Lock()

# 下载进度回调类
class DownloadProgressCallback:
    def __init__(self, id: str, filename: str, file_size: int, download_id: str):
        self.id = id
        self.filename = filename
        self.file_size = file_size
        self.download_id = download_id
        self.progress = 0
        self.status = "downloading"  # downloading, completed, failed
        self.error_message = None
        self.start_time = time.time()

        # 初始化进度记录
        with download_lock:
            download_progress[download_id] = {
                "id": id,
                "filename": filename,
                "file_size": file_size,
                "progress": 0,
                "percentage": 0.0,
                "status": "downloading",
                "start_time": self.start_time,
                "estimated_time": None,
                "speed": 0.0,
                "error_message": None
            }

    def update(self, size: int):
        """更新下载进度"""
        self.progress += size
        current_time = time.time()
        elapsed_time = current_time - self.start_time

        # 计算下载速度和预估时间
        if elapsed_time > 0:
            speed = self.progress / elapsed_time  # bytes per second
            if speed > 0 and self.progress < self.file_size:
                remaining_bytes = self.file_size - self.progress
                estimated_time = remaining_bytes / speed
            else:
                estimated_time = None
        else:
            speed = 0.0
            estimated_time = None

        percentage = (self.progress / self.file_size) * 100 if self.file_size > 0 else 0

        # 更新全局进度
        with download_lock:
            if self.download_id in download_progress:
                # 直接更新字典的值，而不是调用update方法
                progress_dict = download_progress[self.download_id]
                progress_dict["progress"] = self.progress
                progress_dict["percentage"] = round(percentage, 2)
                progress_dict["speed"] = round(speed, 2)
                progress_dict["estimated_time"] = round(estimated_time, 2) if estimated_time else None

    def end(self, success: bool = True, error_message: str = None):
        """下载结束回调"""
        current_time = time.time()
        total_time = current_time - self.start_time

        if success:
            self.status = "completed"
            # 验证下载完整性
            assert self.progress == self.file_size, f"Download incomplete: {self.progress}/{self.file_size}"
        else:
            self.status = "failed"
            self.error_message = error_message

        # 更新最终状态
        with download_lock:
            if self.download_id in download_progress:
                # 直接更新字典的值，而不是调用update方法
                progress_dict = download_progress[self.download_id]
                progress_dict["status"] = self.status
                progress_dict["progress"] = self.file_size if success else self.progress
                if self.file_size > 0:
                    progress_dict["percentage"] = 100.0 if success else (self.progress / self.file_size) * 100
                else:
                    progress_dict["percentage"] = 0.0
                progress_dict["total_time"] = round(total_time, 2)
                progress_dict["error_message"] = self.error_message

    def fail(self, error_message: str):
        """下载失败回调"""
        self.end(success=False, error_message=error_message)


# 生成唯一下载ID
def generate_download_id() -> str:
    import uuid
    return str(uuid.uuid4())


@server.PromptServer.instance.routes.post("/api/download-model")
async def download_model(request):
    """
    Download model from ModelScope using SDK
    """
    log.info("Received download-model request")
    req_json = await request.json()

    try:
        id = req_json.get('id')
        model_id = req_json.get('model_id')
        model_type = req_json.get('model_type')
        dest_dir = req_json.get('dest_dir')

        # 验证必需参数
        if not id:
            return web.json_response({
                "success": False,
                "message": "Missing required parameter: id"
            })

        if not model_id:
            return web.json_response({
                "success": False,
                "message": "Missing required parameter: model_id"
            })

        if not model_type:
            return web.json_response({
                "success": False,
                "message": "Missing required parameter: model_type"
            })

        log.info(f"Downloading model: {model_id} (type: {model_type})")

        # 生成下载ID
        download_id = generate_download_id()

        # 计算目标目录：优先使用传入的dest_dir，否则使用ComfyUI的models目录下对应类型
        resolved_dest_dir = None
        if dest_dir:
            resolved_dest_dir = os.path.abspath(os.path.expanduser(f"models/{dest_dir}"))
        else:
            try:
                model_type_paths = folder_paths.get_folder_paths(model_type)
                resolved_dest_dir = model_type_paths[0] if model_type_paths else os.path.join(folder_paths.models_dir,
                                                                                              model_type)
            except Exception:
                resolved_dest_dir = os.path.join(folder_paths.models_dir, model_type)

        # 创建进度回调
        progress_callback = DownloadProgressCallback(
            id=id,
            filename=f"{model_id}.{model_type}",
            file_size=0,  # 实际大小会在下载过程中获取
            download_id=download_id
        )

        # 启动下载任务（异步执行）
        async def download_task():
            try:
                # 调用下载方法 - 使用snapshot_download
                from modelscope import snapshot_download

                # 创建进度回调包装器 - 实现ModelScope期望的接口
                class ProgressWrapper:
                    """Factory that returns a per-file progress object with update/end."""

                    def __init__(self, download_id: str):
                        self.download_id = download_id

                    def __call__(self, file_name: str, file_size: int):
                        # Create a per-file progress tracker expected by ModelScope
                        download_id = self.download_id

                        class _PerFileProgress:
                            def __init__(self, fname: str, fsize: int):
                                self.file_name = fname
                                self.file_size = max(int(fsize or 0), 0)
                                self.progress = 0
                                self.last_update_time = time.time()
                                self.last_downloaded = 0
                                with download_lock:
                                    if download_id in download_progress:
                                        # If unknown size, keep 0 to avoid div-by-zero
                                        download_progress[download_id]["file_size"] = self.file_size

                            def update(self, size: int):
                                try:
                                    self.progress += int(size or 0)
                                    now = time.time()
                                    # Update global progress
                                    with download_lock:
                                        if download_id in download_progress:
                                            dp = download_progress[download_id]
                                            dp["progress"] = self.progress
                                            if self.file_size > 0:
                                                dp["percentage"] = round(self.progress * 100.0 / self.file_size, 2)
                                            # speed
                                            elapsed = max(now - self.last_update_time, 1e-6)
                                            speed = (self.progress - self.last_downloaded) / elapsed
                                            dp["speed"] = round(speed, 2)
                                    self.last_update_time = now
                                    self.last_downloaded = self.progress
                                except Exception as e:
                                    log.error(f"Error in progress update: {e}")

                            def end(self):
                                # Called by modelscope when a file finishes
                                with download_lock:
                                    if download_id in download_progress:
                                        dp = download_progress[download_id]
                                        if self.file_size > 0:
                                            dp["progress"] = self.file_size
                                            dp["percentage"] = 100.0

                        return _PerFileProgress(file_name, file_size)

                progress_wrapper = ProgressWrapper(download_id)

                # 添加调试日志
                log.info(f"Starting download with progress wrapper: {download_id}")

                # 在线程中执行阻塞的下载，避免阻塞事件循环
                from functools import partial
                local_dir = await asyncio.to_thread(
                    partial(
                        snapshot_download,
                        model_id=model_id,
                        cache_dir=resolved_dest_dir,
                        progress_callbacks=[progress_wrapper]
                    )
                )

                # 下载完成
                progress_callback.end(success=True)
                log.info(f"Model downloaded successfully to: {local_dir}")

                # 下载后遍历目录，将所有重要权重/资源文件移动到最外层（与目录同级，即 resolved_dest_dir）
                try:
                    moved_count = 0
                    allowed_exts = {
                        ".safetensors", ".ckpt", ".pt", ".pth", ".bin"
                        # ".msgpack", ".json", ".yaml", ".yml", ".toml", ".png", ".onnx"
                    }
                    for root, dirs, files in os.walk(local_dir):
                        for name in files:
                            ext = os.path.splitext(name)[1].lower()
                            if ext in allowed_exts:
                                src_path = os.path.join(root, name)
                                target_dir = resolved_dest_dir
                                os.makedirs(target_dir, exist_ok=True)
                                target_path = os.path.join(target_dir, name)
                                # 如果已经在目标目录则跳过
                                if os.path.abspath(os.path.dirname(src_path)) == os.path.abspath(target_dir):
                                    continue
                                # 处理重名情况：自动追加 _1, _2 ...
                                if os.path.exists(target_path):
                                    base, ext_real = os.path.splitext(name)
                                    idx = 1
                                    while True:
                                        candidate = f"{base}_{idx}{ext_real}"
                                        candidate_path = os.path.join(target_dir, candidate)
                                        if not os.path.exists(candidate_path):
                                            target_path = candidate_path
                                            break
                                        idx += 1
                                shutil.move(src_path, target_path)
                                moved_count += 1
                    log.info(
                        f"Moved {moved_count} files with extensions {sorted(list(allowed_exts))} to: {resolved_dest_dir}")
                except Exception as move_err:
                    log.error(f"Post-download move failed: {move_err}")

            except Exception as e:
                progress_callback.fail(str(e))
                log.error(f"Download failed: {str(e)}")

        # 启动异步下载任务
        asyncio.create_task(download_task())

        return web.json_response({
            "success": True,
            "data": {
                "download_id": download_id,
                "id": id,
                "model_id": model_id,
                "model_type": model_type,
                "dest_dir": resolved_dest_dir,
                "status": "started"
            },
            "message": f"Download started for model '{model_id}'"
        })

    except ImportError as e:
        log.error(f"ModelScope SDK not installed: {str(e)}")
        return web.json_response({
            "success": False,
            "message": "ModelScope SDK not installed. Please install with: pip install modelscope"
        })

    except Exception as e:
        log.error(f"Error starting download: {str(e)}")
        import traceback
        traceback.print_exc()
        return web.json_response({
            "success": False,
            "message": f"Failed to start download: {str(e)}"
        })


@server.PromptServer.instance.routes.get("/api/download-progress/{download_id}")
async def get_download_progress(request):
    """
    Get download progress by download ID
    """
    download_id = request.match_info.get('download_id')

    if not download_id:
        return web.json_response({
            "success": False,
            "message": "Missing download_id parameter"
        })

    with download_lock:
        progress_info = download_progress.get(download_id)

    if not progress_info:
        return web.json_response({
            "success": False,
            "message": f"Download ID {download_id} not found"
        })

    return web.json_response({
        "success": True,
        "data": progress_info,
        "message": "Download progress retrieved successfully"
    })


@server.PromptServer.instance.routes.get("/api/download-progress")
async def list_downloads(request):
    """
    List all active downloads
    """
    with download_lock:
        downloads = list(download_progress.keys())

    return web.json_response({
        "success": True,
        "data": {
            "downloads": downloads,
            "count": len(downloads)
        },
        "message": "Download list retrieved successfully"
    })


@server.PromptServer.instance.routes.delete("/api/download-progress/{download_id}")
async def clear_download_progress(request):
    """
    Clear download progress record (for cleanup)
    """
    download_id = request.match_info.get('download_id')

    if not download_id:
        return web.json_response({
            "success": False,
            "message": "Missing download_id parameter"
        })

    with download_lock:
        if download_id in download_progress:
            del download_progress[download_id]
            return web.json_response({
                "success": True,
                "message": f"Download progress {download_id} cleared successfully"
            })
        else:
            return web.json_response({
                "success": False,
                "message": f"Download ID {download_id} not found"
            })


@server.PromptServer.instance.routes.get("/api/model-searchs")
async def model_suggests(request):
    """
    Get model search list by keyword
    """
    log.info("Received model-search request")
    try:
        keyword = request.query.get('keyword')

        if not keyword:
            return web.json_response({
                "success": False,
                "message": "Missing required parameter: keyword"
            })

        # 创建ModelScope网关实例
        gateway = ModelScopeGateway()

        suggests = gateway.search(name=keyword)

        list = suggests["data"] if suggests.get("data") else []

        return web.json_response({
            "success": True,
            "data": {
                "searchs": list,
                "total": len(list)
            },
            "message": f"Get searchs successfully"
        })

    except ImportError as e:
        log.error(f"ModelScope SDK not installed: {str(e)}")
        return web.json_response({
            "success": False,
            "message": "ModelScope SDK not installed. Please install with: pip install modelscope"
        })

    except Exception as e:
        log.error(f"Error get model searchs: {str(e)}")
        import traceback
        traceback.print_exc()
        return web.json_response({
            "success": False,
            "message": f"Get model searchs failed: {str(e)}"
        })


@server.PromptServer.instance.routes.get("/api/model-paths")
async def model_paths(request):
    """
    Get model paths by type
    """
    log.info("Received model-paths request")
    try:
        model_paths = list(folder_paths.folder_names_and_paths.keys())
        return web.json_response({
            "success": True,
            "data": {
                "paths": model_paths,
            },
            "message": f"Get paths successfully"
        })

    except Exception as e:
        log.error(f"Error get model path: {str(e)}")
        import traceback
        traceback.print_exc()
        return web.json_response({
            "success": False,
            "message": f"Get model failed: {str(e)}"
        })