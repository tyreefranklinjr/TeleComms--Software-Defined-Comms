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
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <string>

#include "dsp_pipeline.hpp"
#include "iq_recorder.hpp"
#include "iq_simulator.hpp"
#include "metrics.hpp"
#include "simple_fft.hpp"

using namespace std;

namespace {

constexpr double kSampleRateHz = 1'024'000.0;
constexpr double kSignalFreqHz = 5'000.0;
constexpr size_t kBlockSize = 4096;
constexpr size_t kQueueCapacity = 16;
constexpr size_t kNumBlocksLive = 1500;

void RunLiveMode(const string& metrics_csv_path) {
    printf("Running the simulated real-time SDR pipeline.\n");
    printf("Sample rate: %.0f Hz | Block size: %zu | Blocks to process: %zu\n\n",
           kSampleRateHz, kBlockSize, kNumBlocksLive);

    sdr::DspPipeline pipeline(kSampleRateHz, kSignalFreqHz, kBlockSize, kQueueCapacity);
    pipeline.Run(kNumBlocksLive, metrics_csv_path);
}

void RunRecordMode(const string& output_path) {
    printf("Recording simulated IQ samples to '%s'.\n", output_path.c_str());

    sdr::IQSimulator simulator(kSampleRateHz, kSignalFreqHz, /*noise_amplitude=*/0.3f);
    sdr::IQRecorder recorder(output_path);

    if (!recorder.IsOpen()) {
        printf("ERROR: could not open '%s' for writing.\n", output_path.c_str());
        return;
    }

    constexpr size_t kNumBlocksToRecord = 50;
    for (size_t b = 0; b < kNumBlocksToRecord; ++b) {
        vector<sdr::IQSample> block = simulator.NextBlock(kBlockSize);
        recorder.WriteBlock(block);
    }

    printf("Done. Recorded %zu blocks (%zu samples).\n", kNumBlocksToRecord,
           kNumBlocksToRecord * kBlockSize);
}

void RunReplayMode(const string& input_path) {
    printf("Replaying recorded IQ samples from '%s'.\n\n", input_path.c_str());

    sdr::IQPlayer player(input_path);
    if (!player.IsOpen()) {
        printf("ERROR: could not open '%s' for reading.\n", input_path.c_str());
        return;
    }

    sdr::LatencyStopwatch stopwatch;
    size_t block_number = 0;

    while (true) {
        vector<sdr::IQSample> samples = player.ReadBlock(kBlockSize);
        if (samples.empty()) break;

        const sdr::TimePoint started_at = stopwatch.Start();

        vector<sdr::Complex> complex_samples;
        complex_samples.reserve(samples.size());
        for (size_t i = 0; i < samples.size(); ++i) {
            sdr::Complex sample;
            sample.re = samples[i].i;
            sample.im = samples[i].q;
            complex_samples.push_back(sample);
        }

        vector<float> spectrum = sdr::MagnitudeSpectrum(complex_samples);

        size_t peak_index = 0;
        for (size_t i = 1; i < spectrum.size(); ++i) {
            if (spectrum[i] > spectrum[peak_index]) peak_index = i;
        }

        stopwatch.Stop(started_at);
        printf("[replayed block %3zu] strongest frequency bin = %zu\n", block_number,
               peak_index);
        ++block_number;
    }

    printf("\nReplayed %zu blocks. Mean latency: %.3f ms | p99 latency: %.3f ms\n",
           block_number, stopwatch.MeanMs(), stopwatch.P99Ms());
}

void PrintUsage(const char* program_name) {
    printf("Usage:\n");
    printf("  %s live [metrics_output.csv]\n", program_name);
    printf("  %s record <output_file.iq>\n", program_name);
    printf("  %s replay <input_file.iq>\n", program_name);
}

}  // namespace

int main(int argc, char** argv) {
    // Seeds the random number generator used for simulated noise, so each
    // run of the program produces different (but still realistic) noise.
    srand(static_cast<unsigned int>(time(nullptr)));

    if (argc < 2) {
        PrintUsage(argv[0]);
        return 1;
    }

    const string mode = argv[1];

    if (mode == "live") {
        const string metrics_csv_path = (argc >= 3) ? argv[2] : "";
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
