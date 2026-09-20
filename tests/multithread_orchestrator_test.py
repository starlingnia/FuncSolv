"""
TaskOrchestrator 多线程并发调度与正确性评测自动化测试脚本
------------------------------------------------------------
- 结合 Python 高层业务调度与 C++ 底层多路归并引擎进行多线程并发测试
- 涵盖各种不同特征的业务负载数据集（标准规模、高分支、跨零负数、稠密重复、极端边界、逆序区间）
- 对并发输出结果进行严格的数学属性校验：数量守恒、单调递增有序性、全量元素内容一致性
- 实时统计各线程与系统维度的耗时、吞吐率与并行加速比
- 支持将原始输入、归并结果及详尽性能评测报告持久化落盘至 docs/ 目录
- 全面集成 unittest 测试用例，便于接入 CI/CD 流水线与自动化测试流程
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import sys
import time
from typing import List, Optional, Tuple
import unittest

import numpy as np

# 动态配置模块导入路径，确保无论在哪个目录启动均可正确定位工程根目录与 tools 目录
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

for path_entry in (str(PROJECT_ROOT), str(SRC_DIR)):
    if path_entry not in sys.path:
        sys.path.insert(0, path_entry)

# 从 tools/orsortlist 导入高层任务编排器 TaskOrchestrator
from tools.orsortlist import TaskOrchestrator


def resolve_library_path(custom_path: Optional[str] = None) -> Path:
    """
    智能解析 C++ 动态共享库路径，兼容多平台（macOS .dylib / Linux .so）与自定义路径
    """
    if custom_path:
        target = Path(custom_path)
        if not target.is_absolute():
            target = (PROJECT_ROOT / target).resolve()
        if target.exists():
            return target

    # 预设候选路径（支持常见构建输出路径与扩展名）
    candidates = [
        PROJECT_ROOT / "build" / "libformergesortlists.so",
        PROJECT_ROOT / "build" / "libformergesortlists.dylib",
        PROJECT_ROOT / "bin" / "libformergesortlists.so",
        PROJECT_ROOT / "bin" / "libformergesortlists.dylib",
        PROJECT_ROOT / "build" / "macosx" / "arm64" / "release" / "libformergesortlists.dylib",
        PROJECT_ROOT / "build" / "macosx" / "arm64" / "release" / "libformergesortlists.so",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    # 若未命中，则返回默认构建路径并抛出友好异常
    default_target = (PROJECT_ROOT / "build" / "libformergesortlists.so").resolve()
    raise FileNotFoundError(
        f"未找到共享动态库文件！请先执行编译构建生成动态库。\n"
        f"已尝试查找的路径包括:\n" + "\n".join(f"  - {c}" for c in [default_target] + candidates)
    )


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
    根据指定负载特征类型生成多样化的测试数据集，涵盖标准规模、高并发分支、跨零负数、稠密重复、极端边界等场景
    """
    # 采用可复现的线程独立随机数生成器，保证结果确定性与多线程互不干扰
    rng = np.random.default_rng(seed=1000 + thread_id)
    lists: List[List[int]] = []

    if workload_type == "medium_scale":
        k = max(1, base_k)
        description = f"标准中等规模负载 ({k} 组正序列表，长度 10~{max_len})"
        for _ in range(k):
            length = int(rng.integers(10, max(11, max_len + 1)))
            steps = rng.integers(1, 10, size=length)
            sublist = np.cumsum(steps).tolist()
            lists.append(sublist)

    elif workload_type == "high_cardinality":
        k = max(2, base_k * 2)
        description = f"高分支短列表负载 ({k} 组短升序列表，考察多路分治调度)"
        for _ in range(k):
            length = int(rng.integers(5, 30))
            steps = rng.integers(1, 8, size=length)
            sublist = np.cumsum(steps).tolist()
            lists.append(sublist)

    elif workload_type == "negative_span":
        k = max(2, int(base_k * 0.8))
        description = f"负数与跨零混合负载 ({k} 组包含负数及跨零递增列表)"
        for _ in range(k):
            length = int(rng.integers(10, 80))
            start_val = int(rng.integers(-5000, -100))
            steps = rng.integers(1, 15, size=length)
            sublist = (start_val + np.cumsum(steps)).tolist()
            lists.append(sublist)

    elif workload_type == "dense_duplicates":
        k = max(2, int(base_k * 1.2))
        description = f"稠密重复元素负载 ({k} 组含大量等值元素列表，含单元素边界)"
        for i in range(k):
            if i % 10 == 0:
                # 边界情况：单元素列表
                lists.append([int(rng.integers(0, 1000))])
            else:
                length = int(rng.integers(5, 60))
                # 步长含 0，产生连续相同值
                steps = rng.integers(0, 4, size=length)
                base = int(rng.integers(0, 200))
                sublist = (base + np.cumsum(steps)).tolist()
                lists.append(sublist)

    elif workload_type == "boundary_extremes":
        k = max(5, int(base_k * 0.5))
        description = f"极端边界混合负载 ({k} 组含空列表、单元素、极值交织列表)"
        lists.append([])  # 空列表边界
        lists.append([int(rng.integers(-10000, 10000))])  # 单元素
        lists.append([-99999, 0, 99999])  # 跨极值三元组
        for _ in range(k - 3):
            sub_len = int(rng.integers(0, 20))
            if sub_len == 0:
                lists.append([])
            else:
                steps = rng.integers(1, 5, size=sub_len)
                sublist = (int(rng.integers(-500, 500)) + np.cumsum(steps)).tolist()
                lists.append(sublist)

    elif workload_type == "reverse_distributed":
        k = max(4, int(base_k * 0.6))
        description = f"逆序分布区间负载 ({k} 组子列表间呈大体逆序分布，考察跨区间归并)"
        for i in range(k):
            length = int(rng.integers(5, 40))
            base = (k - i) * 500
            steps = rng.integers(1, 5, size=length)
            sublist = (base + np.cumsum(steps)).tolist()
            lists.append(sublist)

    else:
        k = max(1, base_k)
        description = f"通用随机规模负载 (线程 {thread_id} 自适应生成，{k} 组列表)"
        for _ in range(k):
            length = int(rng.integers(5, max(6, max_len)))
            steps = rng.integers(1, 10, size=length)
            sublist = np.cumsum(steps).tolist()
            lists.append(sublist)

    return description, lists


