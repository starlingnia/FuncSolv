import ctypes
import os
from typing import List

class MergeSortedListsInterface:
    def __init__(self, library_path: str) -> None:
        # 加载编译生成的 C++ 共享库
        self._lib = ctypes.CDLL(library_path)
        
        # 声明 C 接口函数的参数类型与返回值类型
        self._lib.merge_k_lists_c_api.argtypes = [
            ctypes.POINTER(ctypes.c_int), # flat_data
            ctypes.POINTER(ctypes.c_int), # lengths
            ctypes.c_int,                 # k
            ctypes.POINTER(ctypes.c_int)  # out_size
        ]
        self._lib.merge_k_lists_c_api.restype = ctypes.POINTER(ctypes.c_int)
        
        self._lib.free_merged_result.argtypes = [ctypes.POINTER(ctypes.c_int)]
        self._lib.free_merged_result.restype = None

    def merge(self, lists_of_lists: List[List[int]]) -> List[int]:
        k = len(lists_of_lists)
        if k == 0:
            return []

        lengths = [len(lst) for lst in lists_of_lists]
        flat_data = [item for lst in lists_of_lists for item in lst]

        # 转换为 ctypes 兼容数组
        c_lengths = (ctypes.c_int * k)(*lengths)
        c_flat_data = (ctypes.c_int * len(flat_data))(*flat_data)
        out_size = ctypes.c_int(0)

        # 调用底层 C++ 并发归并引擎
        result_ptr = self._lib.merge_k_lists_c_api(
            c_flat_data, c_lengths, k, ctypes.byref(out_size)
        )

        if out_size.value == 0 or not result_ptr:
            return []

        # 将底层返回的连续内存转换为 Python 列表
        result_list = [result_ptr[i] for i in range(out_size.value)]
        
        # 释放 C++ 分配的堆内存
        self._lib.free_merged_result(result_ptr)

        return result_list
