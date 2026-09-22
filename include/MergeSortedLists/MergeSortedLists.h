#pragma once

#include "MergeSortedLists/DivideAndConquerMerge.h"
#include "MergeSortedLists/HeapKWayMerge.h"
#include "MergeSortedLists/ListNode.h"
#include "MergeSortedLists/TwoWayMerge.h"

import std;

/**
 * @brief 多路归并方案核心类
 * 汇聚链表分治归并、连续数组最小堆归并及双路归并
 */
class MergeKSortedListsSolution {
public:
    // 链表多路归并接口
    [[nodiscard]] std::shared_ptr<ListNode> mergeKLists(
        std::vector<std::shared_ptr<ListNode>>& lists
    ) const;

    // 连续切片接口：基于最小堆的高性能流式归并 (零额外堆分配)
    [[nodiscard]] std::vector<int> mergeKSpans(
        std::span<const std::span<const int>> spans
    ) const;

    // 基础两路归并接口
    [[nodiscard]] std::shared_ptr<ListNode> mergeTwoLists(
        std::shared_ptr<ListNode> left,
        std::shared_ptr<ListNode> right
    ) const noexcept;
};

namespace funcsolv {
    using MergeKSortedListsSolution = ::MergeKSortedListsSolution;
    using ListNode = ::ListNode;
}
