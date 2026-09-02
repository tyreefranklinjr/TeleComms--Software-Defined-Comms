// main.cpp
//
// Entry point for the program. Reads the command line and dispatches to one
// of three modes:
//
//   live    runs the simulated real-time pipeline (simulator, FFT, report).
//   record  saves simulated IQ samples to a file.
//   replay  reads a previously recorded file back through the pipeline.
//
// Usage:
//   ./sdr_platform live
//   ./sdr_platform live metrics.csv
//   ./sdr_platform record my_capture.iq
//   ./sdr_platform replay my_capture.iq

#include <cstdio>
#include <cstring>
#include <string>

#include "dsp_pipeline.hpp"
#include "iq_recorder.hpp"
#include "iq_simulator.hpp"
#include "metrics.hpp"
#include "simple_fft.hpp"

namespace {

constexpr double kSampleRateHz = 1'024'000.0;
constexpr double kSignalFreqHz = 5'000.0;
constexpr std::size_t kBlockSize = 4096;
constexpr std::size_t kQueueCapacity = 16;
constexpr std::size_t kNumBlocksLive = 1500;

void RunLiveMode(const std::string& metrics_csv_path) {
    std::printf("Running the simulated real-time SDR pipeline.\n");
    std::printf("Sample rate: %.0f Hz | Block size: %zu | Blocks to process: %zu\n\n",
                kSampleRateHz, kBlockSize, kNumBlocksLive);

    sdr::DspPipeline pipeline(kSampleRateHz, kSignalFreqHz, kBlockSize, kQueueCapacity);
    pipeline.Run(kNumBlocksLive, metrics_csv_path);
}

void RunRecordMode(const std::string& output_path) {
    std::printf("Recording simulated IQ samples to '%s'.\n", output_path.c_str());

    sdr::IQSimulator simulator(kSampleRateHz, kSignalFreqHz, /*noise_amplitude=*/0.3f);
    sdr::IQRecorder recorder(output_path);

    if (!recorder.IsOpen()) {
        std::printf("ERROR: could not open '%s' for writing.\n", output_path.c_str());
        return;
    }

    constexpr std::size_t kNumBlocksToRecord = 50;
    for (std::size_t b = 0; b < kNumBlocksToRecord; ++b) {
        auto block = simulator.NextBlock(kBlockSize);
        recorder.WriteBlock(block);
    }

    std::printf("Done. Recorded %zu blocks (%zu samples).\n", kNumBlocksToRecord,
                kNumBlocksToRecord * kBlockSize);
}

void RunReplayMode(const std::string& input_path) {
    std::printf("Replaying recorded IQ samples from '%s'.\n\n", input_path.c_str());

    sdr::IQPlayer player(input_path);
    if (!player.IsOpen()) {
        std::printf("ERROR: could not open '%s' for reading.\n", input_path.c_str());
        return;
    }

    sdr::LatencyStopwatch stopwatch;
    std::size_t block_number = 0;

    while (true) {
        auto samples = player.ReadBlock(kBlockSize);
        if (samples.empty()) break;

        const auto started_at = stopwatch.Start();

        std::vector<sdr::Complex> complex_samples;
        complex_samples.reserve(samples.size());
        for (const auto& s : samples) complex_samples.emplace_back(s.i, s.q);

        auto spectrum = sdr::MagnitudeSpectrum(std::move(complex_samples));

        std::size_t peak_index = 0;
        for (std::size_t i = 1; i < spectrum.size(); ++i) {
            if (spectrum[i] > spectrum[peak_index]) peak_index = i;
        }

        stopwatch.Stop(started_at);
        std::printf("[replayed block %3zu] strongest frequency bin = %zu\n", block_number,
                    peak_index);
        ++block_number;
    }

    std::printf("\nReplayed %zu blocks. Mean latency: %.3f ms | p99 latency: %.3f ms\n",
                block_number, stopwatch.MeanMs(), stopwatch.P99Ms());
}

void PrintUsage(const char* program_name) {
    std::printf("Usage:\n");
    std::printf("  %s live [metrics_output.csv]\n", program_name);
    std::printf("  %s record <output_file.iq>\n", program_name);
    std::printf("  %s replay <input_file.iq>\n", program_name);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        PrintUsage(argv[0]);
        return 1;
    }

    const std::string mode = argv[1];

    if (mode == "live") {
        const std::string metrics_csv_path = (argc >= 3) ? argv[2] : "";
        RunLiveMode(metrics_csv_path);
    } else if (mode == "record" && argc >= 3) {
        RunRecordMode(argv[2]);
    } else if (mode == "replay" && argc >= 3) {
        RunReplayMode(argv[2]);
    } else {
        PrintUsage(argv[0]);
        return 1;
    }

    return 0;
}
