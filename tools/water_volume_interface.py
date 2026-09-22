"""
接雨水容积计算 Python 接口层 (WaterVolumeInterface)
------------------------------------------------------------
- 遵循 Pitchfork 标准：接口层脚本位于 tools/ 目录下
- 通过 ctypes 动态载入 lib/ 下的 C-ABI 共享库
- 封装底层 C++ 高性能计算接口，支持单地形计算与多地形并行批量计算
- 支持指定算法策略: "two_pointer" (双指针) 或 "monotonic_stack" (单调栈)
"""

import ctypes
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def find_default_library() -> Path:
    """按 Pitchfork 标准优先级查找动态共享库"""
    candidates = [
        PROJECT_ROOT / "lib" / "libforwatervolumes.dylib",
        PROJECT_ROOT / "lib" / "libforwatervolumes.so",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


class WaterVolumeInterface:
    def __init__(self, library_path: Optional[str] = None) -> None:
        target_path = Path(library_path) if library_path else find_default_library()
        if not target_path.exists():
            raise FileNotFoundError(f"Dynamic library not found at: {target_path}")

        self._lib = ctypes.CDLL(str(target_path))
        self._setup_bindings()

    def _setup_bindings(self) -> None:
        # 单个用例计算接口
        self._lib.trap_water_c_api.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
        ]
        self._lib.trap_water_c_api.restype = ctypes.c_int

        # 批量并发计算接口
        self._lib.batch_trap_water_c_api.argtypes = [
            ctypes.POINTER(ctypes.c_int),  # flat_heights
            ctypes.POINTER(ctypes.c_int),  # lengths
            ctypes.c_int,                  # k
            ctypes.c_int,                  # strategy
            ctypes.POINTER(ctypes.c_int),  # out_results
        ]
        self._lib.batch_trap_water_c_api.restype = None

    def trap(self, heights: List[int], strategy: str = "two_pointer") -> int:
        """计算单个地形柱状图的蓄水量"""
        if len(heights) <= 2:
            return 0

        strategy_code = 1 if strategy == "monotonic_stack" else 0
        c_arr = (ctypes.c_int * len(heights))(*heights)
        return int(self._lib.trap_water_c_api(c_arr, len(heights), strategy_code))

    def batch_trap(
        self, 
        list_of_heights: List[List[int]], 
        strategy: str = "two_pointer"
    ) -> List[int]:
        """批量多地形并发计算蓄水量"""
        k = len(list_of_heights)
        if k == 0:
            return []

        strategy_code = 1 if strategy == "monotonic_stack" else 0
        lengths = [len(h) for h in list_of_heights]
        flat_heights = [x for h in list_of_heights for x in h]

        c_lengths = (ctypes.c_int * k)(*lengths)
        c_flat = (ctypes.c_int * len(flat_heights))(*flat_heights)
        out_results = (ctypes.c_int * k)()

        self._lib.batch_trap_water_c_api(
            c_flat, c_lengths, k, strategy_code, out_results
        )

        return [out_results[i] for i in range(k)]
