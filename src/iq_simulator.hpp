// iq_simulator.hpp
//
// Generates simulated IQ samples in place of a real SDR (RTL-SDR) device.
// An IQ sample is a pair of numbers, I (in-phase) and Q (quadrature), that
// together represent one point of a radio signal at a moment in time.
//
// This class produces a sine wave plus random noise, at a chosen sample rate,
// so the rest of the pipeline can be developed and tested without hardware.

#pragma once

#include <cmath>
#include <cstdint>
#include <random>
#include <vector>

namespace sdr {

// One IQ sample. "i" and "q" are the real and imaginary parts of the signal.
struct IQSample {
    float i = 0.0f;
    float q = 0.0f;
};

class IQSimulator {
public:
    // sample_rate_hz: samples produced per second.
    // signal_freq_hz: frequency of the simulated signal.
    // noise_amplitude: strength of the random noise added to the signal.
    IQSimulator(double sample_rate_hz, double signal_freq_hz, float noise_amplitude)
        : sample_rate_hz_(sample_rate_hz),
          signal_freq_hz_(signal_freq_hz),
          noise_amplitude_(noise_amplitude),
          rng_(std::random_device{}()),
          noise_dist_(-noise_amplitude, noise_amplitude) {}

    // Produces the next IQ sample and advances the internal clock.
    IQSample NextSample() {
        const double phase = 2.0 * M_PI * signal_freq_hz_ * time_seconds_;

        IQSample sample;
        sample.i = static_cast<float>(std::cos(phase)) + noise_dist_(rng_);
        sample.q = static_cast<float>(std::sin(phase)) + noise_dist_(rng_);

        time_seconds_ += 1.0 / sample_rate_hz_;
        ++samples_produced_;

        return sample;
    }

    // Produces a block of samples at once. The DSP pipeline processes data
    // in blocks rather than one sample at a time.
    std::vector<IQSample> NextBlock(std::size_t block_size) {
        std::vector<IQSample> block;
        block.reserve(block_size);
        for (std::size_t n = 0; n < block_size; ++n) {
            block.push_back(NextSample());
        }
        return block;
    }

    uint64_t SamplesProduced() const { return samples_produced_; }

private:
    double sample_rate_hz_;
    double signal_freq_hz_;
    float noise_amplitude_;

    double time_seconds_ = 0.0;
    uint64_t samples_produced_ = 0;

    std::mt19937 rng_;
    std::uniform_real_distribution<float> noise_dist_;
};

}  // namespace sdr
