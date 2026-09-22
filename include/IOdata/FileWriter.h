#pragma once

import std;

namespace iodata {

// GSL 规范：[[nodiscard]] 强制调用方检查文件写入结果
[[nodiscard]] bool write_matrix_to_csv(
    const std::filesystem::path& file_path,
    std::span<const double> matrix,
    std::size_t rows,
    std::size_t cols,
    bool include_header = false,
    std::string_view header_str = "");

[[nodiscard]] bool write_pairs_to_csv(
    const std::filesystem::path& file_path,
    std::span<const double> col1,
    std::span<const double> col2,
    bool include_header = false,
    std::string_view header_str = "");

} // namespace iodata
