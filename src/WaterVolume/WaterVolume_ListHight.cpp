#include "WaterVolume/WaterVolume_ListHight.h"

// 编译单元实现：保留符号导出
int trap_water_volume(std::span<const int> height) noexcept {
    Solution s;
    return s.trap(height);
}
