import std;

#include "core/AsyncFileWriter.h"

namespace core::io {

struct AsyncFileWriter::Impl {
    std::filesystem::path path;
    std::queue<std::string> buffer_queue;
    std::mutex queue_mutex;
    std::condition_variable cv;
    std::atomic<bool> is_running{true};
    std::thread worker_thread;

    explicit Impl(std::filesystem::path file_path)
        : path(std::move(file_path)) {
        if (path.has_parent_path()) {
            std::filesystem::create_directories(path.parent_path());
        }
        worker_thread = std::thread(&Impl::worker_loop, this);
    }

    ~Impl() {
        stop();
    }

    void push(std::string data) {
        {
            std::lock_guard<std::mutex> lock(queue_mutex);
            buffer_queue.push(std::move(data));
        }
        cv.notify_one();
    }

    void stop() {
        if (!is_running.load()) {
            return;
        }
        is_running.store(false);
        cv.notify_all();
        if (worker_thread.joinable()) {
            worker_thread.join();
        }
    }

    void worker_loop() {
        std::ofstream out_file(path, std::ios::out | std::ios::trunc);
        if (!out_file.is_open()) {
            return;
        }

        while (true) {
            std::unique_lock<std::mutex> lock(queue_mutex);
            cv.wait(lock, [this] {
                return !buffer_queue.empty() || !is_running.load();
            });

            // 批量清空队列（减少锁争用）
            std::queue<std::string> local_batch;
            local_batch.swap(buffer_queue);
            lock.unlock();

            while (!local_batch.empty()) {
                out_file << local_batch.front() << '\n';
                local_batch.pop();
            }

            if (!is_running.load()) {
                // 再次加锁检查是否还有剩余数据残留
                std::lock_guard<std::mutex> final_lock(queue_mutex);
                while (!buffer_queue.empty()) {
                    out_file << buffer_queue.front() << '\n';
                    buffer_queue.pop();
                }
                out_file.flush();
                break;
            }
        }
    }
};

AsyncFileWriter::AsyncFileWriter(const std::filesystem::path& file_path)
    : p_impl_(std::make_unique<Impl>(file_path)) {}

AsyncFileWriter::~AsyncFileWriter() = default;

AsyncFileWriter::AsyncFileWriter(AsyncFileWriter&&) noexcept = default;
AsyncFileWriter& AsyncFileWriter::operator=(AsyncFileWriter&&) noexcept = default;

void AsyncFileWriter::write_line(std::string line) {
    if (p_impl_) {
        p_impl_->push(std::move(line));
    }
}

void AsyncFileWriter::close() {
    if (p_impl_) {
        p_impl_->stop();
    }
}

} // namespace core::io
