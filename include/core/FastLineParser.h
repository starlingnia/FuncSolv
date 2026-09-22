#pragma once

import std;

namespace core::io {

/**
 * @brief 单一核心小功能：零拷贝行切片整数解析器
 * @param line 包含由空格分隔的一行文本视图
 * @param out_numbers 用于存储解析结果的目标向量
 * 
 * 优势与特性：
 * - 纯 string_view 内存切片，无子字符串复制
 * - 基于 std::from_chars 的底层无异常高速字符转整数机制
 */
inline bool parse_integers_from_line(
    std::string_view line,
    std::vector<int>& out_numbers
) {
    out_numbers.clear();
    out_numbers.reserve(64);

    const char* ptr = line.data();
    const char* end = ptr + line.size();

    while (ptr < end) {
        // 跳过行首或数值间的空白分隔符
        while (ptr < end && *ptr == ' ') {
            ++ptr;
        }
        if (ptr == end) {
            break;
        }

        int val = 0;
        const auto [p, ec] = std::from_chars(ptr, end, val);
        if (ec != std::errc()) {
            return false;
        }

        out_numbers.push_back(val);
        ptr = p;
    }

    return true;
}

} // namespace core::io
