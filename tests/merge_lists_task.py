import os
import time
import numpy as np
from funcsolv.merge_lists_interface import MergeSortedListsInterface

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

def save_test_data(input_lists: list, output_list: list) -> None:
    """自动创建 docs 目录，并将数据处理前与处理后的内容完整写入文本文件"""
    os.makedirs("docs", exist_ok=True)
    
    # 预先将所有子列表转换为格式化字符串集合，随后通过 writelines 完成批量写入
    input_path = "docs/savedata_before.txt"
    formatted_lines = [
        " ".join(str(item) for item in sublist) + "\n"
        for sublist in input_lists
    ]
    with open(input_path, "w", encoding="utf-8") as file_handle:
        file_handle.writelines(formatted_lines)
            
    # 记录处理后的最终归并排序结果
    output_path = "docs/savedata_after.txt"
    output_content = " ".join(str(item) for item in output_list) + "\n"
    with open(output_path, "w", encoding="utf-8") as file_handle:
        file_handle.write(output_content)
        
    print(f"数据处理前的原始输入已保存至路径: {input_path}")
    print(f"数据处理后的最终结果已保存至路径: {output_path}")

def run_performance_test() -> None:
    print("正在初始化 C++ 共享库接口...")
    interface = MergeSortedListsInterface("build/libformergesortlists.so")

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

    # 执行处理前与处理后数据的落盘保存
    save_test_data(reconstructed_lists, sorted_result)

    is_sorted = all(sorted_result[i] <= sorted_result[i+1] for i in range(len(sorted_result) - 1))
    if is_sorted:
        print("校验通过：输出结果严格符合升序排列规范。")
    else:
        print("校验失败：输出结果存在逆序对。")

if __name__ == "__main__":
    run_performance_test()


