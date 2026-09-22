#pragma once

#include <filesystem>
#include <memory>
#include <string>
#include <string_view>

namespace core::io {

/**
 * @brief 单一核心小功能：基于后台专用线程与缓冲队列的非阻塞异步文件写出器
 * 
 * 优势与特性：
 * - 前台计算线程投递数据瞬间返回，彻底避免磁盘 I/O 带来的毫秒级停顿
 * - 遵循 RAII 原则，在析构时自动完成排空刷盘与后台线程汇合
 * - 采用 PImpl 惯用法，保持头文件干净无重量级并发头依赖
 */
class AsyncFileWriter {
public:
    explicit AsyncFileWriter(const std::filesystem::path& file_path);
    ~AsyncFileWriter();

    // 禁用拷贝语义，避免资源与句柄竞态
    AsyncFileWriter(const AsyncFileWriter&) = delete;
    AsyncFileWriter& operator=(const AsyncFileWriter&) = delete;

    // 移动语义
    AsyncFileWriter(AsyncFileWriter&&) noexcept;
    AsyncFileWriter& operator=(AsyncFileWriter&&) noexcept;

    // 非阻塞异步写操作
    void write(std::string chunk);
    void write_line(std::string line);

    // 同步排空当前队列
    void flush();

    // 安全关闭
    void close();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace core::io
