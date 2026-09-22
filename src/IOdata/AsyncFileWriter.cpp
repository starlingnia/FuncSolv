#include "core/AsyncFileWriter.h"

#include <condition_variable>
#include <fstream>
#include <mutex>
#include <queue>
#include <thread>
#include <utility>

namespace core::io {

struct AsyncFileWriter::Impl {
    std::filesystem::path path;
    std::queue<std::string> buffer_queue;
    std::mutex queue_mutex;
    std::condition_variable cv;
    std::condition_variable cv_flush;
    std::jthread worker;
    bool stop_requested{false};

    explicit Impl(std::filesystem::path file_path)
        : path(std::move(file_path)) {
        if (path.has_parent_path()) {
            std::filesystem::create_directories(path.parent_path());
        }
        worker = std::jthread([this](std::stop_token st) {
            this->worker_loop(st);
        });
    }

    void worker_loop(std::stop_token st) {
        std::ofstream out_stream(path);
        if (!out_stream.is_open()) {
            return;
        }

        while (true) {
            std::queue<std::string> local_batch;
            {
                std::unique_lock lock(queue_mutex);
                cv.wait(lock, [this, &st]() {
                    return !buffer_queue.empty() || stop_requested || st.stop_requested();
                });

                // 批处理换出，减少锁占用时间
                local_batch.swap(buffer_queue);
            }

            while (!local_batch.empty()) {
                out_stream << local_batch.front();
                local_batch.pop();
            }
            out_stream.flush();
            cv_flush.notify_all();

            if (buffer_queue.empty() && (stop_requested || st.stop_requested())) {
                break;
            }
        }
    }

    void enqueue(std::string content) {
        {
            std::lock_guard lock(queue_mutex);
            if (stop_requested) {
                return;
            }
            buffer_queue.push(std::move(content));
        }
        cv.notify_one();
    }

    void flush() {
        std::unique_lock lock(queue_mutex);
        cv_flush.wait(lock, [this]() {
            return buffer_queue.empty();
        });
    }

    void close() {
        {
            std::lock_guard lock(queue_mutex);
            if (stop_requested) {
                return;
            }
            stop_requested = true;
        }
        cv.notify_all();
        if (worker.joinable()) {
            worker.join();
        }
    }

    ~Impl() {
        close();
    }
};

AsyncFileWriter::AsyncFileWriter(const std::filesystem::path& file_path)
    : impl_(std::make_unique<Impl>(file_path)) {}

AsyncFileWriter::~AsyncFileWriter() = default;

AsyncFileWriter::AsyncFileWriter(AsyncFileWriter&&) noexcept = default;
AsyncFileWriter& AsyncFileWriter::operator=(AsyncFileWriter&&) noexcept = default;

void AsyncFileWriter::write(std::string chunk) {
    if (impl_) {
        impl_->enqueue(std::move(chunk));
    }
}

void AsyncFileWriter::write_line(std::string line) {
    if (impl_) {
        line.push_back('\n');
        impl_->enqueue(std::move(line));
    }
}

void AsyncFileWriter::flush() {
    if (impl_) {
        impl_->flush();
    }
}

void AsyncFileWriter::close() {
    if (impl_) {
        impl_->close();
    }
}

} // namespace core::io
