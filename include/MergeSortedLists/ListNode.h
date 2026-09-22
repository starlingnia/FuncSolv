#pragma once

#include <memory>

/**
 * @brief 链表节点基础数据结构
 * 遵循 GSL 规范：利用 std::shared_ptr 安全管理链表节点的生命周期
 */
struct ListNode {
    int val{0};
    std::shared_ptr<ListNode> next{nullptr};

    explicit ListNode(int value) : val(value) {}
};
