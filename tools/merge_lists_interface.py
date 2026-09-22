import ctypes
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def find_default_library() -> Path:
    """按 Pitchfork 标准优先级查找动态共享库"""
    candidates = [
        PROJECT_ROOT / "lib" / "libformergesortlists.dylib",
        PROJECT_ROOT / "lib" / "libformergesortlists.so",
        PROJECT_ROOT / "build" / "libformergesortlists.dylib",
        PROJECT_ROOT / "build" / "libformergesortlists.so",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


class MergeSortedListsInterface:
    def __init__(self, library_path: Optional[str] = None) -> None:
        target_path = Path(library_path) if library_path else find_default_library()
        if not target_path.exists():
            raise FileNotFoundError(f"Dynamic library not found at: {target_path}")

        self._lib = ctypes.CDLL(str(target_path))

        # 声明 C 接口函数的参数类型与返回值类型
        self._lib.merge_k_lists_c_api.argtypes = [
            ctypes.POINTER(ctypes.c_int),  # flat_data
            ctypes.POINTER(ctypes.c_int),  # lengths
            ctypes.c_int,                  # k
            ctypes.POINTER(ctypes.c_int),  # out_size
        ]
        self._lib.merge_k_lists_c_api.restype = ctypes.POINTER(ctypes.c_int)

        self._lib.merge_k_spans_c_api.argtypes = [
            ctypes.POINTER(ctypes.c_int),  # flat_data
            ctypes.POINTER(ctypes.c_int),  # lengths
            ctypes.c_int,                  # k
            ctypes.POINTER(ctypes.c_int),  # out_size
        ]
        self._lib.merge_k_spans_c_api.restype = ctypes.POINTER(ctypes.c_int)

        self._lib.free_merged_result.argtypes = [ctypes.POINTER(ctypes.c_int)]
        self._lib.free_merged_result.restype = None

    def merge(self, lists_of_lists: List[List[int]], use_spans: bool = True) -> List[int]:
        k = len(lists_of_lists)
        if k == 0:
            return []

        lengths = [len(lst) for lst in lists_of_lists]
        flat_data = [item for lst in lists_of_lists for item in lst]

        c_lengths = (ctypes.c_int * k)(*lengths)
        c_flat_data = (ctypes.c_int * len(flat_data))(*flat_data)
        out_size = ctypes.c_int(0)

        # 优先调用高性能连续内存 span 接口
        c_func = self._lib.merge_k_spans_c_api if use_spans else self._lib.merge_k_lists_c_api
        result_ptr = c_func(
            c_flat_data, c_lengths, k, ctypes.byref(out_size)
        )

        if out_size.value == 0 or not result_ptr:
            return []

        result_list = [result_ptr[i] for i in range(out_size.value)]
        self._lib.free_merged_result(result_ptr)

        return result_list
