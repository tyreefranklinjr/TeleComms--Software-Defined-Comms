# CMakeLists.txt
#
# Build configuration for the C++ program. Produces two executables:
#   sdr_platform  the main program (src/main.cpp)
#   test_fft      the FFT correctness check (tests/test_fft.cpp)
#
# Usage:
#   mkdir build && cd build
#   cmake ..
#   cmake --build .

cmake_minimum_required(VERSION 3.16)

project(sdr_platform LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

add_executable(sdr_platform src/main.cpp)

find_package(Threads REQUIRED)
target_link_libraries(sdr_platform PRIVATE Threads::Threads)

add_executable(test_fft tests/test_fft.cpp)
target_link_libraries(test_fft PRIVATE Threads::Threads)

enable_testing()
add_test(NAME fft_sanity_check COMMAND test_fft)
