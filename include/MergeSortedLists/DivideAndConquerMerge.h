#pragma once

#include "MergeSortedLists/ListNode.h"

import std;

namespace msl {

/**
 * @brief 单一核心小功能：带自适应阈值并发控制的链表分治归并
 */
[[nodiscard]] std::shared_ptr<ListNode> merge_k_lists_divide_conquer(
    std::span<std::shared_ptr<ListNode>> lists,
    std::size_t max_concurrency_depth = 3
);

} // namespace msl
