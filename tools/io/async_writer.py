"""
异步后台文件写入组件 (AsyncFileWriter)
------------------------------------------------------------
- 核心功能单一：负责将数据非阻塞投递至后台队列，由专用 I/O 线程完成批量磁盘落盘
- 杜绝主计算线程与工作线程因为磁盘 I/O 导致的等待阻塞
- 支持上下文管理器 (with 语法)，退出时自动等待数据刷新完毕并安全关闭
"""

import queue
import threading
from pathlib import Path
from typing import Optional, Union


class AsyncFileWriter:
    """
    非阻塞异步文件落盘器：
    主线程/计算线程通过 write() 瞬间返回，底层由后台守护线程批量写入磁盘。
    """

    def __init__(self, target_path: Union[str, Path], buffer_capacity: int = 50000) -> None:
        self._target_path = Path(target_path)
        self._queue: queue.Queue[Optional[str]] = queue.Queue(maxsize=buffer_capacity)
        self._closed = False
        self._worker_thread = threading.Thread(
            target=self._writer_loop, 
            name=f"AsyncWriter-{self._target_path.name}", 
            daemon=True
        )
        self._worker_thread.start()

    def _writer_loop(self) -> None:
        """后台专职写入线程循环"""
        self._target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._target_path, "w", encoding="utf-8") as file_handle:
            while True:
                item = self._queue.get()
                if item is None:
                    # 终止信号，排空剩余标记后安全退出
                    self._queue.task_done()
                    break
                file_handle.write(item)
                self._queue.task_done()

    def write(self, content: str) -> None:
        """
        非阻塞提交数据至写队列：
        当前线程无需等待磁盘物理写入完成即可立即继续下一步运算。
        """
        if self._closed:
            raise RuntimeError(f"Cannot write to a closed AsyncFileWriter: {self._target_path}")
        self._queue.put(content)

    def flush(self) -> None:
        """等待当前队列中排队的所有 I/O 任务全部落地"""
        self._queue.join()

    def close(self) -> None:
        """关闭写出器并等待后台线程安全结束"""
        if self._closed:
            return
        self._closed = True
        self._queue.put(None)
        self._worker_thread.join()

    def __enter__(self) -> "AsyncFileWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
