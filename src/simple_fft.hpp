/*simple_fft.hpp

A basic FFT (Fast Fourier Transform) implementation. Given a block of
samples over time, the FFT reports which frequencies are present in that
block and how strong each one is.

This is a standard radix-2 Cooley-Tukey FFT, written for clarity rather
than maximum speed. It only works on blocks whose size is a power of two
(256, 512, 1024, 4096, and so on). Production systems typically use a
dedicated library such as FFTW instead of a hand-written FFT.

A complex number is written here as a plain struct with a real part and
an imaginary part, and plain functions (ComplexAdd, ComplexMultiply, and
so on) do the math. This avoids operator overloading, which lets you
write "a + b" for custom types but hides a function call behind that
symbol. Calling ComplexAdd(a, b) makes the same operation visible.
*/

#pragma once

#include <cmath>
#include <cstddef>
#include <vector>

using namespace std;

namespace sdr {

// A complex number: real part "re" and imaginary part "im".
struct Complex {
    float re = 0.0f;
    float im = 0.0f;
};

inline Complex ComplexAdd(Complex a, Complex b) {
    Complex result;
    result.re = a.re + b.re;
    result.im = a.im + b.im;
    return result;
}

inline Complex ComplexSubtract(Complex a, Complex b) {
    Complex result;
    result.re = a.re - b.re;
    result.im = a.im - b.im;
    return result;
}

inline Complex ComplexMultiply(Complex a, Complex b) {
    Complex result;
    result.re = a.re * b.re - a.im * b.im;
    result.im = a.re * b.im + a.im * b.re;
    return result;
}

// The magnitude (length) of a complex number, which is what a frequency
// spectrum plots: how strong a frequency is, regardless of its phase.
inline float ComplexMagnitude(Complex a) {
    return sqrt(a.re * a.re + a.im * a.im);
}

// Runs an FFT on data in place. data.size() must be a power of two.
inline void SimpleFFT(vector<Complex>& data) {
    const size_t n = data.size();
    if (n <= 1) return;

    // Reorder the samples using bit-reversal, which the next step requires.
    for (size_t i = 1, j = 0; i < n; ++i) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) {
            j ^= bit;
        }
        j ^= bit;
        if (i < j) {
            Complex temp = data[i];
            data[i] = data[j];
            data[j] = temp;
        }
    }

    // Combine samples in increasing group sizes: 2, then 4, then 8, and so
    // on until the group size equals the full block.
    for (size_t len = 2; len <= n; len <<= 1) {
        const float angle = -2.0f * static_cast<float>(M_PI) / static_cast<float>(len);
        Complex w_len;
        w_len.re = cos(angle);
        w_len.im = sin(angle);

        for (size_t start = 0; start < n; start += len) {
            Complex w;
            w.re = 1.0f;
            w.im = 0.0f;

            for (size_t k = 0; k < len / 2; ++k) {
                Complex even = data[start + k];
                Complex odd = ComplexMultiply(data[start + k + len / 2], w);

                data[start + k] = ComplexAdd(even, odd);
                data[start + k + len / 2] = ComplexSubtract(even, odd);

                w = ComplexMultiply(w, w_len);
            }
        }
    }
}

// Runs an FFT on a block of IQ samples and returns the magnitude of each
// frequency bin, which is what gets plotted as a frequency spectrum.
inline vector<float> MagnitudeSpectrum(vector<Complex> block) {
    SimpleFFT(block);

    vector<float> magnitudes;
    magnitudes.reserve(block.size());
    for (size_t i = 0; i < block.size(); ++i) {
        magnitudes.push_back(ComplexMagnitude(block[i]));
    }
    return magnitudes;
}

}  // namespace sdr
