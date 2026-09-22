"""
多路有序列表归并单次压测任务
------------------------------------------------------------
- 采用 funcsolv.io 异步写出器与数据序列化器，完成数据落盘
- 杜绝传统文件写盘造成的全量同步阻塞
"""

from pathlib import Path
import sys
import time
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.merge_lists_interface import MergeSortedListsInterface
from tools.io import AsyncFileWriter, serialize_sublists, serialize_single_line


def generate_random_sorted_sublists(num_lists: int, max_length: int) -> tuple:
    """利用 NumPy 向量化操作高效生成多个随机升序列表的扁平数据与长度数组"""
    all_data_list = []
    lengths = []

    for _ in range(num_lists):
        length = np.random.randint(5, max_length)
        lengths.append(length)

        steps = np.random.randint(1, 10, size=length)
        sub_list = np.cumsum(steps)
        all_data_list.extend(sub_list.tolist())

    all_data = np.array(all_data_list, dtype=np.int32)
    return all_data, lengths, num_lists


def save_test_data_async(input_lists: list, output_list: list, docs_dir: Path) -> None:
    """通过 AsyncFileWriter 异步非阻塞持久化落盘处理前与处理后的数据"""
    docs_dir.mkdir(parents=True, exist_ok=True)
    before_path = docs_dir / "savedata_before.txt"
    after_path = docs_dir / "savedata_after.txt"

    with AsyncFileWriter(before_path) as writer_before, AsyncFileWriter(after_path) as writer_after:
        # 非阻塞投递序列化内容
        writer_before.write(serialize_sublists(input_lists))
        writer_after.write(serialize_single_line(output_list))

    print(f"数据处理前的原始输入已异步保存至路径: {before_path}")
    print(f"数据处理后的最终结果已异步保存至路径: {after_path}")


def run_performance_test() -> None:
    print("正在初始化 C++ 共享库接口...")
    interface = MergeSortedListsInterface()

    print("正在使用 NumPy 生成大规模随机测试用例...")
    num_lists = 1000
    max_length = 200

    start_gen = time.time()
    all_flat_data, lengths, k = generate_random_sorted_sublists(num_lists, max_length)

    reconstructed_lists = []
    offset = 0
    for length in lengths:
        reconstructed_lists.append(all_flat_data[offset : offset + length].tolist())
        offset += length

    print(f"用例生成完毕，总计包含 {k} 个升序列表，耗时: {time.time() - start_gen:.4f} 秒。")

    print("开始调用底层 C++ 多线程并发归并引擎...")
    start_calc = time.time()
    sorted_result = interface.merge(reconstructed_lists)
    calc_duration = time.time() - start_calc

    print(f"底层并发计算完成，合并后总元素数量: {len(sorted_result)}")
    print(f"C++ 并发执行耗时: {calc_duration:.6f} 秒。")

    # 执行非阻塞异步数据落盘
    docs_dir = PROJECT_ROOT / "docs"
    save_test_data_async(reconstructed_lists, sorted_result, docs_dir)

    is_sorted = all(sorted_result[i] <= sorted_result[i + 1] for i in range(len(sorted_result) - 1))
    if is_sorted:
        print("校验通过：输出结果严格符合升序排列规范。")
    else:
        print("校验失败：输出结果存在逆序对。")


if __name__ == "__main__":
    run_performance_test()
