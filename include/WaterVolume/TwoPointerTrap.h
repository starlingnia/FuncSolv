#pragma once

#include <span>

namespace watervolume {

/**
 * @brief 单一核心小功能：基于双指针双向夹逼扫描的接雨水容积计算 (O(1) 空间)
 */
[[nodiscard]] int trap_two_pointer(std::span<const int> height) noexcept;

} // namespace watervolume
