# Dockerfile
#
# Builds a self-contained Linux image with everything needed to compile and
# run this project, so the build behaves the same on any machine.
#
# Usage:
#   docker build -t sdr_platform .
#   docker run --rm sdr_platform live

FROM debian:bookworm-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /project
COPY . .

RUN mkdir -p build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release && cmake --build .

RUN cd rust_supervisor && cargo build --release

# Final image: only the compiled binaries are copied in, keeping the image
# smaller than the build stage above.
FROM debian:bookworm-slim

# The rust_supervisor binary looks for the C++ program at a relative path,
# "../build/sdr_platform", so this layout and working directory match that.
WORKDIR /project
COPY --from=build /project/build/sdr_platform ./build/sdr_platform
COPY --from=build /project/rust_supervisor/target/release/sdr_supervisor ./rust_supervisor/sdr_supervisor
WORKDIR /project/rust_supervisor

ENTRYPOINT ["./sdr_supervisor"]
CMD ["live"]
