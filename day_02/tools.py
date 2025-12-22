

def get_current_time() -> str:
    """获取当前时间。"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate(expression: str) -> str:
    """计算数学表达式。

    Args:
        expression: 数学表达式，如 "2 + 2"

    Returns:
        计算结果
    """
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"