def execute_merge_task(
    thread_id: int,
    worker_name: str,
    input_lists: List[List[int]],
    orchestrator: TaskOrchestrator,
) -> Tuple[int, str, List[List[int]], List[int], float, Optional[str]]:
    """
    单个并发工作线程的底层归并执行函数：调度 TaskOrchestrator 并精准记录归并耗时
    """
    start_time = time.perf_counter()
    try:
        # 调用 TaskOrchestrator 统筹高层调度并驱动 C++ 底层归并
        output_list = orchestrator.coordinate_execution(input_lists)
        duration = time.perf_counter() - start_time
        return thread_id, worker_name, input_lists, output_list, duration, None
    except Exception as exc:
        duration = time.perf_counter() - start_time
        return thread_id, worker_name, input_lists, [], duration, str(exc)


def verify_thread_result(
    thread_id: int,
    worker_name: str,
    input_lists: List[List[int]],
    output_list: List[int],
    duration: float,
    error_message: Optional[str] = None,
) -> ThreadTestResult:
    """
    对单个线程任务的归并结果执行严谨的数学属性校验与内容比对
    """
    total_elements = sum(len(sub) for sub in input_lists)
    num_lists = len(input_lists)

    if error_message is not None:
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
            error_message=error_message,
        )

    # 1. 元素总数量守恒校验
    is_length_valid = (len(output_list) == total_elements)

    # 2. 升序单调性校验
    is_sorted = all(output_list[i] <= output_list[i + 1] for i in range(len(output_list) - 1))

    # 3. 元素内容与基准排序结果比对校验
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
            file_after.write(
                f"### [Thread-{res.thread_id}] Status: {status_str} | "
                f"Merged Elements: {len(res.output_list)} | Cost: {res.duration:.6f}s\n"
            )
            file_after.write(" ".join(map(str, res.output_list)) + "\n\n")

    # 3. 统计汇总并生成性能评测报告 (docs/multithread_test_report.txt)
    total_elements_all = sum(res.total_elements for res in results)
    total_lists_all = sum(res.num_lists for res in results)
    sum_thread_duration = sum(res.duration for res in results)
    speedup = sum_thread_duration / wall_duration if wall_duration > 0 else 1.0
    overall_throughput = total_elements_all / wall_duration if wall_duration > 0 else 0.0
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
        f"并发归并总耗时  : {wall_duration:.6f} 秒 (Wall-clock Time)",
        f"线程执行耗时累加: {sum_thread_duration:.6f} 秒 (Cumulative Thread Time)",
        f"并发实际加速比  : {speedup:.2f}x",
        f"系统并发总吞吐率: {overall_throughput:,.1f} elements/sec",
        "--------------------------------------------------------------------------------",
        "各线程并发执行与正确性校验明细:",
        "--------------------------------------------------------------------------------",
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
    lib_path: Optional[str] = None,
    save_docs: bool = True,
    verbose: bool = True,
) -> bool:
    """
    主控测试流程：
    1. 初始化 TaskOrchestrator (加载 C++ 动态库)
    2. 预先生成各线程具有代表性的测试数据集
    3. 并发调度 coordinate_execution 并精准度量并行耗时
    4. 严谨校验输出正确性并统计性能指标
    5. 持久化数据与报告至 docs/ 目录
    """
    docs_dir = Path(docs_dir_path)
    if not docs_dir.is_absolute():
        docs_dir = (PROJECT_ROOT / docs_dir).resolve()

    resolved_lib = resolve_library_path(lib_path)

    if verbose:
        print("=" * 80)
        print(f"🚀 开始启动 TaskOrchestrator 多线程并发测试 (并发数: {num_threads})")
        print(f"📁 共享动态库路径: {resolved_lib}")
        print(f"📁 结果持久化目录: {docs_dir}")
        print("=" * 80)

    # 1. 实例化高层任务编排器
    orchestrator = TaskOrchestrator(str(resolved_lib))

    # 预设不同线程的业务测试场景目录
    workload_type_catalog = [
        "medium_scale",        # 场景 0：标准中等规模负载
        "high_cardinality",    # 场景 1：高分支短链表负载
        "negative_span",       # 场景 2：负数与跨零递增负载
        "dense_duplicates",    # 场景 3：重复值与边界单元素负载
        "boundary_extremes",   # 场景 4：极端边界与空列表负载
        "reverse_distributed", # 场景 5：逆序区间分布负载
    ]

    # [Stage 1] 预先准备数据，避免数据生成耗时干扰纯并发归并基准测试
    if verbose:
        print("\n[Stage 1] 正在准备各并发线程测试数据集...")
    prepared_workloads: List[Tuple[int, str, List[List[int]]]] = []
    for tid in range(num_threads):
        wtype = workload_type_catalog[tid % len(workload_type_catalog)]
        worker_name, input_lists = generate_workload_by_type(
            thread_id=tid,
            workload_type=wtype,
            base_k=base_k,
            max_len=max_len,
        )
        prepared_workloads.append((tid, worker_name, input_lists))
        if verbose:
            total_items = sum(len(sub) for sub in input_lists)
            print(f"  ✓ 线程 {tid} 数据就绪: {worker_name} (k={len(input_lists)}, 总元素={total_items})")

    # [Stage 2] 并发执行与精准计时
    if verbose:
        print(f"\n[Stage 2] 正在并发提交并调度 {num_threads} 个线程归并任务...")

    raw_results: List[Tuple[int, str, List[List[int]], List[int], float, Optional[str]]] = []
    wall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_tid = {
            executor.submit(
                execute_merge_task,
                tid,
                name,
                lists,
                orchestrator,
            ): tid
            for tid, name, lists in prepared_workloads
        }

        for future in as_completed(future_to_tid):
            tid = future_to_tid[future]
            try:
                res = future.result()
                raw_results.append(res)
            except Exception as exc:
                if verbose:
                    print(f"❌ 线程 {tid} 执行发生异常: {exc}")
                raw_results.append((tid, f"Thread-{tid}", [], [], 0.0, str(exc)))

    wall_duration = time.perf_counter() - wall_start

    # [Stage 3] 验证归并结果与统计性能
    if verbose:
        print(f"\n[Stage 3] 多线程并发归并完成，耗时: {wall_duration:.4f} 秒。正在严格校验正确性...")

    raw_results.sort(key=lambda r: r[0])
    results: List[ThreadTestResult] = [
        verify_thread_result(tid, name, inp, out, dur, err)
        for tid, name, inp, out, dur, err in raw_results
    ]

    # [Stage 4] 持久化数据到 docs 目录
    if save_docs:
        if verbose:
            print("\n[Stage 4] 正在将测试原始数据与归并结果持久化至 docs/ 目录...")
        before_p, after_p, report_p = save_multithread_results(
            docs_dir=docs_dir,
            results=results,
            wall_duration=wall_duration,
            library_path=str(resolved_lib),
        )
        if verbose:
            print(f"  ✓ 原始输入数据已保存至: {before_p}")
            print(f"  ✓ 归并排序结果已保存至: {after_p}")
            print(f"  ✓ 性能评测报告已保存至: {report_p}")

    # [Stage 5] 控制台打印汇总概览
    all_passed = all(res.passed for res in results)
    total_elements = sum(r.total_elements for r in results)
    sum_thread_duration = sum(r.duration for r in results)
    speedup = sum_thread_duration / wall_duration if wall_duration > 0 else 1.0
    overall_throughput = total_elements / wall_duration if wall_duration > 0 else 0.0

    if verbose:
        print("\n" + "=" * 80)
        print(f"📊 多线程执行与校验汇总 (总元素: {total_elements}, 状态: {'ALL PASSED' if all_passed else 'FAILED'}):")
        print(
            f"   并发耗时: {wall_duration:.4f}s | "
            f"线程累加: {sum_thread_duration:.4f}s | "
            f"加速比: {speedup:.2f}x | "
            f"总吞吐率: {overall_throughput:,.0f} it/s"
        )
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


