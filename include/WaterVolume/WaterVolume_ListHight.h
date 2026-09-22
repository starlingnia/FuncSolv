#pragma once

#include "WaterVolume/WaterVolume.h"

// 保持对原有 Solution 接口的完全兼容
class Solution {
public:
    [[nodiscard]] int trap(std::span<const int> height) const noexcept {
        watervolume::WaterVolumeCalculator calc;
        return calc.trap(height);
    }
};
