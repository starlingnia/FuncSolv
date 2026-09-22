"""
FuncSolv 核心服务功能包
------------------------------------------------------------
用户可直接在终端中调用各业务功能脚本查看服务逻辑与执行输出:
    - uv run src/funcsolv/water_volume.py [path_to_terrain_file]
    - uv run src/funcsolv/merge_sorted_lists.py [path_to_sublists_file]
"""

from funcsolv.water_volume import run_water_volume_service
from funcsolv.merge_sorted_lists import run_merge_sorted_lists_service


def main() -> None:
    print("=" * 70)
    print("🚀 FuncSolv 算法与高性能科学计算服务套件")
    print("=" * 70)
    print("可用功能服务脚本:")
    print("  1. 接雨水容积计算服务:")
    print("     uv run src/funcsolv/water_volume.py [path_to_terrain_cases.txt]")
    print("  2. 多路有序列表归并服务:")
    print("     uv run src/funcsolv/merge_sorted_lists.py [path_to_sublists.txt]")
    print("=" * 70)


__all__ = [
    "run_water_volume_service",
    "run_merge_sorted_lists_service",
    "main",
]
