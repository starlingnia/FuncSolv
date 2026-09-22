#pragma once

#include <span>
#include <vector>

namespace msl {

/**
 * @brief 单一核心小功能：基于最小堆 (Priority Queue) 的多路有序数组高效归并
 */
[[nodiscard]] std::vector<int> merge_k_spans_heap(
    std::span<const std::span<const int>> spans
);

} // namespace msl
