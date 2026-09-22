#include "WaterVolume/MonotonicStackTrap.h"
#include <algorithm>
#include <vector>

namespace watervolume {

int trap_monotonic_stack(std::span<const int> height) {
    if (height.size() <= 2) {
        return 0;
    }

    std::vector<size_t> stack;
    stack.reserve(height.size());

    int total_water = 0;

    for (size_t current = 0; current < height.size(); ++current) {
        while (!stack.empty() && height[current] > height[stack.back()]) {
            const size_t top = stack.back();
            stack.pop_back();

            if (stack.empty()) {
                break;
            }

            const size_t distance = current - stack.back() - 1;
            const int bounded_height = std::min(height[current], height[stack.back()]) - height[top];
            total_water += static_cast<int>(distance) * bounded_height;
        }
        stack.push_back(current);
    }

    return total_water;
}

} // namespace watervolume
