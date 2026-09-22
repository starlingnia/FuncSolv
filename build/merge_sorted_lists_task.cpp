#include <FuncSolv/Registry.h>
#include <MergeSortedLists/MergeSortedLists.h>
#include <core/AsyncFileWriter.h>
#include <core/FastFileReader.h>

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <print>
#include <random>
#include <span>
#include <string>
#include <string_view>
#include <vector>

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
 * @brief 生成随机多路有序测试数据集
 */
[[nodiscard]] std::vector<std::vector<int>> generate_test_cases(size_t k = 200, size_t max_len = 100) {
    std::random_device rd;
    std::mt19937_64 rng(rd());
    std::uniform_int_distribution<size_t> len_dist(10, max_len);
    std::uniform_int_distribution<int> step_dist(1, 10);

    std::vector<std::vector<int>> lists;
    lists.reserve(k);

    for (size_t i = 0; i < k; ++i) {
        const size_t len = len_dist(rng);
        std::vector<int> sublist;
        sublist.reserve(len);

        int current = 0;
        for (size_t j = 0; j < len; ++j) {
            current += step_dist(rng);
            sublist.push_back(current);
        }
        lists.push_back(std::move(sublist));
    }
    return lists;
}

} // namespace

int run_merge_sorted_lists_task(std::span<const std::string_view> args) {
    const std::filesystem::path before_file = args.empty() 
        ? resolve_project_docs_path("savedata_before.txt") 
        : std::filesystem::path(std::string(args[0]));
    const std::filesystem::path after_file = resolve_project_docs_path("savedata_after.txt");

    std::println("=================================================");
    std::println("1. 正在准备多路有序列表数据集...");
    std::vector<std::vector<int>> lists;

    if (std::filesystem::exists(before_file)) {
        std::println("   从现有文件快速零拷贝加载: {}", before_file.string());
        lists = core::io::load_integer_dataset(before_file);
    }
    if (lists.empty()) {
        std::println("   未检测到有效数据，自适应生成 500 组大规模测试用例...");
        lists = generate_test_cases(500, 150);

        core::io::AsyncFileWriter writer(before_file);
        for (const auto& sublist : lists) {
            std::string line;
            for (size_t i = 0; i < sublist.size(); ++i) {
                line += std::to_string(sublist[i]);
                if (i + 1 < sublist.size()) line.push_back(' ');
            }
            writer.write_line(std::move(line));
        }
        writer.close();
    }

    size_t total_items = 0;
    std::vector<std::span<const int>> spans;
    spans.reserve(lists.size());
    for (const auto& lst : lists) {
        total_items += lst.size();
        spans.emplace_back(lst);
    }

    std::println("   包含 {} 组列表，待归并元素总规模: {} 个", lists.size(), total_items);

    std::println("2. 调用底层核心高性能最小堆流式归并 (mergeKSpans)...");
    const auto start_time = std::chrono::high_resolution_clock::now();

    MergeKSortedListsSolution solution;
    std::vector<int> merged = solution.mergeKSpans(spans);

    const auto end_time = std::chrono::high_resolution_clock::now();
    const double duration = std::chrono::duration<double>(end_time - start_time).count();

    std::println("   归并计算耗时: {:.6f} 秒 | 吞吐率: {:.0f} items/sec",
                 duration, total_items / (duration > 0 ? duration : 1e-9));

    std::println("3. 严格执行数学单调性校验与守恒校验...");
    const bool length_ok = (merged.size() == total_items);
    const bool sorted_ok = std::is_sorted(merged.begin(), merged.end());

    if (length_ok && sorted_ok) {
        std::println("   ✓ 校验通过: 数量守恒且严格单调递增！");
    } else {
        std::println(stderr, "   ❌ 校验失败: length_ok={}, sorted_ok={}", length_ok, sorted_ok);
        return 1;
    }

    std::println("4. 通过 AsyncFileWriter 异步非阻塞持久化最终有序结果 -> {}", after_file.string());
    core::io::AsyncFileWriter writer(after_file);
    std::string out_line;
    out_line.reserve(merged.size() * 6);
    for (size_t i = 0; i < merged.size(); ++i) {
        out_line += std::to_string(merged[i]);
        if (i + 1 < merged.size()) out_line.push_back(' ');
    }
    writer.write_line(std::move(out_line));
    writer.close();

    std::println("=================================================");
    std::println("多路有序列表归并任务全部完成！");
    return 0;
}

REGISTER_TASK("merge", run_merge_sorted_lists_task, "High-performance multi-way sorted list merge with async IO");
