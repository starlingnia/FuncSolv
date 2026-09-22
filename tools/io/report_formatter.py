"""
评测报告格式化组件 (Report Formatter)
------------------------------------------------------------
- 核心功能单一：将多线程测试汇总指标与各线程结果格式化为标准文本报告
- 保持纯函数特性，无直接磁盘文件依赖
"""

from datetime import datetime
from typing import Any, List


def format_multithread_report(
    results: List[Any],
    wall_duration: float,
    library_path: str,
    docs_dir: str,
) -> str:
    """
    格式化生成完整的多线程性能评测报告文本
    """
    total_elements_all = sum(res.total_elements for res in results)
    total_lists_all = sum(res.num_lists for res in results)
    sum_thread_duration = sum(res.duration for res in results)
    speedup = sum_thread_duration / wall_duration if wall_duration > 0 else 1.0
    overall_throughput = total_elements_all / wall_duration if wall_duration > 0 else 0.0
    all_passed = all(res.passed for res in results)

    report_lines = [
        "=" * 80,
        "                    TaskOrchestrator 多线程并发运行测试报告",
        "=" * 80,
        f"测试时间        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"C++ 动态共享库  : {library_path}",
        f"持久化输出目录  : {docs_dir}",
        f"并发工作线程数  : {len(results)}",
        f"处理子列表总量  : {total_lists_all} 个",
        f"归并元素总规模  : {total_elements_all} 个整数",
        f"并发归并总耗时  : {wall_duration:.6f} 秒 (Wall-clock Time)",
        f"线程执行耗时累加: {sum_thread_duration:.6f} 秒 (Cumulative Thread Time)",
        f"并发实际加速比  : {speedup:.2f}x",
        f"系统并发总吞吐率: {overall_throughput:,.1f} elements/sec",
        "-" * 80,
        "各线程并发执行与正确性校验明细:",
        "-" * 80,
    ]

    for res in results:
        status_tag = "PASS" if res.passed else "FAIL"
        report_lines.append(f"[Thread-{res.thread_id}] {res.worker_name}")
        report_lines.append(
            f"  - 校验状态: [{status_tag}] (数量守恒: {res.is_length_valid}, "
            f"升序排列: {res.is_sorted}, 元素全等: {res.is_content_valid})"
        )
        report_lines.append(f"  - 子列表数: {res.num_lists}, 元素总数: {res.total_elements}")
        report_lines.append(f"  - 耗时    : {res.duration:.6f} 秒 | 吞吐率: {res.throughput:,.1f} elements/sec")
        if getattr(res, "error_message", None):
            report_lines.append(f"  - 异常信息: {res.error_message}")
        report_lines.append("")

    conclusion = (
        ">>> 全部测试用例通过 (ALL TESTS PASSED) <<<"
        if all_passed
        else ">>> 测试未完全通过 (SOME TESTS FAILED) <<<"
    )
    report_lines.extend([
        "-" * 80,
        f"测试总体结论: {conclusion}",
        "=" * 80,
    ])

    return "\n".join(report_lines) + "\n"
