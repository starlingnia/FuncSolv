#pragma once

#include <charconv>
#include <span>
#include <string_view>
#include <system_error>
#include <vector>

namespace core::io {

/**
 * @brief 单一核心小功能：零拷贝行切片整数解析器
 * @param line 包含由空格分隔的一行文本视图
 * @param out_numbers 用于存储解析结果的目标向量
 * 
 * 遵循 GSL 规范：
 * - 使用 std::string_view 避免深拷贝
 * - 使用 std::from_chars 达到最高性能数字解析，彻底杜绝 std::istringstream 堆分配开销
 * - 采用 Guard Clauses 防卫式退出
 */
inline void parse_integers_from_line(std::string_view line, std::vector<int>& out_numbers) {
    out_numbers.clear();
    
    // 卫语句：空行直接返回
    if (line.empty()) {
        return;
    }

    const char* ptr = line.data();
    const char* const end = ptr + line.size();

    while (ptr < end) {
        // 快速跳过前置空白符
        while (ptr < end && (*ptr == ' ' || *ptr == '\t' || *ptr == '\r' || *ptr == '\n')) {
            ++ptr;
        }
        if (ptr >= end) {
            break;
        }

        int value = 0;
        const auto [next_ptr, ec] = std::from_chars(ptr, end, value);
        if (ec == std::errc{}) {
            out_numbers.push_back(value);
            ptr = next_ptr;
        } else {
            // 跳过无法解析的单个字符以恢复流状态
            ++ptr;
        }
    }
}

} // namespace core::io
