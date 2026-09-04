// iq_simulator.hpp
//
// Generates simulated IQ samples in place of a real SDR (RTL-SDR) device.
// An IQ sample is a pair of numbers, I (in-phase) and Q (quadrature), that
// together represent one point of a radio signal at a moment in time.
//
// This class produces a sine wave plus random noise, at a chosen sample rate,
// so the rest of the pipeline can be developed and tested without hardware.
//
// Noise uses the plain rand() function instead of the <random> library's
// generator/distribution objects, since rand() is a single, well known
// function: it returns a random integer, and dividing that by RAND_MAX
// turns it into a fraction between 0.0 and 1.0.

#pragma once

#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <vector>

using namespace std;

namespace sdr {

// One IQ sample. "i" and "q" are the real and imaginary parts of the signal.
struct IQSample {
    float i = 0.0f;
    float q = 0.0f;
};

class IQSimulator {
public:
    // sample_rate_hz: samples produced per second
    // signal_freq_hz: frequency of the simulated signal
    // noise_amplitude: strength of the random noise added to the signal
    IQSimulator(double sample_rate_hz, double signal_freq_hz, float noise_amplitude)
        : sample_rate_hz_(sample_rate_hz),
          signal_freq_hz_(signal_freq_hz),
          noise_amplitude_(noise_amplitude) {}

    IQSample NextSample() {
        const double phase = 2.0 * M_PI * signal_freq_hz_ * time_seconds_;

        IQSample sample;
        sample.i = static_cast<float>(cos(phase)) + RandomNoise();
        sample.q = static_cast<float>(sin(phase)) + RandomNoise();

        time_seconds_ += 1.0 / sample_rate_hz_;
        ++samples_produced_;

        return sample;
    }

    // Returns a block of simulated IQ data to be read by the DSP pipeline
    vector<IQSample> NextBlock(size_t block_size) {
        vector<IQSample> block;
        block.reserve(block_size);
        
        for (size_t n = 0; n < block_size; n++) {block.push_back(NextSample());}
        return block;
    }

    uint64_t SamplesProduced() const { return samples_produced_; }

private:
    // Returns a random value within the range [-x, x] then scales to the amplitude

    // I do plan on using an additive white gaussian noise technique later..
    float RandomNoise() {
        float fraction = static_cast<float>(rand()) / static_cast<float>(RAND_MAX);
        return (fraction * 2.0f - 1.0f) * noise_amplitude_;
    }

    double sample_rate_hz_;
    double signal_freq_hz_;
    float noise_amplitude_;

    double time_seconds_ = 0.0;
    uint64_t samples_produced_ = 0;
};

}
