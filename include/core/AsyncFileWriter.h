#pragma once

import std;

namespace core::io {

/**
 * @brief 单一核心小功能：基于后台专用线程与缓冲队列的非阻塞异步文件写出器
 * 
 * 优势与特性：
 * - 前台计算线程投递数据瞬间返回，彻底避免磁盘 I/O 带来的毫秒级停顿
 * - 遵循 RAII 原则，在析构时自动完成排空刷盘与后台线程汇合
 */
class AsyncFileWriter {
public:
    explicit AsyncFileWriter(const std::filesystem::path& file_path);
    ~AsyncFileWriter();

    // 禁用拷贝语义，强制使用移动语义防止多线程资源竞态
    AsyncFileWriter(const AsyncFileWriter&) = delete;
    AsyncFileWriter& operator=(const AsyncFileWriter&) = delete;

    AsyncFileWriter(AsyncFileWriter&&) noexcept;
    AsyncFileWriter& operator=(AsyncFileWriter&&) noexcept;

    /**
     * @brief 零阻塞写入单行数据
     * @param line 待写入的一行文本
     */
    void write_line(std::string line);

    /**
     * @brief 手动提前刷盘并关闭写出器
     */
    void close();

private:
    struct Impl;
    std::unique_ptr<Impl> p_impl_;
};

} // namespace core::io
