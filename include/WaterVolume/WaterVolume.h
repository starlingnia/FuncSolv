#pragma once

#include "WaterVolume/MonotonicStackTrap.h"
#include "WaterVolume/TwoPointerTrap.h"

#include <span>

namespace watervolume {

/**
 * @brief 雨水蓄水量计算器门面类
 * 提供双指针算法与单调栈算法两种实现策略
 */
class WaterVolumeCalculator {
public:
    enum class Strategy {
        TwoPointer,
        MonotonicStack
    };

    [[nodiscard]] int trap(
        std::span<const int> height, 
        Strategy strategy = Strategy::TwoPointer
    ) const noexcept;
};

} // namespace watervolume

namespace funcsolv {
    using WaterVolumeCalculator = ::watervolume::WaterVolumeCalculator;
}
