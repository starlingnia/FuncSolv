#include "MergeSortedLists/MergeSortedLists.h"
#include <future>

std::shared_ptr<ListNode> MergeKSortedListsSolution::mergeTwoLists(
    std::shared_ptr<ListNode> left_list, 
    std::shared_ptr<ListNode> right_list
) const {
    // 卫语句：当左侧链表指针为空时直接返回右侧链表
    if (left_list == nullptr) {
        return right_list;
    }
    
    // 卫语句：当右侧链表指针为空时直接返回左侧链表
    if (right_list == nullptr) {
        return left_list;
    }

    auto dummy_root = std::make_shared<ListNode>(0);
    auto current_node = dummy_root;
    auto cursor_left = left_list;
    auto cursor_right = right_list;

    // 采用标准结构化条件处理链表节点归并
    while ((cursor_left != nullptr) && (cursor_right != nullptr)) {
        if (cursor_left->val < cursor_right->val) {
            current_node->next = cursor_left;
            cursor_left = cursor_left->next;
        } else {
            current_node->next = cursor_right;
            cursor_right = cursor_right->next;
        }
        current_node = current_node->next;
    }

    current_node->next = (cursor_left != nullptr) ? cursor_left : cursor_right;
    return dummy_root->next;
}

std::shared_ptr<ListNode> MergeKSortedListsSolution::mergeKLists(
    std::vector<std::shared_ptr<ListNode>>& lists
) const {
    // 卫语句：当输入列表为空时直接返回空指针
    if (lists.empty()) {
        return nullptr;
    }
    
    // 卫语句：当输入列表仅包含单个元素时直接返回该元素
    if (lists.size() == 1) {
        return lists[0];
    }

    // 计算分治中点
    size_t split_index = lists.size() / 2;

    // 利用标准库范围迭代器切分数据子集
    std::vector<std::shared_ptr<ListNode>> left_sublists(lists.begin(), lists.begin() + split_index);
    std::vector<std::shared_ptr<ListNode>> right_sublists(lists.begin() + split_index, lists.end());

    // 引入现代 C++ 并发编程：利用 std::async 在多线程中并行调度左右两侧的归并任务
    auto left_future = std::async(std::launch::async, [this, left_sublists]() mutable {
        auto mutable_lists = left_sublists;
        return this->mergeKLists(mutable_lists);
    });

    auto right_future = std::async(std::launch::async, [this, right_sublists]() mutable {
        auto mutable_lists = right_sublists;
        return this->mergeKLists(mutable_lists);
    });

    // 汇聚异步并发结果并执行最终的两路归并
    return mergeTwoLists(left_future.get(), right_future.get());
}
