// test_fft.cpp
//
// AI-assisted (Claude): this test was developed with AI assistance.
//
// A small correctness check for the FFT implementation. Builds a pure sine
// wave at a known frequency, runs the FFT on it, and checks that the peak
// shows up in the expected frequency bin. Prints PASS or FAIL.

#include <cmath>
#include <cstdio>
#include <vector>

#include "../src/simple_fft.hpp"

int main() {
    constexpr std::size_t kN = 1024;
    constexpr std::size_t kExpectedBin = 32;

    std::vector<sdr::Complex> signal;
    signal.reserve(kN);
    for (std::size_t n = 0; n < kN; ++n) {
        double angle = 2.0 * M_PI * static_cast<double>(kExpectedBin) *
                       static_cast<double>(n) / static_cast<double>(kN);
        signal.emplace_back(static_cast<float>(std::cos(angle)), 0.0f);
    }

    std::vector<float> spectrum = sdr::MagnitudeSpectrum(signal);

    // Only the first half of the spectrum needs to be checked, since it
    // mirrors for a real-valued input.
    std::size_t peak_bin = 0;
    for (std::size_t i = 1; i < spectrum.size() / 2; ++i) {
        if (spectrum[i] > spectrum[peak_bin]) peak_bin = i;
    }

    std::printf("Expected peak near bin %zu, found peak at bin %zu\n", kExpectedBin,
                peak_bin);

    if (peak_bin == kExpectedBin) {
        std::printf("PASS\n");
        return 0;
    }
    std::printf("FAIL\n");
    return 1;
}
