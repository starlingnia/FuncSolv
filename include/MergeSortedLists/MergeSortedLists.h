#pragma once

#include <memory>
#include <vector>

// 遵循 GSL 规范：利用 std 智能指针安全管理链表节点的生命周期
struct ListNode {
    int val{0};
    std::shared_ptr<ListNode> next{nullptr};
    
    explicit ListNode(int value) : val(value) {}
};

class MergeKSortedListsSolution {
public:
    // 对外暴露的高性能合并接口
    std::shared_ptr<ListNode> mergeKLists(std::vector<std::shared_ptr<ListNode>>& lists) const;

private:
    // 基础两路归并核心函数
    std::shared_ptr<ListNode> mergeTwoLists(
        std::shared_ptr<ListNode> left_list, 
        std::shared_ptr<ListNode> right_list
    ) const;
};
