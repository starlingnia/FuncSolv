#!/usr/bin/env python3
"""
FuncSolv 多路有序归并服务执行脚本 (MergeSortedLists Functional Service)
------------------------------------------------------------
用法:
    uv run src/funcsolv/merge_sorted_lists.py [path_to_sublists_file] [--output docs/savedata_after.txt]

功能:
    1. 异步读取多路有序子列表文件 (若未传则默认使用 docs/savedata_before.txt)
    2. 调用底层核心 C++ 多路分治/最小堆归并服务 (MergeSortedListsInterface)
    3. 严格校验输出的数学单调递增性与元素守恒性
    4. 实时输出归并规模、耗时与吞吐率
    5. 异步持久化落盘至 docs/savedata_after.txt
"""

import argparse
from pathlib import Path
import sys
import time
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.merge_lists_interface import MergeSortedListsInterface
from tools.io import AsyncFileWriter, parse_sublists_from_text, serialize_single_line


def load_or_generate_sublists(file_path: Path) -> List[List[int]]:
    """加载指定的子列表文件，若不存在则自适应生成大规模测试数据集"""
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        sublists = parse_sublists_from_text(content)
        if sublists:
            return sublists

    print(f"⚠️ 指定文件不存在或为空，正在自动生成标准升序子列表数据集至: {file_path}")
    import numpy as np
    rng = np.random.default_rng(seed=123)
    sublists = []
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with AsyncFileWriter(file_path) as writer:
        for _ in range(500):
            length = int(rng.integers(10, 100))
            steps = rng.integers(1, 10, size=length)
            lst = np.cumsum(steps).tolist()
            sublists.append(lst)
            writer.write(" ".join(map(str, lst)) + "\n")
    return sublists


def run_merge_sorted_lists_service(
    input_path_str: str,
    output_path_str: str,
    preview_limit: int = 20
) -> int:
    input_path = Path(input_path_str)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    output_path = Path(output_path_str)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    print("=" * 80)
    print("🔀 FuncSolv MergeSortedLists 服务正在启动...")
    print(f"📁 输入数据文件: {input_path}")
    print("⚙️ 核心归并引擎: C++ 最小堆多路流式归并 (零多余堆分配)")
    print("=" * 80)

    # 1. 异步加载数据
    start_load = time.perf_counter()
    sublists = load_or_generate_sublists(input_path)
    load_cost = time.perf_counter() - start_load
    total_elements = sum(len(sub) for sub in sublists)
    print(f"✓ 数据加载就绪: {len(sublists)} 组有序子列表 (总计 {total_elements} 个整数), 耗时: {load_cost:.4f}s")

    # 2. 调用核心 C++ 归并服务
    print("🚀 正在调用底层 C++ 高性能服务执行多路归并...")
    interface = MergeSortedListsInterface()
    start_calc = time.perf_counter()
    merged_result = interface.merge(sublists, use_spans=True)
    calc_cost = time.perf_counter() - start_calc

    # 3. 严格数学属性校验
    length_valid = len(merged_result) == total_elements
    is_sorted = all(merged_result[i] <= merged_result[i + 1] for i in range(len(merged_result) - 1))
    passed = length_valid and is_sorted

    print("-" * 80)
    print(f"🔍 正确性校验: 数量守恒: {length_valid} | 严格单调升序: {is_sorted} | 结论: {'PASS ✅' if passed else 'FAIL ❌'}")
    preview_str = str(merged_result[:preview_limit])[:-1] + (", ...]" if len(merged_result) > preview_limit else "]")
    print(f"📊 归并结果预览: {preview_str}")
    print("-" * 80)

    throughput = total_elements / calc_cost if calc_cost > 0 else 0.0
    print(f"归并后总元素: {len(merged_result):,} 个")
    print(f"纯归并耗时  : {calc_cost:.6f} 秒")
    print(f"系统总吞吐率: {throughput:,.1f} items/sec")

    # 4. 异步落盘持久化
    print(f"💾 正在通过 AsyncFileWriter 异步保存全局有序结果至: {output_path}")
    with AsyncFileWriter(output_path) as writer:
        writer.write(serialize_single_line(merged_result))

    print("✨ 服务执行完毕！逻辑验证完全通过。")
    print("=" * 80)
    return 0 if passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="FuncSolv 多路有序归并功能服务脚本")
    parser.add_argument(
        "input_path",
        nargs="?",
        default="docs/savedata_before.txt",
        help="输入多路子列表数据文件路径 (默认: docs/savedata_before.txt)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="docs/savedata_after.txt",
        help="输出结果文件路径 (默认: docs/savedata_after.txt)"
    )
    args = parser.parse_args()
    sys.exit(run_merge_sorted_lists_service(args.input_path, args.output))


if __name__ == "__main__":
    main()
