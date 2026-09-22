#include "FuncSolv/MergeSortedLists.h"
#include <memory>
#include <span>
#include <vector>

extern "C" {

/**
 * @brief 传统接口：接收扁平数据并转为链表后多路归并
 */
int* merge_k_lists_c_api(const int* flat_data, const int* lengths, int k, int* out_size) {
    if ((flat_data == nullptr) || (lengths == nullptr) || (k <= 0) || (out_size == nullptr)) {
        return nullptr;
    }

    std::vector<std::shared_ptr<ListNode>> lists;
    lists.reserve(k);

    const int* current_pos = flat_data;

    for (int i = 0; i < k; ++i) {
        int length = lengths[i];
        std::shared_ptr<ListNode> head = nullptr;
        std::shared_ptr<ListNode> tail = nullptr;

        for (int j = 0; j < length; ++j) {
            auto new_node = std::make_shared<ListNode>(*current_pos);
            ++current_pos;

            if (head == nullptr) {
                head = new_node;
                tail = head;
            } else {
                tail->next = new_node;
                tail = new_node;
            }
        }
        lists.push_back(head);
    }

    funcsolv::MergeKSortedListsSolution solution;
    auto merged_head = solution.mergeKLists(lists);

    int total_len = 0;
    auto cursor = merged_head;
    while (cursor != nullptr) {
        ++total_len;
        cursor = cursor->next;
    }

    *out_size = total_len;

    if (total_len == 0) {
        return nullptr;
    }

    int* result_array = new int[total_len];
    cursor = merged_head;
    for (int i = 0; i < total_len; ++i) {
        result_array[i] = cursor->val;
        cursor = cursor->next;
    }

    return result_array;
}

/**
 * @brief 高性能新接口：零链表堆分配，直接基于连续内存切片 (span) + 最小堆并发归并
 */
int* merge_k_spans_c_api(const int* flat_data, const int* lengths, int k, int* out_size) {
    if ((flat_data == nullptr) || (lengths == nullptr) || (k <= 0) || (out_size == nullptr)) {
        return nullptr;
    }

    std::vector<std::span<const int>> spans;
    spans.reserve(k);

    const int* current_pos = flat_data;
    for (int i = 0; i < k; ++i) {
        const int length = lengths[i];
        spans.emplace_back(current_pos, length);
        current_pos += length;
    }

    funcsolv::MergeKSortedListsSolution solution;
    std::vector<int> merged_vec = solution.mergeKSpans(spans);

    *out_size = static_cast<int>(merged_vec.size());
    if (merged_vec.empty()) {
        return nullptr;
    }

    int* result_array = new int[merged_vec.size()];
    std::copy(merged_vec.begin(), merged_vec.end(), result_array);

    return result_array;
}

/**
 * @brief 释放结果内存的统一接口
 */
void free_merged_result(int* ptr) {
    if (ptr != nullptr) {
        delete[] ptr;
    }
}

}
