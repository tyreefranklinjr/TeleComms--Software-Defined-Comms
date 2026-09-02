// simple_fft.hpp
//
// A basic FFT (Fast Fourier Transform) implementation. Given a block of
// samples over time, the FFT reports which frequencies are present in that
// block and how strong each one is.
//
// This is a standard radix-2 Cooley-Tukey FFT, written for clarity rather
// than maximum speed. It only works on blocks whose size is a power of two
// (256, 512, 1024, 4096, and so on). Production systems typically use a
// dedicated library such as FFTW instead of a hand-written FFT.

#pragma once

#include <cmath>
#include <complex>
#include <cstddef>
#include <vector>

namespace sdr {

using Complex = std::complex<float>;

// Runs an FFT on data in place. data.size() must be a power of two.
inline void SimpleFFT(std::vector<Complex>& data) {
    const std::size_t n = data.size();
    if (n <= 1) return;

    // Reorder the samples using bit-reversal, which the next step requires.
    for (std::size_t i = 1, j = 0; i < n; ++i) {
        std::size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) {
            j ^= bit;
        }
        j ^= bit;
        if (i < j) {
            std::swap(data[i], data[j]);
        }
    }

    // Combine samples in increasing group sizes: 2, then 4, then 8, and so
    // on until the group size equals the full block.
    for (std::size_t len = 2; len <= n; len <<= 1) {
        const float angle = -2.0f * static_cast<float>(M_PI) / static_cast<float>(len);
        const Complex w_len(std::cos(angle), std::sin(angle));

        for (std::size_t start = 0; start < n; start += len) {
            Complex w(1.0f, 0.0f);
            for (std::size_t k = 0; k < len / 2; ++k) {
                Complex even = data[start + k];
                Complex odd = data[start + k + len / 2] * w;

                data[start + k] = even + odd;
                data[start + k + len / 2] = even - odd;

                w *= w_len;
            }
        }
    }
}

// Runs an FFT on a block of IQ samples and returns the magnitude of each
// frequency bin, which is what gets plotted as a frequency spectrum.
inline std::vector<float> MagnitudeSpectrum(std::vector<Complex> block) {
    SimpleFFT(block);

    std::vector<float> magnitudes;
    magnitudes.reserve(block.size());
    for (const Complex& c : block) {
        magnitudes.push_back(std::abs(c));
    }
    return magnitudes;
}

}  // namespace sdr
