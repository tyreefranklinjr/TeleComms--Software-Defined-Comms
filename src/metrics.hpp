// metrics.hpp
//
// Measures how long each block of data takes to process, and tracks how
// many blocks were delivered versus dropped. This is what produces the
// latency and delivery numbers reported at the end of a run.

#pragma once

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <vector>

namespace sdr {

using Clock = std::chrono::steady_clock;
using TimePoint = Clock::time_point;

class LatencyStopwatch {
public:
    // Call before processing a block.
    TimePoint Start() const { return Clock::now(); }

    // Call after processing a block. Records the elapsed time in milliseconds.
    void Stop(TimePoint started_at) {
        const auto finished_at = Clock::now();
        const double milliseconds =
            std::chrono::duration<double, std::milli>(finished_at - started_at).count();
        samples_ms_.push_back(milliseconds);
    }

    double MeanMs() const {
        if (samples_ms_.empty()) return 0.0;
        double sum = 0.0;
        for (double v : samples_ms_) sum += v;
        return sum / static_cast<double>(samples_ms_.size());
    }

    // p99 latency: 99% of measured blocks finished faster than this value.
    double P99Ms() const {
        if (samples_ms_.empty()) return 0.0;

        std::vector<double> sorted = samples_ms_;
        std::sort(sorted.begin(), sorted.end());

        std::size_t index = static_cast<std::size_t>(0.99 * (sorted.size() - 1));
        return sorted[index];
    }

    std::size_t Count() const { return samples_ms_.size(); }

    // The most recently recorded latency. Used when logging each
    // measurement individually, for example to a CSV file.
    double LastMs() const { return samples_ms_.empty() ? 0.0 : samples_ms_.back(); }

private:
    std::vector<double> samples_ms_;
};

// Tracks how many blocks were delivered versus dropped, so a delivery rate
// can be reported at the end of a run.
class DeliveryTracker {
public:
    void RecordDelivered() { ++delivered_; }
    void RecordDropped() { ++dropped_; }

    double DeliveryRatePercent() const {
        const uint64_t total = delivered_ + dropped_;
        if (total == 0) return 100.0;
        return 100.0 * static_cast<double>(delivered_) / static_cast<double>(total);
    }

    uint64_t Delivered() const { return delivered_; }
    uint64_t Dropped() const { return dropped_; }

private:
    uint64_t delivered_ = 0;
    uint64_t dropped_ = 0;
};

}  // namespace sdr
