import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import sys
import time
from typing import List, Tuple

# 动态配置模块导入路径，确保无论在哪个目录启动均可正确定位 tools 目录
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 从 tools/orsortlist 导入高层调度器 TaskOrchestrator
from tools.orsortlist import TaskOrchestrator


@dataclass
class ThreadTestResult:
    """封装单个线程任务的运行数据与验证结果"""
    thread_id: int
    worker_name: str
    num_lists: int
    total_elements: int
    duration: float
    throughput: float
    is_length_valid: bool
    is_sorted: bool
    is_content_valid: bool
    passed: bool
    input_lists: List[List[int]]
    output_list: List[int]
    error_message: str = ""


def generate_workload_by_type(
    thread_id: int,
    workload_type: str,
    base_k: int = 100,
    max_len: int = 100,
) -> Tuple[str, List[List[int]]]:
    """
    根据线程类型生成多样化的测试数据集，涵盖标准规模、高并发数、负数区间、重复元素等场景
    """
    import numpy as np

    # 采用可复现的线程独立随机数生成器
    rng = np.random.default_rng(seed=1000 + thread_id)
    lists: List[List[int]] = []

    if workload_type == "medium_scale":
        description = "标准中等规模负载 (100 组正序列表，长度 10~100)"
        k = base_k
        for _ in range(k):
            length = rng.integers(10, max_len + 1)
            steps = rng.integers(1, 10, size=length)
            sublist = np.cumsum(steps).tolist()
            lists.append(sublist)

    elif workload_type == "high_cardinality":
        description = "高分支短列表负载 (200 组短升序列表，考察多路分治调度)"
        k = base_k * 2
        for _ in range(k):
            length = rng.integers(5, 30)
            steps = rng.integers(1, 8, size=length)
            sublist = np.cumsum(steps).tolist()
            lists.append(sublist)

    elif workload_type == "negative_span":
        description = "负数与零混合负载 (80 组包含负数及跨零递增列表)"
        k = max(20, int(base_k * 0.8))
        for _ in range(k):
            length = rng.integers(10, 80)
            start_val = rng.integers(-5000, -100)
            steps = rng.integers(1, 15, size=length)
            sublist = (start_val + np.cumsum(steps)).tolist()
            lists.append(sublist)

    elif workload_type == "dense_duplicates":
        description = "稠密重复元素负载 (120 组含大量等值元素列表，含单元素边界)"
        k = int(base_k * 1.2)
        for i in range(k):
            if i % 10 == 0:
                # 边界情况：单元素列表
                lists.append([int(rng.integers(0, 1000))])
            else:
                length = rng.integers(5, 60)
                # 步长含 0，产生连续相同值
                steps = rng.integers(0, 4, size=length)
                base = rng.integers(0, 200)
                sublist = (base + np.cumsum(steps)).tolist()
                lists.append(sublist)

    else:
        description = f"通用随机规模负载 (线程 {thread_id} 自适应生成)"
        k = base_k
        for _ in range(k):
            length = rng.integers(5, max_len)
            steps = rng.integers(1, 10, size=length)
            sublist = np.cumsum(steps).tolist()
            lists.append(sublist)

    return description, lists


def execute_thread_task(
    thread_id: int,
    workload_type: str,
    orchestrator: TaskOrchestrator,
    base_k: int = 100,
    max_len: int = 100,
) -> ThreadTestResult:
    """
    单个并发工作线程执行函数：准备数据 -> 调度 TaskOrchestrator -> 严谨校验输出正确性
    """
    worker_name, input_lists = generate_workload_by_type(
        thread_id=thread_id,
        workload_type=workload_type,
        base_k=base_k,
        max_len=max_len,
    )

    total_elements = sum(len(sub) for sub in input_lists)
    num_lists = len(input_lists)

    start_time = time.perf_counter()
    try:
        # 调用 TaskOrchestrator 统筹高层调度并驱动 C++ 底层归并
        output_list = orchestrator.coordinate_execution(input_lists)
        duration = time.perf_counter() - start_time
    except Exception as exc:
        duration = time.perf_counter() - start_time
        return ThreadTestResult(
            thread_id=thread_id,
            worker_name=worker_name,
            num_lists=num_lists,
            total_elements=total_elements,
            duration=duration,
            throughput=0.0,
            is_length_valid=False,
            is_sorted=False,
            is_content_valid=False,
            passed=False,
            input_lists=input_lists,
            output_list=[],
            error_message=str(exc),
        )

    # 1. 元素数量守恒校验
    is_length_valid = (len(output_list) == total_elements)

    # 2. 升序单调性校验
    is_sorted = all(output_list[i] <= output_list[i + 1] for i in range(len(output_list) - 1))

    # 3. 元素内容与基准排序比对校验
    ground_truth = sorted([item for sub in input_lists for item in sub])
    is_content_valid = (output_list == ground_truth)

    passed = is_length_valid and is_sorted and is_content_valid
    throughput = total_elements / duration if duration > 0 else 0.0

    return ThreadTestResult(
        thread_id=thread_id,
        worker_name=worker_name,
        num_lists=num_lists,
        total_elements=total_elements,
        duration=duration,
        throughput=throughput,
        is_length_valid=is_length_valid,
        is_sorted=is_sorted,
        is_content_valid=is_content_valid,
        passed=passed,
        input_lists=input_lists,
        output_list=output_list,
    )


