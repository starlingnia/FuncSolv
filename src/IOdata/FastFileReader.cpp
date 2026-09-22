import std;

#include "core/FastFileReader.h"
#include "core/FastLineParser.h"

namespace core::io {

bool stream_read_lines(
    const std::filesystem::path& file_path,
    const std::function<void(std::string_view)>& line_consumer
) {
    // 卫语句：当路径不存在时直接返回失败
    if (!std::filesystem::exists(file_path)) {
        return false;
    }

    std::ifstream file_stream(file_path);
    if (!file_stream.is_open()) {
        return false;
    }

    std::string current_line;
    // 预分配缓冲区，减少行读取动态扩容开销
    current_line.reserve(512);

    while (std::getline(file_stream, current_line)) {
        // 空白行过滤
        if (current_line.empty()) {
            continue;
        }
        line_consumer(current_line);
    }

    return true;
}

std::vector<std::vector<int>> load_integer_dataset(
    const std::filesystem::path& file_path
) {
    std::vector<std::vector<int>> dataset;
    dataset.reserve(1024);

    const bool success = stream_read_lines(file_path, [&dataset](std::string_view line) {
        std::vector<int> numbers;
        if (parse_integers_from_line(line, numbers)) {
            dataset.push_back(std::move(numbers));
        }
    });

    if (!success) {
        return {};
    }

    return dataset;
}

} // namespace core::io
