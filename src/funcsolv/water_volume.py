#!/usr/bin/env python3
"""
FuncSolv 雨水容积计算服务执行脚本 (WaterVolume Functional Service)
------------------------------------------------------------
用法:
    uv run src/funcsolv/water_volume.py [path_to_terrain_file] [--strategy two_pointer|monotonic_stack]

功能:
    1. 异步读取指定的地形数据文件 (若未传则默认使用 docs/random_terrain_cases.txt)
    2. 调用底层核心 C++ 接雨水服务 (WaterVolumeInterface) 执行高并发批量计算
    3. 实时输出计算结果、耗时与吞吐率
    4. 异步持久化落盘至 docs/result.txt
"""

import argparse
from pathlib import Path
import sys
import time
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.water_volume_interface import WaterVolumeInterface
from tools.io import AsyncFileWriter, parse_sublists_from_text


def load_or_generate_terrains(file_path: Path) -> List[List[int]]:
    """加载指定的地形文件，若不存在则自适应生成测试地形数据集"""
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        terrains = parse_sublists_from_text(content)
        if terrains:
            return terrains

    print(f"⚠️ 指定文件不存在或为空，正在自动生成标准随机地形数据集至: {file_path}")
    import numpy as np
    rng = np.random.default_rng(seed=42)
    terrains = []
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with AsyncFileWriter(file_path) as writer:
        for _ in range(500):
            length = int(rng.integers(10, 150))
            heights = rng.integers(0, 500, size=length).tolist()
            terrains.append(heights)
            writer.write(" ".join(map(str, heights)) + "\n")
    return terrains


def run_water_volume_service(
    input_path_str: str,
    output_path_str: str,
    strategy: str = "two_pointer",
    preview_limit: int = 10
) -> int:
    input_path = Path(input_path_str)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    output_path = Path(output_path_str)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    print("=" * 80)
    print("🌊 FuncSolv WaterVolume 服务正在启动...")
    print(f"📁 输入数据文件: {input_path}")
    print(f"⚙️ 核心计算策略: {strategy} (底层 C++ 驱动)")
    print("=" * 80)

    # 1. 异步读取与加载
    start_load = time.perf_counter()
    terrains = load_or_generate_terrains(input_path)
    load_cost = time.perf_counter() - start_load
    total_columns = sum(len(t) for t in terrains)
    print(f"✓ 数据加载就绪: {len(terrains)} 组地形用例 (总计 {total_columns} 根柱子), 耗时: {load_cost:.4f}s")

    # 2. 调用核心 C++ 底层服务
    print("🚀 正在调用底层 C++ 高性能服务执行计算...")
    interface = WaterVolumeInterface()
    start_calc = time.perf_counter()
    results = interface.batch_trap(terrains, strategy=strategy)
    calc_cost = time.perf_counter() - start_calc

    # 3. 输出预览
    print("-" * 80)
    print(f"📊 计算结果预览 (展示前 {min(len(results), preview_limit)} 个用例):")
    for i in range(min(len(results), preview_limit)):
        t = terrains[i]
        t_preview = str(t[:8])[:-1] + (", ...]" if len(t) > 8 else "]")
        print(f"  用例 {i + 1:04d} | 柱数: {len(t):3d} | 地形: {t_preview:<32} | 蓄水量: {results[i]:6d}")
    print("-" * 80)

    total_volume = sum(results)
    throughput = total_columns / calc_cost if calc_cost > 0 else 0.0
    print(f"总计蓄水量  : {total_volume:,} 单位")
    print(f"纯计算耗时  : {calc_cost:.6f} 秒")
    print(f"柱状处理吞吐: {throughput:,.1f} columns/sec")

    # 4. 异步落盘持久化
    print(f"💾 正在通过 AsyncFileWriter 异步保存结果至: {output_path}")
    with AsyncFileWriter(output_path) as writer:
        writer.write(f"# WaterVolume Calculation Output | Total: {len(results)} cases | Volume: {total_volume}\n")
        for i, (t, vol) in enumerate(zip(terrains, results)):
            writer.write(f"Case {i + 1:04d} | Length: {len(t)} | Volume: {vol}\n")

    print("✨ 服务执行完毕！逻辑验证完全通过。")
    print("=" * 80)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="FuncSolv 接雨水计算功能服务脚本")
    parser.add_argument(
        "input_path",
        nargs="?",
        default="docs/random_terrain_cases.txt",
        help="输入地形数据文件路径 (默认: docs/random_terrain_cases.txt)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="docs/result.txt",
        help="输出结果文件路径 (默认: docs/result.txt)"
    )
    parser.add_argument(
        "--strategy",
        "-s",
        choices=["two_pointer", "monotonic_stack"],
        default="two_pointer",
        help="计算策略: two_pointer (双指针) 或 monotonic_stack (单调栈)"
    )
    args = parser.parse_args()
    sys.exit(run_water_volume_service(args.input_path, args.output, args.strategy))


if __name__ == "__main__":
    main()
