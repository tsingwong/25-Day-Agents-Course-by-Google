"""
Human-in-the-Loop 客户端

交互式客户端，演示完整的 Human-in-the-Loop 流程:
1. 提交任务请求
2. 查看待审批任务
3. 审批或拒绝任务
4. 查看执行结果

运行方式:
    python -m client.hitl_client
"""

import asyncio
import sys
import os
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

# HITL Server URL
HITL_SERVER_URL = os.getenv("HITL_SERVER_URL", "http://localhost:8016")


class HITLClient:
    """Human-in-the-Loop 客户端"""

    def __init__(self, base_url: str = HITL_SERVER_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=120.0,
            trust_env=False,
        )

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            resp = await self.client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def create_task(self, message: str) -> dict:
        """创建新任务"""
        resp = await self.client.post(
            "/tasks",
            json={"message": message},
        )
        resp.raise_for_status()
        return resp.json()

    async def list_tasks(self, status: Optional[str] = None) -> dict:
        """获取任务列表"""
        params = {}
        if status:
            params["status"] = status
        resp = await self.client.get("/tasks", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_pending_approvals(self) -> dict:
        """获取待审批任务"""
        resp = await self.client.get("/tasks/pending")
        resp.raise_for_status()
        return resp.json()

    async def get_task(self, task_id: str) -> dict:
        """获取任务详情"""
        resp = await self.client.get(f"/tasks/{task_id}")
        resp.raise_for_status()
        return resp.json()

    async def approve_task(
        self,
        task_id: str,
        comment: str = "",
        approver: str = "user",
    ) -> dict:
        """批准任务"""
        resp = await self.client.post(
            f"/tasks/{task_id}/approve",
            json={
                "approved": True,
                "comment": comment,
                "approver": approver,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def reject_task(
        self,
        task_id: str,
        comment: str = "",
        approver: str = "user",
    ) -> dict:
        """拒绝任务"""
        resp = await self.client.post(
            f"/tasks/{task_id}/reject",
            json={
                "approved": False,
                "comment": comment,
                "approver": approver,
            },
        )
        resp.raise_for_status()
        return resp.json()


# ============================================================
# 交互式演示
# ============================================================

def print_header(title: str):
    """打印标题"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_task(task: dict, show_details: bool = False):
    """打印任务信息"""
    print(f"  ID: {task.get('task_id', 'N/A')[:8]}...")
    print(f"  状态: {task.get('status', 'N/A')}")
    if task.get('pending_action'):
        print(f"  待执行: {task.get('pending_action')}")
    if task.get('user_input'):
        print(f"  用户输入: {task.get('user_input')[:50]}...")
    if show_details:
        print(f"  创建时间: {task.get('created_at', 'N/A')}")
        print(f"  更新时间: {task.get('updated_at', 'N/A')}")


async def demo_low_risk():
    """演示低风险任务（自动执行）"""
    print_header("场景 1: 低风险任务 - 自动执行")
    print("  请求: 查询今天的天气")
    print("-" * 60)

    client = HITLClient()
    try:
        result = await client.create_task("查询今天北京的天气")
        print(f"\n  任务创建成功!")
        print(f"  Task ID: {result.get('task_id', 'N/A')[:8]}...")
        print(f"  状态: {result.get('status')}")
        print(f"  需要审批: {result.get('requires_approval')}")
        print(f"  风险等级: {result.get('risk_level')}")
        print()
        print(f"  响应: {result.get('message')[:200]}...")
    except Exception as e:
        print(f"  ❌ 错误: {e}")
    finally:
        await client.close()


async def demo_high_risk():
    """演示高风险任务（需要审批）"""
    print_header("场景 2: 高风险任务 - 需要审批")
    print("  请求: 删除所有用户数据")
    print("-" * 60)

    client = HITLClient()
    try:
        # 创建任务
        result = await client.create_task("请帮我删除所有用户数据")
        task_id = result.get('task_id')

        print(f"\n  任务创建成功!")
        print(f"  Task ID: {task_id[:8]}...")
        print(f"  状态: {result.get('status')}")
        print(f"  需要审批: {result.get('requires_approval')}")
        print(f"  风险等级: {result.get('risk_level')}")
        print(f"  待执行操作: {result.get('action_description')}")
        print()
        print(f"  消息: {result.get('message')}")

        if result.get('status') == 'waiting_approval':
            print()
            print("-" * 60)
            print("  任务等待审批中...")
            print("-" * 60)

            # 模拟人工审批决策
            print()
            print("  [模拟审批] 这是一个危险操作，拒绝执行")

            # 拒绝任务
            reject_result = await client.reject_task(
                task_id,
                comment="操作过于危险，不允许批量删除用户数据",
                approver="security_admin",
            )

            print()
            print(f"  审批结果: {reject_result.get('status')}")
            print(f"  响应: {reject_result.get('result', 'N/A')[:200]}...")

    except Exception as e:
        print(f"  ❌ 错误: {e}")
    finally:
        await client.close()


async def demo_approved_task():
    """演示审批通过的任务"""
    print_header("场景 3: 审批通过的任务")
    print("  请求: 发送一封邮件给用户")
    print("-" * 60)

    client = HITLClient()
    try:
        # 创建任务
        result = await client.create_task("发送一封欢迎邮件给新注册的用户 test@example.com")
        task_id = result.get('task_id')

        print(f"\n  任务创建成功!")
        print(f"  Task ID: {task_id[:8]}...")
        print(f"  状态: {result.get('status')}")
        print(f"  需要审批: {result.get('requires_approval')}")
        print(f"  风险等级: {result.get('risk_level')}")

        if result.get('status') == 'waiting_approval':
            print()
            print("-" * 60)
            print("  任务等待审批中...")
            print("-" * 60)

            # 模拟人工审批决策
            print()
            print("  [模拟审批] 邮件内容合规，批准发送")

            # 批准任务
            approve_result = await client.approve_task(
                task_id,
                comment="邮件内容已审核，批准发送",
                approver="content_reviewer",
            )

            print()
            print(f"  审批结果: {approve_result.get('status')}")
            print(f"  执行结果: {approve_result.get('result', 'N/A')[:200]}...")

    except Exception as e:
        print(f"  ❌ 错误: {e}")
    finally:
        await client.close()


async def demo_list_tasks():
    """演示任务列表查询"""
    print_header("任务列表查询")

    client = HITLClient()
    try:
        # 获取所有任务
        result = await client.list_tasks()
        tasks = result.get('tasks', [])

        print(f"\n  共 {result.get('total', 0)} 个任务:")
        print("-" * 60)

        for task in tasks[:5]:  # 只显示前 5 个
            print()
            print_task(task)

        if len(tasks) > 5:
            print(f"\n  ... 还有 {len(tasks) - 5} 个任务")

        # 获取待审批任务
        pending = await client.get_pending_approvals()
        pending_tasks = pending.get('tasks', [])

        if pending_tasks:
            print()
            print("-" * 60)
            print(f"  待审批任务: {len(pending_tasks)} 个")
            print("-" * 60)
            for task in pending_tasks:
                print()
                print_task(task)

    except Exception as e:
        print(f"  ❌ 错误: {e}")
    finally:
        await client.close()


async def interactive_mode():
    """交互模式"""
    print_header("交互模式")
    print("  输入命令与 HITL Agent 交互")
    print()
    print("  可用命令:")
    print("    send <message>  - 发送请求")
    print("    list            - 查看任务列表")
    print("    pending         - 查看待审批任务")
    print("    approve <id>    - 批准任务")
    print("    reject <id>     - 拒绝任务")
    print("    detail <id>     - 查看任务详情")
    print("    quit            - 退出")
    print()

    client = HITLClient()

    try:
        while True:
            try:
                user_input = input("HITL> ").strip()
                if not user_input:
                    continue

                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                if command == "quit" or command == "exit":
                    print("再见!")
                    break

                elif command == "send":
                    if not args:
                        print("请输入消息内容")
                        continue
                    result = await client.create_task(args)
                    print(f"\n任务 ID: {result.get('task_id')}")
                    print(f"状态: {result.get('status')}")
                    print(f"风险等级: {result.get('risk_level')}")
                    print(f"响应: {result.get('message')[:300]}...")

                elif command == "list":
                    result = await client.list_tasks()
                    tasks = result.get('tasks', [])
                    print(f"\n共 {len(tasks)} 个任务:")
                    for task in tasks[:10]:
                        print(f"  [{task.get('status'):15}] {task.get('task_id')[:8]}... - {task.get('user_input', '')[:30]}...")

                elif command == "pending":
                    result = await client.get_pending_approvals()
                    tasks = result.get('tasks', [])
                    if tasks:
                        print(f"\n待审批任务 ({len(tasks)} 个):")
                        for task in tasks:
                            print(f"  {task.get('task_id')[:8]}... - {task.get('pending_action', '')[:50]}...")
                    else:
                        print("\n没有待审批的任务")

                elif command == "approve":
                    if not args:
                        print("请输入任务 ID")
                        continue
                    comment = input("审批意见 (可选): ").strip()
                    result = await client.approve_task(args, comment)
                    print(f"\n审批结果: {result.get('status')}")
                    print(f"响应: {result.get('result', 'N/A')[:300]}...")

                elif command == "reject":
                    if not args:
                        print("请输入任务 ID")
                        continue
                    comment = input("拒绝原因: ").strip()
                    result = await client.reject_task(args, comment)
                    print(f"\n审批结果: {result.get('status')}")
                    print(f"响应: {result.get('result', 'N/A')[:300]}...")

                elif command == "detail":
                    if not args:
                        print("请输入任务 ID")
                        continue
                    result = await client.get_task(args)
                    task = result.get('task', {})
                    print(f"\n任务详情:")
                    print(f"  ID: {task.get('task_id')}")
                    print(f"  状态: {task.get('status')}")
                    print(f"  用户输入: {task.get('user_input')}")
                    print(f"  待执行: {task.get('pending_action')}")
                    print(f"  创建时间: {task.get('created_at')}")
                    if result.get('state'):
                        state = result['state']
                        print(f"  风险等级: {state.get('risk_level')}")
                        print(f"  分析: {state.get('analysis', '')[:100]}...")

                else:
                    print(f"未知命令: {command}")

            except KeyboardInterrupt:
                print("\n再见!")
                break
            except Exception as e:
                print(f"错误: {e}")

    finally:
        await client.close()


async def main():
    """主程序"""
    print("=" * 60)
    print("  Day 16: Human-in-the-Loop Client")
    print("=" * 60)
    print()
    print(f"服务地址: {HITL_SERVER_URL}")

    # 健康检查
    client = HITLClient()
    try:
        is_healthy = await client.health_check()
        if not is_healthy:
            print()
            print("❌ 无法连接到 HITL 服务")
            print("   请确保服务正在运行:")
            print("   python -m langgraph_agent.server")
            return
        print("✅ 服务连接正常")
    finally:
        await client.close()

    print()
    print("选择演示模式:")
    print("  1. 低风险任务演示 (自动执行)")
    print("  2. 高风险任务演示 (需要审批)")
    print("  3. 审批通过演示")
    print("  4. 查看任务列表")
    print("  5. 交互模式")
    print("  6. 运行所有演示")
    print("  q. 退出")
    print()

    choice = input("请选择 (1-6/q): ").strip()

    if choice == "1":
        await demo_low_risk()
    elif choice == "2":
        await demo_high_risk()
    elif choice == "3":
        await demo_approved_task()
    elif choice == "4":
        await demo_list_tasks()
    elif choice == "5":
        await interactive_mode()
    elif choice == "6":
        await demo_low_risk()
        await asyncio.sleep(1)
        await demo_high_risk()
        await asyncio.sleep(1)
        await demo_approved_task()
        await asyncio.sleep(1)
        await demo_list_tasks()
    elif choice.lower() == "q":
        print("再见!")
    else:
        print("无效选择")

    print()
    print("=" * 60)
    print("  演示结束")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
