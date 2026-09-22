#include "MergeSortedLists/MergeSortedLists.h"

std::shared_ptr<ListNode> MergeKSortedListsSolution::mergeKLists(
    std::vector<std::shared_ptr<ListNode>>& lists
) const {
    return msl::merge_k_lists_divide_conquer(lists);
}

std::vector<int> MergeKSortedListsSolution::mergeKSpans(
    std::span<const std::span<const int>> spans
) const {
    return msl::merge_k_spans_heap(spans);
}

std::shared_ptr<ListNode> MergeKSortedListsSolution::mergeTwoLists(
    std::shared_ptr<ListNode> left,
    std::shared_ptr<ListNode> right
) const noexcept {
    return msl::merge_two_lists(left, right);
}
