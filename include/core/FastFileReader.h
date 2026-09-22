#pragma once

#include <filesystem>
#include <functional>
#include <string_view>
#include <vector>

namespace core::io {

/**
 * @brief 单一核心小功能：流式逐行读取文本文件
 * @param file_path 目标文本文件路径
 * @param line_consumer 针对每一行的无拷贝回调函数 (接收 std::string_view)
 * @return 是否成功打开并完成遍历
 */
bool stream_read_lines(
    const std::filesystem::path& file_path,
    const std::function<void(std::string_view)>& line_consumer
);

/**
 * @brief 单一核心小功能：将由空格隔开的数字文本文件加载为二维整数集合
 * @param file_path 目标文本文件路径
 * @return 解析得到的二维整数向量
 */
[[nodiscard]] std::vector<std::vector<int>> load_integer_dataset(
    const std::filesystem::path& file_path
);

} // namespace core::io
