"""
雨水容积高层任务编排控制器 (WaterVolumeOrchestrator)
------------------------------------------------------------
- 遵循 Pitchfork 规范：调度控制器位于 tools/ 目录下
- 配合 tools.io.AsyncFileWriter 异步写出器完成计算结果落盘，避免主线程阻塞
"""

from pathlib import Path
import sys
from typing import List, Optional

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.water_volume_interface import WaterVolumeInterface
from tools.io import AsyncFileWriter


class WaterVolumeOrchestrator:
    def __init__(self, library_path: Optional[str] = None) -> None:
        self.interface = WaterVolumeInterface(library_path)

    def calculate_and_save(
        self,
        terrains: List[List[int]],
        output_path: Path,
        strategy: str = "two_pointer"
    ) -> List[int]:
        """批量调度底层 C++ 并发计算，并使用 AsyncFileWriter 异步非阻塞落盘"""
        results = self.interface.batch_trap(terrains, strategy=strategy)

        with AsyncFileWriter(output_path) as writer:
            for i, (terrain, res) in enumerate(zip(terrains, results)):
                writer.write(f"Case {i + 1:04d} | Length: {len(terrain)} | Water Volume: {res}\n")

        return results


if __name__ == "__main__":
    orchestrator = WaterVolumeOrchestrator()
    sample_terrains = [
        [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1],
        [4, 2, 0, 3, 2, 5],
        [3, 0, 2, 0, 4],
    ]
    out_file = PROJECT_ROOT / "docs" / "result.txt"
    volumes = orchestrator.calculate_and_save(sample_terrains, out_file)
    print(f"Sample calculation complete: {volumes}")
    print(f"Results saved to: {out_file}")
