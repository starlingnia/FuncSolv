import ctypes
import os

class TaskOrchestrator:
    def __init__(self, library_path: str) -> None:
        self.library_path = library_path
        print(f"Python 高层调度器初始化完成：正在加载动态共享库 -> {library_path}")
        
        # 加载编译生成的 C++ 共享库
        self._lib = ctypes.CDLL(library_path)
        self._setup_bindings()

    def _setup_bindings(self) -> None:
        """绑定 C++ 导出的 C 兼容接口及数据类型"""
        self._lib.merge_k_lists_c_api.argtypes = [
            ctypes.POINTER(ctypes.c_int), # flat_data
            ctypes.POINTER(ctypes.c_int), # lengths
            ctypes.c_int,                 # k
            ctypes.POINTER(ctypes.c_int)  # out_size
        ]
        self._lib.merge_k_lists_c_api.restype = ctypes.POINTER(ctypes.c_int)
        
        self._lib.free_merged_result.argtypes = [ctypes.POINTER(ctypes.c_int)]
        self._lib.free_merged_result.restype = None

    def coordinate_execution(self, lists_of_lists: list[list[int]]) -> list[int]:
        """高层业务编排：统筹参数转换并驱动 C++ 底层并发核心"""
        print("当前阶段：由 Python 负责高层任务编排，准备向 C++ 传递数据...")
        
        k = len(lists_of_lists)
        if k == 0:
            return []

        lengths = [len(lst) for lst in lists_of_lists]
        flat_data = [item for lst in lists_of_lists for item in lst]

        c_lengths = (ctypes.c_int * k)(*lengths)
        c_flat_data = (ctypes.c_int * len(flat_data))(*flat_data)
        out_size = ctypes.c_int(0)

        # 真正调用底层 C++ 多线程并发归并引擎
        result_ptr = self._lib.merge_k_lists_c_api(
            c_flat_data, c_lengths, k, ctypes.byref(out_size)
        )

        if out_size.value == 0 or not result_ptr:
            return []

        result_list = [result_ptr[i] for i in range(out_size.value)]
        
        # 释放底层分配的堆内存
        self._lib.free_merged_result(result_ptr)

        print(f"底层并发计算完成，成功合并返回 {len(result_list)} 个有序元素。")
        return result_list

if __name__ == "__main__":
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    lib_candidates = [
        project_root / "build" / "libformergesortlists.so",
        project_root / "build" / "libformergesortlists.dylib",
    ]
    lib_path = next((p for p in lib_candidates if p.exists()), None)
    if lib_path:
        orchestrator = TaskOrchestrator(str(lib_path))
        sample_input = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
        result = orchestrator.coordinate_execution(sample_input)
        print(f"示例运行结果: {result}")
    else:
        print("未找到 C++ 共享库，请先编译生成对应库。")

