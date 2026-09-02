// iq_recorder.hpp
//
// Saves a stream of IQ samples to a file, and reads them back later. This
// makes it possible to capture one specific run of data and replay the
// exact same input again, which is useful for repeatable testing.
//
// The file format is a flat sequence of 32-bit floats: I, Q, I, Q, and so on.

#pragma once

#include <fstream>
#include <string>
#include <vector>

#include "iq_simulator.hpp"

namespace sdr {

class IQRecorder {
public:
    explicit IQRecorder(const std::string& file_path)
        : out_(file_path, std::ios::binary) {}

    bool IsOpen() const { return out_.is_open(); }

    void WriteBlock(const std::vector<IQSample>& block) {
        for (const IQSample& s : block) {
            out_.write(reinterpret_cast<const char*>(&s.i), sizeof(float));
            out_.write(reinterpret_cast<const char*>(&s.q), sizeof(float));
        }
    }

private:
    std::ofstream out_;
};

class IQPlayer {
public:
    explicit IQPlayer(const std::string& file_path)
        : in_(file_path, std::ios::binary) {}

    bool IsOpen() const { return in_.is_open(); }

    // Reads up to block_size samples. Returns fewer samples once the file
    // is exhausted, and an empty result when there is nothing left to read.
    std::vector<IQSample> ReadBlock(std::size_t block_size) {
        std::vector<IQSample> block;
        block.reserve(block_size);

        for (std::size_t n = 0; n < block_size; ++n) {
            IQSample s;
            in_.read(reinterpret_cast<char*>(&s.i), sizeof(float));
            in_.read(reinterpret_cast<char*>(&s.q), sizeof(float));
            if (!in_) break;
            block.push_back(s);
        }
        return block;
    }

private:
    std::ifstream in_;
};

}  // namespace sdr
