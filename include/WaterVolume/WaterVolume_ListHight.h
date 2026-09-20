#pragma once

#include <span>
#include <cstddef>

// 状态结构体：封装双指针扫描时的局部状态
struct TrappingState {
    int total_water{0};
    int left_max{0};
    int right_max{0};
};

class Solution {
public:
    // GSL规范：使用 std::span 传递只读连续数组视图，标记 [[nodiscard]] 与 const
    [[nodiscard]] int trap(std::span<const int> height) const noexcept;
};
