#include "MergeSortedLists/MergeSortedLists.h"
#include <vector>
#include <memory>

extern "C" {

// 接口函数：接收扁平化的数据与长度元数据，返回处理后的连续内存指针
int* merge_k_lists_c_api(const int* flat_data, const int* lengths, int k, int* out_size) {
    // 卫语句：当输入指针为空时直接返回空指针
    if ((flat_data == nullptr) || (lengths == nullptr) || (k <= 0)) {
        return nullptr;
    }

    std::vector<std::shared_ptr<ListNode>> lists;
    lists.reserve(k);

    const int* current_pos = flat_data;
    
    // 步骤一：在 C++ 堆内存中重建复杂数据结构（链表）
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

    // 步骤二：调用核心算法
    MergeKSortedListsSolution solution;
    auto merged_head = solution.mergeKLists(lists);

    // 步骤三：计算结果长度
    int total_len = 0;
    auto cursor = merged_head;
    while (cursor != nullptr) {
        ++total_len;
        cursor = cursor->next;
    }

    *out_size = total_len;
    
    // 卫语句：结果为空时直接返回
    if (total_len == 0) {
        return nullptr;
    }

    // 步骤四：将结果平铺到连续内存中，交由指针传递给 Python
    int* result_array = new int[total_len];
    cursor = merged_head;
    for (int i = 0; i < total_len; ++i) {
        result_array[i] = cursor->val;
        cursor = cursor->next;
    }

    return result_array;
}

// 配套的内存释放接口：闭环生命周期管理，防止内存泄漏
void free_merged_result(int* ptr) {
    // 卫语句：指针有效时执行安全的数组成员释放
    if (ptr != nullptr) {
        delete[] ptr;
    }
}

}
