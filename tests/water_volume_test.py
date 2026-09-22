"""
WaterVolume 算法与高层编排器自动化测试脚本
------------------------------------------------------------
- 校验 C++ 底层双指针算法 (TwoPointer) 与单调栈算法 (MonotonicStack) 的计算全等性
- 验证空数组、单柱、平原、极值山谷等边界情况的正确性
- 测试通过 WaterVolumeOrchestrator 并发异步批量计算与落盘
"""

from pathlib import Path
import sys
import unittest

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

for p in (str(PROJECT_ROOT), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from tools.water_volume_interface import WaterVolumeInterface
from tools.water_volume_orchestrator import WaterVolumeOrchestrator


class TestWaterVolumeComponent(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.interface = WaterVolumeInterface()
        cls.orchestrator = WaterVolumeOrchestrator()

    def test_standard_cases(self) -> None:
        """标准接雨水经典用例验证"""
        case1 = [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]
        self.assertEqual(self.interface.trap(case1, "two_pointer"), 6)
        self.assertEqual(self.interface.trap(case1, "monotonic_stack"), 6)

        case2 = [4, 2, 0, 3, 2, 5]
        self.assertEqual(self.interface.trap(case2, "two_pointer"), 9)
        self.assertEqual(self.interface.trap(case2, "monotonic_stack"), 9)

    def test_edge_cases(self) -> None:
        """极端边界用例验证（空、单元素、两元素、单调递增、单调递减、平原）"""
        self.assertEqual(self.interface.trap([], "two_pointer"), 0)
        self.assertEqual(self.interface.trap([5], "two_pointer"), 0)
        self.assertEqual(self.interface.trap([5, 5], "two_pointer"), 0)
        self.assertEqual(self.interface.trap([1, 2, 3, 4, 5], "two_pointer"), 0)
        self.assertEqual(self.interface.trap([5, 4, 3, 2, 1], "two_pointer"), 0)
        self.assertEqual(self.interface.trap([3, 3, 3, 3], "two_pointer"), 0)

    def test_algorithm_equivalence_random_cases(self) -> None:
        """大规模随机测试下双指针与单调栈双算法严格等价性检验"""
        import numpy as np
        rng = np.random.default_rng(seed=42)

        batch_cases = []
        for _ in range(50):
            length = int(rng.integers(10, 100))
            terrain = rng.integers(0, 50, size=length).tolist()
            batch_cases.append(terrain)

        results_two_pointer = self.interface.batch_trap(batch_cases, strategy="two_pointer")
        results_stack = self.interface.batch_trap(batch_cases, strategy="monotonic_stack")

        self.assertEqual(len(results_two_pointer), len(batch_cases))
        self.assertEqual(results_two_pointer, results_stack)

    def test_orchestrator_async_save(self) -> None:
        """测试 WaterVolumeOrchestrator 批量调度与异步持久化"""
        terrains = [
            [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1],
            [4, 2, 0, 3, 2, 5],
            [3, 0, 2, 0, 4],
        ]
        out_file = PROJECT_ROOT / "docs" / "result.txt"
        volumes = self.orchestrator.calculate_and_save(terrains, out_file)
        self.assertEqual(volumes, [6, 9, 7])
        self.assertTrue(out_file.exists())


if __name__ == "__main__":
    unittest.main()