def save_multithread_results(
    docs_dir: Path,
    results: List[ThreadTestResult],
    wall_duration: float,
    library_path: str,
) -> Tuple[Path, Path, Path]:
    """
    将多线程测试的输入数据、归并结果以及性能评测报告完整持久化到 docs/ 目录下
    """
    docs_dir.mkdir(parents=True, exist_ok=True)

    before_path = docs_dir / "multithread_data_before.txt"
    after_path = docs_dir / "multithread_data_after.txt"
    report_path = docs_dir / "multithread_test_report.txt"

    # 1. 保存多线程测试前的数据集 (docs/multithread_data_before.txt)
    with open(before_path, "w", encoding="utf-8") as file_before:
        file_before.write("# ==============================================================================\n")
        file_before.write("# TaskOrchestrator 多线程并发测试 - 处理前原始输入数据集\n")
        file_before.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        file_before.write("# 格式规范: 每个线程数据由标识行开始，随后每一行表示一个升序子列表，数字空格隔开\n")
        file_before.write("# ==============================================================================\n\n")

        for res in results:
            file_before.write(f"### [Thread-{res.thread_id}] {res.worker_name}\n")
            file_before.write(f"# 子列表总数 (k): {res.num_lists}, 元素总数: {res.total_elements}\n")
            for sublist in res.input_lists:
                file_before.write(" ".join(map(str, sublist)) + "\n")
            file_before.write("\n")

    # 2. 保存多线程测试后的归并结果 (docs/multithread_data_after.txt)
    with open(after_path, "w", encoding="utf-8") as file_after:
        file_after.write("# ==============================================================================\n")
        file_after.write("# TaskOrchestrator 多线程并发测试 - 处理后最终有序合并结果\n")
        file_after.write(f"# 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        file_after.write("# 格式规范: 每个线程对应一行完整的全局升序排列结果\n")
        file_after.write("# ==============================================================================\n\n")

        for res in results:
            status_str = "SUCCESS" if res.passed else "FAILED"
            file_after.write(f"### [Thread-{res.thread_id}] Status: {status_str} | Merged Elements: {len(res.output_list)} | Cost: {res.duration:.6f}s\n")
            file_after.write(" ".join(map(str, res.output_list)) + "\n\n")

    # 3. 统计汇总并生成性能评测报告 (docs/multithread_test_report.txt)
    total_elements_all = sum(res.total_elements for res in results)
    total_lists_all = sum(res.num_lists for res in results)
    sum_thread_duration = sum(res.duration for res in results)
    speedup = sum_thread_duration / wall_duration if wall_duration > 0 else 1.0
    all_passed = all(res.passed for res in results)

    report_lines = [
        "================================================================================",
        "                    TaskOrchestrator 多线程并发运行测试报告",
        "================================================================================",
        f"测试时间        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"C++ 动态共享库  : {library_path}",
        f"持久化输出目录  : {docs_dir}",
        f"并发工作线程数  : {len(results)}",
        f"处理子列表总量  : {total_lists_all} 个",
        f"归并元素总规模  : {total_elements_all} 个整数",
        f"并发总运行耗时  : {wall_duration:.6f} 秒 (Wall-clock Time)",
        f"线程执行耗时累加: {sum_thread_duration:.6f} 秒 (Cumulative Thread Time)",
        f"并发实际加速比  : {speedup:.2f}x",
        "--------------------------------------------------------------------------------",
        "各线程并发执行与正确性校验明细:",
        "--------------------------------------------------------------------------------",
    ]

    for res in results:
        status_tag = "PASS" if res.passed else "FAIL"
        report_lines.append(f"[Thread-{res.thread_id}] {res.worker_name}")
        report_lines.append(f"  - 校验状态: [{status_tag}] (数量守恒: {res.is_length_valid}, 升序排列: {res.is_sorted}, 元素全等: {res.is_content_valid})")
        report_lines.append(f"  - 子列表数: {res.num_lists}, 元素总数: {res.total_elements}")
        report_lines.append(f"  - 耗时    : {res.duration:.6f} 秒 | 吞吐率: {res.throughput:,.1f} elements/sec")
        if res.error_message:
            report_lines.append(f"  - 异常信息: {res.error_message}")
        report_lines.append("")

    report_lines.extend([
        "--------------------------------------------------------------------------------",
        f"测试总体结论: {'>>> 全部测试用例通过 (ALL TESTS PASSED) <<<' if all_passed else '>>> 测试未完全通过 (SOME TESTS FAILED) <<<'}",
        "================================================================================",
    ])

    with open(report_path, "w", encoding="utf-8") as file_report:
        file_report.write("\n".join(report_lines) + "\n")

    return before_path, after_path, report_path


def run_multithread_test(
    num_threads: int = 4,
    base_k: int = 100,
    max_len: int = 100,
    docs_dir_path: str = "docs",
    lib_path: str = "build/libformergesortlists.so",
) -> bool:
    """
    主控测试流程：
    1. 初始化 TaskOrchestrator
    2. 多线程并发调度 coordinate_execution
    3. 收集性能指标与一致性校验结果
    4. 持久化数据与报告至 docs/ 目录
    """
    docs_dir = Path(docs_dir_path)
    if not docs_dir.is_absolute():
        docs_dir = (PROJECT_ROOT / docs_dir).resolve()

    resolved_lib = Path(lib_path)
    if not resolved_lib.is_absolute():
        resolved_lib = (PROJECT_ROOT / lib_path).resolve()

    if not resolved_lib.exists():
        raise FileNotFoundError(f"未找到共享动态库文件: {resolved_lib}，请先执行构建生成对应库。")

    print("=" * 80)
    print(f"🚀 开始启动 TaskOrchestrator 多线程并发测试 (并发数: {num_threads})")
    print(f"📁 共享动态库路径: {resolved_lib}")
    print(f"📁 结果持久化目录: {docs_dir}")
    print("=" * 80)

    # 1. 实例化高层任务编排器
    orchestrator = TaskOrchestrator(str(resolved_lib))

    # 预设不同线程的业务测试场景
    workload_types = [
        "medium_scale",      # 线程 0：标准中等规模负载
        "high_cardinality",  # 线程 1：高分支短链表负载
        "negative_span",     # 线程 2：负数与跨零递增负载
        "dense_duplicates",  # 线程 3：重复值与边界单元素负载
    ]

    print("\n[Stage 1] 正在并发提交并调度多线程归并任务...")
    wall_start = time.perf_counter()

    results: List[ThreadTestResult] = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_tid = {}
        for tid in range(num_threads):
            wtype = workload_types[tid % len(workload_types)]
            future = executor.submit(
                execute_thread_task,
                thread_id=tid,
                workload_type=wtype,
                orchestrator=orchestrator,
                base_k=base_k,
                max_len=max_len,
            )
            future_to_tid[future] = tid

        for future in as_completed(future_to_tid):
            tid = future_to_tid[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as exc:
                print(f"❌ 线程 {tid} 执行发生异常: {exc}")

    wall_duration = time.perf_counter() - wall_start
    # 按线程 ID 排序结果
    results.sort(key=lambda r: r.thread_id)

    print(f"\n[Stage 2] 多线程并发执行完毕，总耗时: {wall_duration:.4f} 秒。")

    # 3. 持久化数据到 docs 目录
    print("\n[Stage 3] 正在将测试原始数据与归并结果持久化至 docs/ 目录...")
    before_p, after_p, report_p = save_multithread_results(
        docs_dir=docs_dir,
        results=results,
        wall_duration=wall_duration,
        library_path=str(resolved_lib),
    )
    print(f"  ✓ 原始输入数据已保存至: {before_p}")
    print(f"  ✓ 归并排序结果已保存至: {after_p}")
    print(f"  ✓ 性能评测报告已保存至: {report_p}")

    # 4. 控制台打印汇总概览
    all_passed = all(res.passed for res in results)
    total_elements = sum(r.total_elements for r in results)
    print("\n" + "=" * 80)
    print(f"📊 多线程执行与校验汇总 (总元素: {total_elements}, 状态: {'ALL PASSED' if all_passed else 'FAILED'}):")
    print("-" * 80)
    for r in results:
        status_symbol = "✅" if r.passed else "❌"
        print(
            f"  {status_symbol} [Thread-{r.thread_id}] {r.worker_name[:36]:<36} | "
            f"k={r.num_lists:<3} | Items={r.total_elements:<6} | "
            f"Time={r.duration:.4f}s | {r.throughput:,.0f} it/s"
        )
    print("=" * 80)

    return all_passed


import unittest


class TestTaskOrchestratorMultithreading(unittest.TestCase):
    """支持集成进 unittest / CI 流程的单元测试用例集"""

    def test_multithread_concurrency(self) -> None:
        passed = run_multithread_test(
            num_threads=4,
            base_k=50,
            max_len=50,
            docs_dir_path="docs",
        )
        self.assertTrue(passed, "TaskOrchestrator 多线程并发测试未全部通过！")


def main() -> None:
    parser = argparse.ArgumentParser(description="TaskOrchestrator 多线程运行测试脚本")
    parser.add_argument("--threads", type=int, default=4, help="并发执行的工作线程数量 (默认: 4)")
    parser.add_argument("--base-k", type=int, default=100, help="基准子列表数量 (默认: 100)")
    parser.add_argument("--max-len", type=int, default=100, help="子列表最大长度 (默认: 100)")
    parser.add_argument("--docs-dir", type=str, default="docs", help="数据与报告输出目录 (默认: docs)")
    parser.add_argument(
        "--lib-path",
        type=str,
        default="build/libformergesortlists.so",
        help="C++ 共享库路径 (默认: build/libformergesortlists.so)",
    )

    args = parser.parse_args()

    success = run_multithread_test(
        num_threads=args.threads,
        base_k=args.base_k,
        max_len=args.max_len,
        docs_dir_path=args.docs_dir,
        lib_path=args.lib_path,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
