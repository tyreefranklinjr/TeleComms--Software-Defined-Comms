#pragma once
#include <bits/stdc++.h>
#include <cstdlib>
#include <iostream>
#include <cmath>
using namespace std;

struct IQSample {
    double i = 0.0f;
    double q = 0.0f;
};

class IQSim {
    public:
        IQSim(double sample_freq, double sample_rate, float noise_amplitude)
            : sample_freq_(sample_freq), sample_rate_(sample_rate), noise_amplitude_(noise_amplitude) {}

        IQSample NextSample() {
            const double phase = 2.0 * M_PI * sample_freq_ * time_sec_;
            time_sec_ += 1.0 / sample_rate_;
            samples_produced_++;
            return IQSample {cos(phase) + RandNoise(), sin(phase) + RandNoise()};
        };
        
        vector<IQSample> NextBlock(size_t block_size) {
            vector<IQSample> block;
            block.reserve(block_size);
            for (size_t n = 0; n < block_size; n++) {block.push_back(NextSample());}
            return block;
        }
        
    private:
        float RandNoise() {
            float frac = static_cast<float>(rand()) / static_cast<float>(RAND_MAX);
            return (frac * 2.0f - 1.0f) * noise_amplitude_;
        }
        
        double sample_freq_;
        double sample_rate_;
        float noise_amplitude_;
        double time_sec_ = 0.0;
        int samples_produced_ = 0;
};
