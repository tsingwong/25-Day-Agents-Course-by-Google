#!/usr/bin/env python3
"""
Day 14: A2A 协议演示 - 一键运行脚本

这个脚本会：
1. 启动远程 Agent (A2A Server) 在后台
2. 等待服务就绪
3. 运行 Host Agent (A2A Client) 进行测试
4. 清理并退出

运行方式:
    python run_demo.py
"""

import asyncio
import subprocess
import sys
import time
import os
import signal

# 确保使用正确的 Python 环境
PYTHON = sys.executable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def check_server_ready(url: str, max_attempts: int = 30) -> bool:
    """检查服务器是否就绪"""
    import httpx

    for i in range(max_attempts):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/.well-known/agent.json")
                if response.status_code == 200:
                    print(f"   ✅ 服务器就绪!")
                    return True
        except Exception:
            pass
        print(f"   等待服务器启动... ({i + 1}/{max_attempts})")
        await asyncio.sleep(1)
    return False


async def run_demo():
    """运行完整的 A2A 演示"""
    print("=" * 60)
    print("Day 14: A2A 协议演示")
    print("=" * 60)
    print()

    server_process = None

    try:
        # 步骤 1: 启动远程 Agent
        print("📡 步骤 1: 启动远程 Agent (A2A Server)...")
        print()

        server_process = subprocess.Popen(
            [PYTHON, "-m", "remote_agent.agent"],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # 等待服务器就绪
        print("   等待服务器启动...")
        if not await check_server_ready("http://localhost:8001"):
            print("   ❌ 服务器启动失败!")
            return

        print()

        # 步骤 2: 运行客户端测试
        print("🖥️  步骤 2: 运行 Host Agent (A2A Client)...")
        print()

        # 导入并运行 host agent
        sys.path.insert(0, BASE_DIR)
        from host_agent.agent import main as host_main
        await host_main()

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断...")

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理
        print("\n🧹 清理资源...")
        if server_process:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("   远程 Agent 已停止")

        print()
        print("=" * 60)
        print("演示结束!")
        print("=" * 60)


if __name__ == "__main__":
    # 检查依赖
    try:
        import httpx
    except ImportError:
        print("正在安装 httpx...")
        subprocess.run([PYTHON, "-m", "pip", "install", "httpx"], check=True)

    asyncio.run(run_demo())
