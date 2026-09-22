#pragma once

import std;

namespace watervolume {

/**
 * @brief 单一核心小功能：基于单调递减栈横向切片的接雨水容积计算 (O(N) 空间)
 */
[[nodiscard]] int trap_monotonic_stack(std::span<const int> height);

} // namespace watervolume
