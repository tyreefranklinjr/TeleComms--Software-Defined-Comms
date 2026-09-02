// bounded_queue.hpp
//
// A thread-safe queue with a fixed maximum size. One thread (the producer)
// pushes items in, and another thread (the consumer) pops items out.
//
// If the queue is full, Push() waits until space is available instead of
// growing without limit. This is called backpressure: it keeps memory use
// bounded when the consumer is slower than the producer.

#pragma once

#include <condition_variable>
#include <deque>
#include <mutex>

namespace sdr {

template <typename T>
class BoundedQueue {
public:
    explicit BoundedQueue(std::size_t capacity) : capacity_(capacity) {}

    void Push(T item) {
        std::unique_lock<std::mutex> lock(mutex_);

        not_full_.wait(lock, [this] { return items_.size() < capacity_ || shutdown_; });
        if (shutdown_) return;

        items_.push_back(std::move(item));
        not_empty_.notify_one();
    }

    // Removes and returns the next item. Returns false once the queue has
    // been shut down and is empty, meaning there is nothing left to process.
    bool Pop(T* out_item) {
        std::unique_lock<std::mutex> lock(mutex_);

        not_empty_.wait(lock, [this] { return !items_.empty() || shutdown_; });
        if (items_.empty()) {return false;}
        *out_item = std::move(items_.front());
        items_.pop_front();

        not_full_.notify_one();
        return true;
    }

    // Signals that no more items will be pushed. Wakes any waiting threads
    // so they can exit instead of waiting forever.
    void Shutdown() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            shutdown_ = true;
        }
        not_empty_.notify_all();
        not_full_.notify_all();
    }

    std::size_t Size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return items_.size();
    }

private:
    mutable std::mutex mutex_;
    std::condition_variable not_full_;
    std::condition_variable not_empty_;
    std::deque<T> items_;
    std::size_t capacity_;
    bool shutdown_ = false;
};

}
