#include "core/FastFileReader.h"
#include "core/FastLineParser.h"

#include <fstream>
#include <string>

namespace core::io {

bool stream_read_lines(
    const std::filesystem::path& file_path,
    const std::function<void(std::string_view)>& line_consumer
) {
    // 卫语句：当路径不存在时直接返回失败
    if (!std::filesystem::exists(file_path)) {
        return false;
    }

    std::ifstream stream(file_path);
    if (!stream.is_open()) {
        return false;
    }

    std::string line_buffer;
    while (std::getline(stream, line_buffer)) {
        line_consumer(std::string_view(line_buffer));
    }

    return true;
}

std::vector<std::vector<int>> load_integer_dataset(
    const std::filesystem::path& file_path
) {
    std::vector<std::vector<int>> dataset;

    stream_read_lines(file_path, [&dataset](std::string_view line) {
        std::vector<int> numbers;
        parse_integers_from_line(line, numbers);
        if (!numbers.empty()) {
            dataset.push_back(std::move(numbers));
        }
    });

    return dataset;
}

} // namespace core::io
