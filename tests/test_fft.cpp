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

using namespace std;

int main() {
    constexpr size_t kN = 1024;
    constexpr size_t kExpectedBin = 32;

    vector<sdr::Complex> signal;
    signal.reserve(kN);
    for (size_t n = 0; n < kN; ++n) {
        double angle = 2.0 * M_PI * static_cast<double>(kExpectedBin) *
                       static_cast<double>(n) / static_cast<double>(kN);
        sdr::Complex sample;
        sample.re = static_cast<float>(cos(angle));
        sample.im = 0.0f;
        signal.push_back(sample);
    }

    vector<float> spectrum = sdr::MagnitudeSpectrum(signal);

    // Only the first half of the spectrum needs to be checked, since it
    // mirrors for a real-valued input.
    size_t peak_bin = 0;
    for (size_t i = 1; i < spectrum.size() / 2; ++i) {
        if (spectrum[i] > spectrum[peak_bin]) peak_bin = i;
    }

    printf("Expected peak near bin %zu, found peak at bin %zu\n", kExpectedBin,
           peak_bin);

    if (peak_bin == kExpectedBin) {
        printf("PASS\n");
        return 0;
    }
    printf("FAIL\n");
    return 1;
}
