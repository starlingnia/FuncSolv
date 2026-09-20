#include <FuncSolv/Registry.h>
#include <WaterVolume/WaterVolume_ListHight.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <future>
#include <print>
#include <random>
#include <span>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

namespace {

// GSL 规范：小函数职责单一，[[nodiscard]] 强制调用方检查结果
[[nodiscard]] bool generate_random_test_file(
    const std::filesystem::path& file_path,
    const size_t case_count = 8) {

    std::ofstream out_file(file_path);
    if (!out_file.is_open()) {
        std::println(stderr, "错误: 无法创建测试文件: {}", file_path.string());
        return false;
    }

    std::random_device rd;
    std::mt19937_64 rng(rd());

    // 随机用例长度分布：包含边缘情况（0, 1, 2）以及一般地形情况（3 ~ 20）
    std::uniform_int_distribution<int> length_dist(0, 200);
    // 高度范围：0 到 10
    std::uniform_int_distribution<int> height_dist(0, 600);

    for (size_t i = 0; i < case_count; ++i) {
        const int length = length_dist(rng);
        for (int j = 0; j < length; ++j) {
            out_file << height_dist(rng);
            if (j + 1 < length) {
                out_file << ' ';
            }
        }
        out_file << '\n';
    }

    return true;
}

// GSL 规范：RAII 文件管理，安全解析文本数据
[[nodiscard]] std::vector<std::vector<int>> read_test_cases_from_file(
    const std::filesystem::path& file_path) {

    std::vector<std::vector<int>> test_cases;
    std::ifstream in_file(file_path);
    if (!in_file.is_open()) {
        std::println(stderr, "错误: 无法打开测试文件: {}", file_path.string());
        return test_cases;
    }

    std::string line;
    while (std::getline(in_file, line)) {
        std::vector<int> current_case;
        std::istringstream line_stream(line);
        int val = 0;
        while (line_stream >> val) {
            current_case.push_back(val);
        }
        test_cases.push_back(std::move(current_case));
    }

    return test_cases;
}

// 格式化输出数组视图辅助函数
void print_case_summary(size_t index, std::span<const int> case_span, int water_volume) {
    std::string terrain_str = "[";
    const size_t display_limit = 200;
    const size_t count = std::min(case_span.size(), display_limit);

    for (size_t i = 0; i < count; ++i) {
        terrain_str += std::to_string(case_span[i]);
        if (i + 1 < case_span.size()) {
            terrain_str += ", ";
        }
    }
    if (case_span.size() > display_limit) {
        terrain_str += "...";
    }
    terrain_str += "]";

    std::println("用例 {:02d} | 长度: {:2d} | 地形: {:<35} | 储水量: {}",
                 index + 1, case_span.size(), terrain_str, water_volume);
}

} // namespace

// 任务执行函数：遵循 TaskRegistry 的规范
int run_water_volume_task(std::span<const std::string_view> args) {
    const std::filesystem::path file_path = args.empty() ? "docs/random_terrain_cases.txt" : std::string(args[0]);
    const size_t case_count = 1000;

    std::println("=================================================");
    std::println("1. 正在生成随机地形测试用例文件 -> {}", file_path.string());
    if (!generate_random_test_file(file_path, case_count)) {
        return 1;
    }

    std::println("2. 正在从文本文件中读取测试用例...");
    const std::vector<std::vector<int>> test_cases = read_test_cases_from_file(file_path);
    if (test_cases.empty()) {
        std::println(stderr, "警告: 读取到的测试用例为空！");
        return 1;
    }
    std::println("   成功读取 {} 组测试用例", test_cases.size());

    std::println("3. 启动现代并发任务 (std::async) 计算储水量...");
    std::println("-------------------------------------------------");

    const Solution solution;
    // 异步任务句柄列表
    std::vector<std::future<int>> futures;
    futures.reserve(test_cases.size());

    // 采用只读 span 视图配合并发异步调度，保证无额外内存拷贝
    for (const auto& terrain : test_cases) {
        std::span<const int> current_span = terrain;
        futures.push_back(std::async(std::launch::async, [&solution, current_span]() {
            return solution.trap(current_span);
        }));
    }

    // 收集所有并发计算结果并格式化输出
    for (size_t i = 0; i < futures.size(); ++i) {
        const int result = futures[i].get();
        print_case_summary(i, test_cases[i], result);
    }

    std::println("=================================================");
    std::println("所有并发计算任务执行完毕！");

    return 0;
}

// 注册到任务中心
REGISTER_TASK("trap", run_water_volume_task, "Generate random test cases file, read and compute water volume concurrently");
