#include "MergeSortedLists/TwoWayMerge.h"

namespace msl {

std::shared_ptr<ListNode> merge_two_lists(
    std::shared_ptr<ListNode> left,
    std::shared_ptr<ListNode> right
) noexcept {
    // 卫语句：单侧为空时直接返回对侧
    if (left == nullptr) {
        return right;
    }
    if (right == nullptr) {
        return left;
    }

    auto dummy = std::make_shared<ListNode>(0);
    auto current = dummy;
    auto cur_left = left;
    auto cur_right = right;

    while (cur_left != nullptr && cur_right != nullptr) {
        if (cur_left->val <= cur_right->val) {
            current->next = cur_left;
            cur_left = cur_left->next;
        } else {
            current->next = cur_right;
            cur_right = cur_right->next;
        }
        current = current->next;
    }

    current->next = (cur_left != nullptr) ? cur_left : cur_right;
    return dummy->next;
}

void merge_two_spans(
    std::span<const int> a,
    std::span<const int> b,
    std::vector<int>& out
) {
    out.clear();
    out.reserve(a.size() + b.size());

    std::size_t i = 0;
    std::size_t j = 0;

    while (i < a.size() && j < b.size()) {
        if (a[i] <= b[j]) {
            out.push_back(a[i]);
            ++i;
        } else {
            out.push_back(b[j]);
            ++j;
        }
    }

    while (i < a.size()) {
        out.push_back(a[i]);
        ++i;
    }
    while (j < b.size()) {
        out.push_back(b[j]);
        ++j;
    }
}

} // namespace msl
