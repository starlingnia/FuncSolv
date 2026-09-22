#include <FuncSolv/Registry.h>
#include <WaterVolume/WaterVolume.h>
#include <core/AsyncFileWriter.h>
#include <core/FastFileReader.h>
#include <core/FastLineParser.h>

import std;

namespace {

/**
 * @brief 解析项目 docs/ 目录的真实路径，杜绝在 bin/ 下污染生成 bin/docs/
 */
[[nodiscard]] std::filesystem::path resolve_project_docs_path(const std::string& filename) {
    if (std::filesystem::is_directory("docs")) {
        return std::filesystem::path("docs") / filename;
    }
    if (std::filesystem::is_directory("../docs")) {
        return std::filesystem::path("../docs") / filename;
    }
    return std::filesystem::path("docs") / filename;
}

/**
 * @brief 使用 AsyncFileWriter 异步非阻塞生成并持久化测试用例
 */
[[nodiscard]] bool generate_random_test_file_async(
    const std::filesystem::path& file_path,
    const std::size_t case_count = 1000) {

    core::io::AsyncFileWriter writer(file_path);

    std::random_device rd;
    std::mt19937_64 rng(rd());

    std::uniform_int_distribution<int> length_dist(0, 200);
    std::uniform_int_distribution<int> height_dist(0, 600);

    for (std::size_t i = 0; i < case_count; ++i) {
        const int length = length_dist(rng);
        std::string line;
        line.reserve(length * 5);

        for (int j = 0; j < length; ++j) {
            line += std::to_string(height_dist(rng));
            if (j + 1 < length) {
                line.push_back(' ');
            }
        }
        writer.write_line(std::move(line));
    }

    writer.close();
    return true;
}

/**
 * @brief 格式化输出数组视图辅助函数
 */
void print_case_summary(std::size_t index, std::span<const int> case_span, int water_volume) {
    std::string terrain_str = "[";
    const std::size_t display_limit = 15;
    const std::size_t count = std::min(case_span.size(), display_limit);

    for (std::size_t i = 0; i < count; ++i) {
        terrain_str += std::to_string(case_span[i]);
        if (i + 1 < case_span.size()) {
            terrain_str += ", ";
        }
    }
    if (case_span.size() > display_limit) {
        terrain_str += "...";
    }
    terrain_str += "]";

    std::println("用例 {:04d} | 长度: {:3d} | 地形: {:<40} | 储水量: {}",
                 index + 1, case_span.size(), terrain_str, water_volume);
}

} // namespace

int run_water_volume_task(std::span<const std::string_view> args) {
    const std::filesystem::path file_path = args.empty() 
        ? resolve_project_docs_path("random_terrain_cases.txt") 
        : std::filesystem::path(std::string(args[0]));
    const std::size_t case_count = 1000;

    std::println("=================================================");
    std::println("1. 正在通过 AsyncFileWriter 异步生成测试用例文件 -> {}", file_path.string());
    if (!generate_random_test_file_async(file_path, case_count)) {
        return 1;
    }

    std::println("2. 正在通过 FastFileReader 快速零拷贝解析测试用例...");
    const std::vector<std::vector<int>> test_cases = core::io::load_integer_dataset(file_path);
    if (test_cases.empty()) {
        std::println(std::cerr, "警告: 读取到的测试用例为空！");
        return 1;
    }
    std::println("   成功读取 {} 组测试用例", test_cases.size());

    std::println("3. 启动现代并发任务 (std::async) 计算储水量...");
    std::println("-------------------------------------------------");

    const watervolume::WaterVolumeCalculator solution;
    std::vector<std::future<int>> futures;
    futures.reserve(test_cases.size());

    for (const auto& terrain : test_cases) {
        std::span<const int> current_span = terrain;
        futures.push_back(std::async(std::launch::async, [&solution, current_span]() {
            return solution.trap(current_span);
        }));
    }

    const std::size_t display_count = std::min(test_cases.size(), std::size_t{10});
    for (std::size_t i = 0; i < test_cases.size(); ++i) {
        const int result = futures[i].get();
        if (i < display_count) {
            print_case_summary(i, test_cases[i], result);
        }
    }

    std::println("   ... 其余 {} 个用例全部计算完成", test_cases.size() - display_count);
    std::println("=================================================");
    std::println("所有并发计算任务执行完毕！");

    return 0;
}

REGISTER_TASK("trap", run_water_volume_task, "Generate random test cases file, read and compute water volume concurrently");
