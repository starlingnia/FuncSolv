"""
TaskOrchestrator 多线程并发调度与正确性评测自动化测试脚本
------------------------------------------------------------
- 基于模块化编程思想，将 IO 落盘、数据序列化与用例生成下沉至 funcsolv.io 组件
- 采用非阻塞异步文件写出器 (AsyncFileWriter)，消除主线程与工作线程全量阻塞
- 涵盖各种不同特征的业务负载数据集（标准规模、高分支、跨零负数、稠密重复、极端边界、逆序区间）
- 对并发输出结果进行严格的数学属性校验：数量守恒、单调递增有序性、全量元素内容一致性
- 实时统计各线程与系统维度的耗时、吞吐率与并行加速比
- 全面集成 unittest 测试用例，便于接入 CI/CD 流水线与自动化测试流程
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
import time
from typing import List, Optional, Tuple
import unittest

# 配置模块导入路径
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

for path_entry in (str(PROJECT_ROOT), str(SRC_DIR)):
    if path_entry not in sys.path:
        sys.path.insert(0, path_entry)

from tools.orsortlist import TaskOrchestrator
from tools.io import (
    AsyncFileWriter,
    serialize_thread_input_block,
    serialize_thread_output_block,
    format_multithread_report,
    generate_workload_by_type,
)


def resolve_library_path(custom_path: Optional[str] = None) -> Path:
    """
    智能解析 C++ 动态共享库路径，遵循 Pitchfork 规范优先定位 lib/ 目录
    """
    if custom_path:
        target = Path(custom_path)
        if not target.is_absolute():
            target = (PROJECT_ROOT / target).resolve()
        if target.exists():
            return target

    candidates = [
        PROJECT_ROOT / "lib" / "libformergesortlists.dylib",
        PROJECT_ROOT / "lib" / "libformergesortlists.so",
        PROJECT_ROOT / "build" / "libformergesortlists.dylib",
        PROJECT_ROOT / "build" / "libformergesortlists.so",
        PROJECT_ROOT / "bin" / "libformergesortlists.dylib",
        PROJECT_ROOT / "bin" / "libformergesortlists.so",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    default_target = (PROJECT_ROOT / "lib" / "libformergesortlists.dylib").resolve()
    raise FileNotFoundError(
        f"未找到共享动态库文件！请先执行 `xmake` 编译构建生成动态库。\n"
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
        # 并发执行时静默控制台，避免 stdout 锁争用
        output_list = orchestrator.coordinate_execution(input_lists, verbose=False)
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
    is_length_valid = len(output_list) == total_elements

    # 2. 升序单调性校验
    is_sorted = all(output_list[i] <= output_list[i + 1] for i in range(len(output_list) - 1))

    # 3. 元素内容与基准排序结果比对校验
    ground_truth = sorted([item for sub in input_lists for item in sub])
    is_content_valid = output_list == ground_truth

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


def save_multithread_results_async(
    docs_dir: Path,
    results: List[ThreadTestResult],
    wall_duration: float,
    library_path: str,
) -> Tuple[Path, Path, Path]:
    """
    利用 AsyncFileWriter 异步非阻塞持久化落盘输入、输出及性能评测报告
    """
    docs_dir.mkdir(parents=True, exist_ok=True)

    before_path = docs_dir / "multithread_data_before.txt"
    after_path = docs_dir / "multithread_data_after.txt"
    report_path = docs_dir / "multithread_test_report.txt"

    with AsyncFileWriter(before_path) as writer_before, \
         AsyncFileWriter(after_path) as writer_after, \
         AsyncFileWriter(report_path) as writer_report:

        # 1. 异步非阻塞写入原始输入数据
        before_header = (
            "# ==============================================================================\n"
            "# TaskOrchestrator 多线程并发测试 - 处理前原始输入数据集\n"
            f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "# 格式规范: 每个线程数据由标识行开始，随后每一行表示一个升序子列表，数字空格隔开\n"
            "# ==============================================================================\n\n"
        )
        writer_before.write(before_header)
        for res in results:
            writer_before.write(
                serialize_thread_input_block(res.thread_id, res.worker_name, res.input_lists)
            )

        # 2. 异步非阻塞写入归并结果
        after_header = (
            "# ==============================================================================\n"
            "# TaskOrchestrator 多线程并发测试 - 处理后最终有序合并结果\n"
            f"# 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "# 格式规范: 每个线程对应一行完整的全局升序排列结果\n"
            "# ==============================================================================\n\n"
        )
        writer_after.write(after_header)
        for res in results:
            writer_after.write(
                serialize_thread_output_block(res.thread_id, res.passed, res.output_list, res.duration)
            )

        # 3. 异步非阻塞写入评测报告
        report_content = format_multithread_report(
            results=results,
            wall_duration=wall_duration,
            library_path=library_path,
            docs_dir=str(docs_dir),
        )
        writer_report.write(report_content)

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
    2. 预先生成各线程具有代表性的测试数据集 (模块化 generator)
    3. 并发调度 coordinate_execution 并精准度量并行耗时
    4. 严谨校验输出正确性并统计性能指标
    5. 通过 AsyncFileWriter 非阻塞持久化数据与报告至 docs/ 目录
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

    orchestrator = TaskOrchestrator(str(resolved_lib), verbose=False)

    workload_type_catalog = [
        "medium_scale",        # 场景 0：标准中等规模负载
        "high_cardinality",    # 场景 1：高分支短链表负载
        "negative_span",       # 场景 2：负数与跨零递增负载
        "dense_duplicates",    # 场景 3：重复值与边界单元素负载
        "boundary_extremes",   # 场景 4：极端边界与空列表负载
        "reverse_distributed", # 场景 5：逆序区间分布负载
    ]

    # [Stage 1] 模块化生成数据
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

    # [Stage 4] 异步非阻塞持久化数据到 docs 目录
    if save_docs:
        if verbose:
            print("\n[Stage 4] 正在通过 AsyncFileWriter 异步非阻塞持久化至 docs/ 目录...")
        before_p, after_p, report_p = save_multithread_results_async(
            docs_dir=docs_dir,
            results=results,
            wall_duration=wall_duration,
            library_path=str(resolved_lib),
        )
        if verbose:
            print(f"  ✓ 原始输入数据已异步写入: {before_p}")
            print(f"  ✓ 归并排序结果已异步写入: {after_p}")
            print(f"  ✓ 性能评测报告已异步写入: {report_p}")

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
        cls.orchestrator = TaskOrchestrator(str(cls.lib_path), verbose=False)

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
        self.assertEqual(self.orchestrator.coordinate_execution([]), [])
        self.assertEqual(self.orchestrator.coordinate_execution([[], [], []]), [])
        self.assertEqual(self.orchestrator.coordinate_execution([[1, 2, 3]]), [1, 2, 3])
        mixed = [[], [5], [], [1, 3], [], [2, 4]]
        self.assertEqual(self.orchestrator.coordinate_execution(mixed), [1, 2, 3, 4, 5])
        neg_input = [[-10, -5, 0], [-7, -2, 3], [-1, 2, 4]]
        self.assertEqual(
            self.orchestrator.coordinate_execution(neg_input),
            [-10, -7, -5, -2, -1, 0, 2, 3, 4],
        )
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
        help="C++ 共享库路径 (默认自动探测: lib/libformergesortlists.dylib 或 .so)",
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
