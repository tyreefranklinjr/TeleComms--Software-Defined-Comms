/*iq_recorder.hpp

Saves a stream of IQ samples to a file, and reads them back later. This
makes it possible to capture one specific run of data and replay the
exact same input again, which is useful for repeatable testing.

The file format is a flat sequence of 32-bit floats: I, Q, I, Q, and so on.

This uses the plain C file functions (fopen, fwrite, fread, fclose)
instead of C++ file streams. They map directly to "open a file, write
some bytes, close the file," with no cast needed to write a float's raw
bytes.*/

    
#pragma once

#include <cstdio>
#include <string>
#include <vector>

#include "iq_simulator.hpp"

using namespace std;

namespace sdr {

class IQRecorder {
public:
    explicit IQRecorder(const string& file_path) {
        file_ = fopen(file_path.c_str(), "wb");
    }

    ~IQRecorder() {
        if (file_ != nullptr) {
            fclose(file_);
        }
    }

    bool IsOpen() const { return file_ != nullptr; }

    void WriteBlock(const vector<IQSample>& block) {
        for (size_t i = 0; i < block.size(); ++i) {
            fwrite(&block[i].i, sizeof(float), 1, file_);
            fwrite(&block[i].q, sizeof(float), 1, file_);
        }
    }

private:
    FILE* file_ = nullptr;
};

class IQPlayer {
public:
    explicit IQPlayer(const string& file_path) {
        file_ = fopen(file_path.c_str(), "rb");
    }

    ~IQPlayer() {
        if (file_ != nullptr) {fclose(file_);}
    }

    bool IsOpen() const { return file_ != nullptr; }

    // Reads up to block_size samples. Returns fewer samples once the file
    // is exhausted, and an empty result when there is nothing left to read.
    vector<IQSample> ReadBlock(size_t block_size) {
        vector<IQSample> block;
        block.reserve(block_size);

        for (size_t n = 0; n < block_size; ++n) {
            IQSample s;
            size_t read_i = fread(&s.i, sizeof(float), 1, file_);
            size_t read_q = fread(&s.q, sizeof(float), 1, file_);
            if (read_i != 1 || read_q != 1) break;
            block.push_back(s);
        }
        return block;
    }

private:
    FILE* file_ = nullptr;
};

}  // namespace sdr
