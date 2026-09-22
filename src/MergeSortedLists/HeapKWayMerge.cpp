#include "MergeSortedLists/HeapKWayMerge.h"

import std;

namespace msl {

namespace {

struct Cursor {
    int value;
    std::size_t list_idx;
    std::size_t elem_idx;

    bool operator>(const Cursor& other) const noexcept {
        return value > other.value;
    }
};

} // namespace

std::vector<int> merge_k_spans_heap(
    std::span<const std::span<const int>> spans
) {
    if (spans.empty()) {
        return {};
    }

    if (spans.size() == 1) {
        return std::vector<int>(spans[0].begin(), spans[0].end());
    }

    std::size_t total_elements = 0;
    for (const auto& sp : spans) {
        total_elements += sp.size();
    }

    std::vector<int> result;
    result.reserve(total_elements);

    std::priority_queue<Cursor, std::vector<Cursor>, std::greater<Cursor>> min_heap;

    for (std::size_t i = 0; i < spans.size(); ++i) {
        if (!spans[i].empty()) {
            min_heap.push(Cursor{
                .value = spans[i][0],
                .list_idx = i,
                .elem_idx = 0
            });
        }
    }

    while (!min_heap.empty()) {
        Cursor top = min_heap.top();
        min_heap.pop();
        result.push_back(top.value);

        const std::size_t next_idx = top.elem_idx + 1;
        const auto& current_sublist = spans[top.list_idx];
        if (next_idx < current_sublist.size()) {
            min_heap.push(Cursor{
                .value = current_sublist[next_idx],
                .list_idx = top.list_idx,
                .elem_idx = next_idx
            });
        }
    }

    return result;
}

} // namespace msl
