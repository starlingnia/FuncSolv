#include "WaterVolume/WaterVolume.h"

import std;

extern "C" {

/**
 * @brief 单个地形数组的雨水计算 C 接口
 * @param heights 连续高度数组指针
 * @param length 数组长度
 * @param strategy 策略代码 (0: TwoPointer, 1: MonotonicStack)
 * @return 蓄水量结果
 */
int trap_water_c_api(const int* heights, int length, int strategy) {
    if (heights == nullptr || length <= 2) {
        return 0;
    }

    std::span<const int> height_span(heights, length);
    funcsolv::WaterVolumeCalculator calc;
    auto strat = (strategy == 1) 
        ? funcsolv::WaterVolumeCalculator::Strategy::MonotonicStack 
        : funcsolv::WaterVolumeCalculator::Strategy::TwoPointer;

    return calc.trap(height_span, strat);
}

/**
 * @brief 批量多地形数组并发雨水计算 C 接口
 * @param flat_heights 展平的高度数组
 * @param lengths 各个用例的长度数组
 * @param k 用例数量
 * @param strategy 策略代码 (0: TwoPointer, 1: MonotonicStack)
 * @param out_results 输出结果数组指针 (长度至少为 k)
 */
void batch_trap_water_c_api(
    const int* flat_heights,
    const int* lengths,
    int k,
    int strategy,
    int* out_results
) {
    if (flat_heights == nullptr || lengths == nullptr || k <= 0 || out_results == nullptr) {
        return;
    }

    funcsolv::WaterVolumeCalculator calc;
    auto strat = (strategy == 1) 
        ? funcsolv::WaterVolumeCalculator::Strategy::MonotonicStack 
        : funcsolv::WaterVolumeCalculator::Strategy::TwoPointer;

    std::vector<std::future<int>> futures;
    futures.reserve(k);

    const int* cur_pos = flat_heights;
    for (int i = 0; i < k; ++i) {
        const int len = lengths[i];
        std::span<const int> cur_span(cur_pos, len);
        cur_pos += len;

        futures.push_back(std::async(std::launch::async, [&calc, cur_span, strat]() {
            return calc.trap(cur_span, strat);
        }));
    }

    for (int i = 0; i < k; ++i) {
        out_results[i] = futures[i].get();
    }
}

}
