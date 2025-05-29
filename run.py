import subprocess
import sys
import os
import time
import requests
from requests.exceptions import RequestException
from config import API_HOST, API_PORT, FRONTEND_PORT

def wait_for_api(url: str, max_retries: int = 30, delay: float = 1.0):
    """等待API服务可用"""
    print(f"等待API服务启动 ({url})...")
    for i in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("API服务已就绪！")
                return True
        except RequestException:
            pass
        print(f"等待中... ({i + 1}/{max_retries})")
        time.sleep(delay)
    print("API服务启动超时！")
    return False

def main():
    # 检查是否安装了所需的依赖
    try:
        import fastapi
        import streamlit
        import jieba
        import numpy
    except ImportError:
        print("正在安装依赖...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    print("启动后端服务...")
    # 启动后端服务
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--reload", "--host", API_HOST, "--port", str(API_PORT)],
        env=os.environ.copy()
    )
    
    # 等待后端服务启动
    if not wait_for_api(f"http://{API_HOST}:{API_PORT}/docs"):
        print("无法启动后端服务，请检查日志！")
        backend_process.terminate()
        return
    
    print("启动前端服务...")
    # 启动前端服务
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port", str(FRONTEND_PORT), "--server.address", API_HOST],
        env=os.environ.copy()
    )
    
    try:
        # 等待任意一个进程结束
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("服务已关闭")

if __name__ == "__main__":
    main() 