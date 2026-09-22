#include "MergeSortedLists/DivideAndConquerMerge.h"
#include "MergeSortedLists/TwoWayMerge.h"

import std;

namespace msl {

namespace {

std::shared_ptr<ListNode> internal_divide_conquer(
    std::span<std::shared_ptr<ListNode>> lists,
    std::size_t depth
) {
    if (lists.empty()) {
        return nullptr;
    }
    if (lists.size() == 1) {
        return lists[0];
    }
    if (lists.size() == 2) {
        return merge_two_lists(lists[0], lists[1]);
    }

    const std::size_t mid = lists.size() / 2;
    auto left_span = lists.subspan(0, mid);
    auto right_span = lists.subspan(mid);

    if (depth > 0) {
        auto left_future = std::async(std::launch::async, [left_span, depth]() {
            return internal_divide_conquer(left_span, depth - 1);
        });

        auto right_res = internal_divide_conquer(right_span, depth - 1);
        auto left_res = left_future.get();

        return merge_two_lists(left_res, right_res);
    }

    auto left_res = internal_divide_conquer(left_span, 0);
    auto right_res = internal_divide_conquer(right_span, 0);
    return merge_two_lists(left_res, right_res);
}

} // namespace

std::shared_ptr<ListNode> merge_k_lists_divide_conquer(
    std::span<std::shared_ptr<ListNode>> lists,
    std::size_t max_concurrency_depth
) {
    return internal_divide_conquer(lists, max_concurrency_depth);
}

} // namespace msl
