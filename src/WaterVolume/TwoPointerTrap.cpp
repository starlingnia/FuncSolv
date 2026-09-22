#include "WaterVolume/TwoPointerTrap.h"
#include <algorithm>

namespace watervolume {

int trap_two_pointer(std::span<const int> height) noexcept {
    if (height.size() <= 2) {
        return 0;
    }

    size_t left = 0;
    size_t right = height.size() - 1;
    int left_max = 0;
    int right_max = 0;
    int total_water = 0;

    while (left < right) {
        if (height[left] < height[right]) {
            if (height[left] >= left_max) {
                left_max = height[left];
            } else {
                total_water += left_max - height[left];
            }
            ++left;
        } else {
            if (height[right] >= right_max) {
                right_max = height[right];
            } else {
                total_water += right_max - height[right];
            }
            --right;
        }
    }

    return total_water;
}

} // namespace watervolume
