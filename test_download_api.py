#!/usr/bin/env python3
"""
测试下载进度API的脚本
"""

import requests
import json
import time

# ComfyUI服务器地址
BASE_URL = "http://localhost:8188"

def test_download_model():
    """测试开始下载模型"""
    url = f"{BASE_URL}/api/download-model"
    
    data = {
        "model_id": "damo/sd-v1-5",
        "model_type": "checkpoints",
        "dest_dir": None  # 使用默认目录
    }
    
    try:
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get("success"):
            download_id = result["data"]["download_id"]
            print(f"✅ 下载已开始，下载ID: {download_id}")
            return download_id
        else:
            print(f"❌ 下载启动失败: {result.get('message')}")
            return None
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def poll_download_progress(download_id):
    """轮询下载进度"""
    url = f"{BASE_URL}/api/download-progress/{download_id}"
    
    print(f"\n📊 开始监控下载进度 (ID: {download_id})")
    print("=" * 60)
    
    while True:
        try:
            response = requests.get(url)
            result = response.json()
            
            if result.get("success"):
                progress_data = result["data"]
                status = progress_data["status"]
                percentage = progress_data["percentage"]
                progress = progress_data["progress"]
                file_size = progress_data["file_size"]
                speed = progress_data["speed"]
                estimated_time = progress_data["estimated_time"]
                
                # 格式化显示
                if file_size > 0:
                    progress_mb = progress / (1024 * 1024)
                    total_mb = file_size / (1024 * 1024)
                    progress_str = f"{progress_mb:.1f}MB / {total_mb:.1f}MB"
                else:
                    progress_str = f"{progress} bytes"
                
                speed_str = f"{speed:.2f} B/s" if speed else "N/A"
                eta_str = f"{estimated_time:.1f}s" if estimated_time else "N/A"
                
                print(f"\r📥 {status.upper()}: {percentage:.1f}% | {progress_str} | 速度: {speed_str} | 剩余时间: {eta_str}", end="", flush=True)
                
                if status in ["completed", "failed"]:
                    print()  # 换行
                    if status == "completed":
                        print(f"✅ 下载完成！总用时: {progress_data.get('total_time', 'N/A')}s")
                    else:
                        print(f"❌ 下载失败: {progress_data.get('error_message', 'Unknown error')}")
                    break
                    
            else:
                print(f"\n❌ 获取进度失败: {result.get('message')}")
                break
                
        except Exception as e:
            print(f"\n❌ 请求失败: {e}")
            break
            
        time.sleep(1)  # 每秒轮询一次

def list_all_downloads():
    """列出所有下载"""
    url = f"{BASE_URL}/api/download-progress"
    
    try:
        response = requests.get(url)
        result = response.json()
        
        if result.get("success"):
            downloads = result["data"]["downloads"]
            count = result["data"]["count"]
            print(f"\n📋 当前活跃下载: {count} 个")
            
            for download_id in downloads:
                print(f"  - {download_id}")
        else:
            print(f"❌ 获取下载列表失败: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def clear_download_progress(download_id):
    """清理下载进度记录"""
    url = f"{BASE_URL}/api/download-progress/{download_id}"
    
    try:
        response = requests.delete(url)
        result = response.json()
        
        if result.get("success"):
            print(f"✅ 已清理下载进度记录: {download_id}")
        else:
            print(f"❌ 清理失败: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def main():
    """主函数"""
    print("🚀 下载进度API测试")
    print("=" * 60)
    
    # 1. 开始下载
    download_id = test_download_model()
    if not download_id:
        return
    
    # 2. 列出所有下载
    list_all_downloads()
    
    # 3. 监控下载进度
    poll_download_progress(download_id)
    
    # 4. 清理进度记录（可选）
    # clear_download_progress(download_id)

if __name__ == "__main__":
    main()





