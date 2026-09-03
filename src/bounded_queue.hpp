// bounded_queue.hpp
//
// A thread-safe queue with a fixed maximum size. One thread (the producer)
// pushes blocks in, and another thread (the consumer) pops blocks out.
//
// If the queue is full, Push() waits until space is available instead of
// growing without limit. This is called backpressure: it keeps memory use
// bounded when the consumer is slower than the producer.
//
// This queue only ever needs to hold one kind of item, IQBlock, so it is
// written as a plain class instead of a template. A template would let one
// class definition work for many different item types, which is more
// machinery than this project needs.

#pragma once

#include <condition_variable>
#include <cstdint>
#include <deque>
#include <mutex>
#include <vector>

#include "iq_simulator.hpp"

using namespace std;

namespace sdr {

// One unit of work passed from the producer thread to the consumer thread.
struct IQBlock {
    vector<IQSample> samples;
    uint64_t block_number = 0;
};

class BoundedQueue {
public:
    explicit BoundedQueue(size_t capacity) : capacity_(capacity) {}

    // Adds a block to the queue. Waits here if the queue is already full.
    void Push(IQBlock item) {
        unique_lock<mutex> lock(mutex_);

        // Keep waiting while the queue is full and we have not been told to
        // shut down. wait() releases the lock while it waits, and re-checks
        // this condition each time it is woken up.
        while (items_.size() >= capacity_ && !shutdown_) {
            not_full_.wait(lock);
        }

        if (shutdown_) return;

        items_.push_back(item);
        not_empty_.notify_one();
    }

    // Removes and returns the next block. Returns false once the queue has
    // been shut down and is empty, meaning there is nothing left to process.
    bool Pop(IQBlock* out_item) {
        unique_lock<mutex> lock(mutex_);

        while (items_.empty() && !shutdown_) {
            not_empty_.wait(lock);
        }

        if (items_.empty()) {
            return false;
        }

        *out_item = items_.front();
        items_.pop_front();

        not_full_.notify_one();
        return true;
    }

    // Signals that no more items will be pushed. Wakes any waiting threads
    // so they can exit instead of waiting forever.
    void Shutdown() {
        {
            lock_guard<mutex> lock(mutex_);
            shutdown_ = true;
        }
        not_empty_.notify_all();
        not_full_.notify_all();
    }

    size_t Size() const {
        lock_guard<mutex> lock(mutex_);
        return items_.size();
    }

private:
    mutable mutex mutex_;
    condition_variable not_full_;
    condition_variable not_empty_;
    deque<IQBlock> items_;
    size_t capacity_;
    bool shutdown_ = false;
};

}  // namespace sdr
