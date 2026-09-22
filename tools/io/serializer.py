"""
数据格式化与序列化组件 (Serializer)
------------------------------------------------------------
- 核心功能单一：纯函数式的内存数据结构与磁盘文本协议互转
- 无物理 I/O 副作用，专注于高效的字符串拼接与数据解析
"""

from typing import Iterable, List


def serialize_sublists(lists: Iterable[Iterable[int]]) -> str:
    """
    将二维多路列表序列化为行文本：每行代表一个升序子列表，数字以空格隔开
    """
    return "".join(" ".join(map(str, sublist)) + "\n" for sublist in lists)


def serialize_single_line(numbers: Iterable[int]) -> str:
    """
    将一维有序列表序列化为单行空格隔开的文本
    """
    return " ".join(map(str, numbers)) + "\n"


def serialize_thread_input_block(
    thread_id: int, 
    worker_name: str, 
    input_lists: List[List[int]]
) -> str:
    """
    序列化单个线程的输入数据块（包含元数据头与内容）
    """
    total_elements = sum(len(sub) for sub in input_lists)
    num_lists = len(input_lists)
    header = (
        f"### [Thread-{thread_id}] {worker_name}\n"
        f"# 子列表总数 (k): {num_lists}, 元素总数: {total_elements}\n"
    )
    body = serialize_sublists(input_lists)
    return header + body + "\n"


def serialize_thread_output_block(
    thread_id: int,
    passed: bool,
    output_list: List[int],
    duration: float,
) -> str:
    """
    序列化单个线程的最终合并输出块（包含状态头与单行有序结果）
    """
    status_str = "SUCCESS" if passed else "FAILED"
    header = (
        f"### [Thread-{thread_id}] Status: {status_str} | "
        f"Merged Elements: {len(output_list)} | Cost: {duration:.6f}s\n"
    )
    body = serialize_single_line(output_list)
    return header + body + "\n"


def parse_sublists_from_text(content: str) -> List[List[int]]:
    """
    从标准格式文本中反序列化解析出二维整数列表（过滤注释与空行）
    """
    result: List[List[int]] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        result.append([int(x) for x in line.split()])
    return result
