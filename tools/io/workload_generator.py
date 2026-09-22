"""
测试工作负载生成组件 (Workload Generator)
------------------------------------------------------------
- 核心功能单一：根据特征类型（标准规模、高并发分支、跨零负数、稠密重复、极端边界等）
  使用向量化 NumPy 生成升序子列表数据
- 具备种子独立性，便于多线程与多任务并发解耦生成
"""

from typing import List, Tuple
import numpy as np


def generate_workload_by_type(
    thread_id: int,
    workload_type: str,
    base_k: int = 100,
    max_len: int = 100,
) -> Tuple[str, List[List[int]]]:
    """
    根据负载特征类型生成多样化的测试数据集：
    - medium_scale: 标准中等规模正序列表
    - high_cardinality: 高分支短列表（考察多路分治调度）
    - negative_span: 负数与跨零混合递增列表
    - dense_duplicates: 稠密重复元素列表（含单元素边界）
    - boundary_extremes: 极端边界混合列表（含空列表、单元素、极值三元组）
    - reverse_distributed: 区间大体逆序分布列表（考察跨区间归并）
    """
    rng = np.random.default_rng(seed=1000 + thread_id)
    lists: List[List[int]] = []

    if workload_type == "medium_scale":
        k = max(1, base_k)
        description = f"标准中等规模负载 ({k} 组正序列表，长度 10~{max_len})"
        for _ in range(k):
            length = int(rng.integers(10, max(11, max_len + 1)))
            steps = rng.integers(1, 10, size=length)
            sublist = np.cumsum(steps).tolist()
            lists.append(sublist)

    elif workload_type == "high_cardinality":
        k = max(2, base_k * 2)
        description = f"高分支短列表负载 ({k} 组短升序列表，考察多路分治调度)"
        for _ in range(k):
            length = int(rng.integers(5, 30))
            steps = rng.integers(1, 8, size=length)
            sublist = np.cumsum(steps).tolist()
            lists.append(sublist)

    elif workload_type == "negative_span":
        k = max(2, int(base_k * 0.8))
        description = f"负数与跨零混合负载 ({k} 组包含负数及跨零递增列表)"
        for _ in range(k):
            length = int(rng.integers(10, 80))
            start_val = int(rng.integers(-5000, -100))
            steps = rng.integers(1, 15, size=length)
            sublist = (start_val + np.cumsum(steps)).tolist()
            lists.append(sublist)

    elif workload_type == "dense_duplicates":
        k = max(2, int(base_k * 1.2))
        description = f"稠密重复元素负载 ({k} 组含大量等值元素列表，含单元素边界)"
        for i in range(k):
            if i % 10 == 0:
                lists.append([int(rng.integers(0, 1000))])
            else:
                length = int(rng.integers(5, 60))
                steps = rng.integers(0, 4, size=length)
                base = int(rng.integers(0, 200))
                sublist = (base + np.cumsum(steps)).tolist()
                lists.append(sublist)

    elif workload_type == "boundary_extremes":
        k = max(5, int(base_k * 0.5))
        description = f"极端边界混合负载 ({k} 组含空列表、单元素、极值交织列表)"
        lists.append([])
        lists.append([int(rng.integers(-10000, 10000))])
        lists.append([-99999, 0, 99999])
        for _ in range(k - 3):
            sub_len = int(rng.integers(0, 20))
            if sub_len == 0:
                lists.append([])
            else:
                steps = rng.integers(1, 5, size=sub_len)
                sublist = (int(rng.integers(-500, 500)) + np.cumsum(steps)).tolist()
                lists.append(sublist)

    elif workload_type == "reverse_distributed":
        k = max(4, int(base_k * 0.6))
        description = f"逆序分布区间负载 ({k} 组子列表间呈大体逆序分布，考察跨区间归并)"
        for i in range(k):
            length = int(rng.integers(5, 40))
            base = (k - i) * 500
            steps = rng.integers(1, 5, size=length)
            sublist = (base + np.cumsum(steps)).tolist()
            lists.append(sublist)

    else:
        k = max(1, base_k)
        description = f"通用随机规模负载 (自适应生成，{k} 组列表)"
        for _ in range(k):
            length = int(rng.integers(5, max(6, max_len)))
            steps = rng.integers(1, 10, size=length)
            sublist = np.cumsum(steps).tolist()
            lists.append(sublist)

    return description, lists
