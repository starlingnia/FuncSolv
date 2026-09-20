#include <WaterVolume/WaterVolume_ListHight.h>
#include <algorithm>
#include <span>

namespace {

// 将分支逻辑封装为内部函数，避免外泄；参数使用引用保证零拷贝
// 遵循 GSL 规范：保留完整大括号，显式作用域
void process_water_step(auto& left_iter, auto& right_iter, TrappingState& state) noexcept {
    state.left_max = std::max(state.left_max, *left_iter);
    state.right_max = std::max(state.right_max, *right_iter);

    if (state.left_max < state.right_max) {
        state.total_water += state.left_max - *left_iter;
        ++left_iter;
    } else {
        state.total_water += state.right_max - *right_iter;
        --right_iter;
    }
}

} // namespace

int Solution::trap(std::span<const int> height) const noexcept {
    TrappingState state{};

    // 确保具备形成水槽的基本物理空间条件 (至少需要 3 个柱子)
    if (height.size() > 2) {
        auto left = height.begin();
        auto right = height.end() - 1;

        while (left <= right) {
            process_water_step(left, right, state);
        }
    }

    return state.total_water;
}
