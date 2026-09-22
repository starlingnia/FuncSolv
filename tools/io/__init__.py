"""
tools.io 模块
------------------------------------------------------------
模块化无阻塞 I/O 组件：
- AsyncFileWriter: 基于后台独立线程与工作队列的高性能异步文件落盘器
- 序列化套件: serialize_sublists, serialize_single_line, serialize_thread_input_block, serialize_thread_output_block
- 评测报告格式化: format_multithread_report
- 测试负载生成器: generate_workload_by_type
"""

from tools.io.async_writer import AsyncFileWriter
from tools.io.serializer import (
    serialize_sublists,
    serialize_single_line,
    serialize_thread_input_block,
    serialize_thread_output_block,
    parse_sublists_from_text,
)
from tools.io.report_formatter import format_multithread_report
from tools.io.workload_generator import generate_workload_by_type

__all__ = [
    "AsyncFileWriter",
    "serialize_sublists",
    "serialize_single_line",
    "serialize_thread_input_block",
    "serialize_thread_output_block",
    "parse_sublists_from_text",
    "format_multithread_report",
    "generate_workload_by_type",
]
