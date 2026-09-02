// dsp_pipeline.hpp
//
// Connects the simulator, queue, FFT, and metrics into one running pipeline.
// One thread (the producer) generates IQ samples and pushes them into a
// bounded queue. A second thread (the consumer) pops blocks from the queue,
// runs an FFT on each one, and records how long that took.
//
// Running the producer and consumer on separate threads means data can
// keep arriving even while a previous block is still being processed,
// which matches how a real radio feed behaves.

#pragma once

#include <atomic>
#include <chrono>
#include <complex>
#include <cstdio>
#include <fstream>
#include <string>
#include <thread>
#include <vector>

#include "bounded_queue.hpp"
#include "iq_simulator.hpp"
#include "metrics.hpp"
#include "simple_fft.hpp"

namespace sdr {

// One unit of work passed from the producer thread to the consumer thread.
struct IQBlock {
    std::vector<IQSample> samples;
    uint64_t block_number = 0;
};

class DspPipeline {
public:
    DspPipeline(double sample_rate_hz, double signal_freq_hz, std::size_t block_size,
                std::size_t queue_capacity)
        : simulator_(sample_rate_hz, signal_freq_hz, /*noise_amplitude=*/0.3f),
          block_size_(block_size),
          queue_(queue_capacity),
          // A real radio delivers samples continuously at a fixed rate,
          // rather than all at once. This pacing makes the simulated
          // producer behave the same way.
          block_period_(std::chrono::duration<double>(
              static_cast<double>(block_size) / sample_rate_hz)) {}

    // Runs the pipeline for num_blocks blocks, then prints a report.
    //
    // metrics_csv_path is optional. When set, every processed block's
    // measured latency is written as one row of a CSV file, so the results
    // can be analyzed or plotted afterward.
    void Run(std::size_t num_blocks, const std::string& metrics_csv_path = "") {
        if (!metrics_csv_path.empty()) {
            metrics_csv_.open(metrics_csv_path);
            metrics_csv_ << "block_number,latency_ms,peak_bin,peak_magnitude\n";
        }

        std::thread producer([this, num_blocks] { ProducerLoop(num_blocks); });
        std::thread consumer([this] { ConsumerLoop(); });

        producer.join();
        queue_.Shutdown();
        consumer.join();

        PrintReport();
    }

private:
    void ProducerLoop(std::size_t num_blocks) {
        for (uint64_t block_num = 0; block_num < num_blocks; ++block_num) {
            IQBlock block;
            block.block_number = block_num;
            block.samples = simulator_.NextBlock(block_size_);

            // Push() waits here if the queue is full, which slows the
            // producer down to match the consumer's speed.
            queue_.Push(std::move(block));

            std::this_thread::sleep_for(block_period_);
        }
    }

    void ConsumerLoop() {
        IQBlock block;
        while (queue_.Pop(&block)) {
            const TimePoint started_at = stopwatch_.Start();

            std::vector<Complex> complex_samples;
            complex_samples.reserve(block.samples.size());
            for (const IQSample& s : block.samples) {
                complex_samples.emplace_back(s.i, s.q);
            }

            std::vector<float> spectrum = MagnitudeSpectrum(std::move(complex_samples));

            std::size_t peak_index = 0;
            for (std::size_t i = 1; i < spectrum.size(); ++i) {
                if (spectrum[i] > spectrum[peak_index]) peak_index = i;
            }

            stopwatch_.Stop(started_at);
            delivery_.RecordDelivered();

            if (metrics_csv_.is_open()) {
                metrics_csv_ << block.block_number << ','
                             << stopwatch_.LastMs() << ',' << peak_index << ','
                             << spectrum[peak_index] << '\n';
            }

            if (block.block_number % 50 == 0) {
                std::printf("[block %6llu] strongest frequency bin = %zu, magnitude = %.2f\n",
                            static_cast<unsigned long long>(block.block_number), peak_index,
                            spectrum[peak_index]);
            }
        }
    }

    void PrintReport() const {
        std::printf("\nDSP Pipeline Report\n");
        std::printf("Blocks processed:     %zu\n", stopwatch_.Count());
        std::printf("Mean latency:         %.3f ms\n", stopwatch_.MeanMs());
        std::printf("p99 latency:          %.3f ms\n", stopwatch_.P99Ms());
        std::printf("Delivery rate:        %.4f%% (%llu delivered, %llu dropped)\n",
                     delivery_.DeliveryRatePercent(),
                     static_cast<unsigned long long>(delivery_.Delivered()),
                     static_cast<unsigned long long>(delivery_.Dropped()));
    }

    IQSimulator simulator_;
    std::size_t block_size_;
    BoundedQueue<IQBlock> queue_;
    std::chrono::duration<double> block_period_;

    LatencyStopwatch stopwatch_;
    DeliveryTracker delivery_;
    std::ofstream metrics_csv_;
};

}  // namespace sdr
