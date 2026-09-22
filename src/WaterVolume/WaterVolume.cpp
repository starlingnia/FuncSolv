#include "WaterVolume/WaterVolume.h"

namespace watervolume {

int WaterVolumeCalculator::trap(
    std::span<const int> height, 
    Strategy strategy
) const noexcept {
    if (strategy == Strategy::MonotonicStack) {
        return watervolume::trap_monotonic_stack(height);
    }
    return watervolume::trap_two_pointer(height);
}

} // namespace watervolume