class TestTaskOrchestratorMultithreading(unittest.TestCase):
    """支持集成进 unittest / CI 流程的单元测试用例集"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.lib_path = resolve_library_path()
        cls.orchestrator = TaskOrchestrator(str(cls.lib_path))

    def test_multithread_concurrency(self) -> None:
        """标准 4 线程并发压力与正确性集成测试"""
        passed = run_multithread_test(
            num_threads=4,
            base_k=50,
            max_len=50,
            docs_dir_path="docs",
            save_docs=True,
            verbose=False,
        )
        self.assertTrue(passed, "TaskOrchestrator 4 线程并发测试未全部通过！")

    def test_multithread_edge_cases(self) -> None:
        """并发边界与极端用例测试（空列表、单元素、极值分布）"""
        passed = run_multithread_test(
            num_threads=4,
            base_k=30,
            max_len=30,
            docs_dir_path="docs",
            save_docs=False,
            verbose=False,
        )
        self.assertTrue(passed, "TaskOrchestrator 边界并发测试未全部通过！")

    def test_direct_orchestrator_boundary_conditions(self) -> None:
        """TaskOrchestrator 核心接口直接调用的边界值校验"""
        # 1. 空输入测试
        self.assertEqual(self.orchestrator.coordinate_execution([]), [])

        # 2. 全空子列表集合
        self.assertEqual(self.orchestrator.coordinate_execution([[], [], []]), [])

        # 3. 单列表测试
        self.assertEqual(self.orchestrator.coordinate_execution([[1, 2, 3]]), [1, 2, 3])

        # 4. 混合空列表与有效列表
        mixed = [[], [5], [], [1, 3], [], [2, 4]]
        self.assertEqual(self.orchestrator.coordinate_execution(mixed), [1, 2, 3, 4, 5])

        # 5. 负数与跨零有序性
        neg_input = [[-10, -5, 0], [-7, -2, 3], [-1, 2, 4]]
        self.assertEqual(
            self.orchestrator.coordinate_execution(neg_input),
            [-10, -7, -5, -2, -1, 0, 2, 3, 4],
        )

        # 6. 大量重复元素
        dup_input = [[2, 2, 2], [2], [1, 2, 3]]
        self.assertEqual(
            self.orchestrator.coordinate_execution(dup_input),
            [1, 2, 2, 2, 2, 2, 3],
        )

    def test_multithread_scalability_8_threads(self) -> None:
        """高并发场景（8 工作线程）压力与正确性测试"""
        passed = run_multithread_test(
            num_threads=8,
            base_k=30,
            max_len=40,
            save_docs=False,
            verbose=False,
        )
        self.assertTrue(passed, "TaskOrchestrator 8 线程高并发测试未全部通过！")


def main() -> None:
    parser = argparse.ArgumentParser(description="TaskOrchestrator 多线程运行与评测测试脚本")
    parser.add_argument("--threads", type=int, default=4, help="并发执行的工作线程数量 (默认: 4)")
    parser.add_argument("--base-k", type=int, default=100, help="基准子列表数量 (默认: 100)")
    parser.add_argument("--max-len", type=int, default=100, help="子列表最大长度 (默认: 100)")
    parser.add_argument("--docs-dir", type=str, default="docs", help="数据与报告输出目录 (默认: docs)")
    parser.add_argument(
        "--lib-path",
        type=str,
        default=None,
        help="C++ 共享库路径 (默认自动探测: build/libformergesortlists.so 或 .dylib)",
    )
    parser.add_argument("--no-save", action="store_true", help="跳过结果文件落盘保存至 docs/ 目录")
    parser.add_argument("--quiet", "-q", action="store_true", help="减少控制台输出信息")

    args = parser.parse_args()

    success = run_multithread_test(
        num_threads=args.threads,
        base_k=args.base_k,
        max_len=args.max_len,
        docs_dir_path=args.docs_dir,
        lib_path=args.lib_path,
        save_docs=not args.no_save,
        verbose=not args.quiet,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
