#pragma once

import std;

namespace core::io {

/**
 * @brief 单一核心小功能：流式逐行读取文本文件
 * @param file_path 目标文本文件路径
 * @param line_consumer 针对每一行的无拷贝回调函数 (接收 std::string_view)
 * @return 是否成功打开并完成遍历
 */
[[nodiscard]] bool stream_read_lines(
    const std::filesystem::path& file_path,
    const std::function<void(std::string_view)>& line_consumer
);

/**
 * @brief 批量预解析测试用例数据
 * @param file_path 目标文本文件路径
 * @return 包含所有行拆分后的二维整型数组
 */
[[nodiscard]] std::vector<std::vector<int>> load_integer_dataset(
    const std::filesystem::path& file_path
);

} // namespace core::io
