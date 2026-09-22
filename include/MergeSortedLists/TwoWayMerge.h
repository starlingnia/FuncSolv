#pragma once

#include "MergeSortedLists/ListNode.h"
#include <memory>
#include <span>
#include <vector>

namespace msl {

/**
 * @brief 单一核心小功能：链表两路有序归并
 */
[[nodiscard]] std::shared_ptr<ListNode> merge_two_lists(
    std::shared_ptr<ListNode> left,
    std::shared_ptr<ListNode> right
) noexcept;

/**
 * @brief 单一核心小功能：连续切片（span）两路有序归并
 */
void merge_two_spans(
    std::span<const int> a,
    std::span<const int> b,
    std::vector<int>& out
);

} // namespace msl
