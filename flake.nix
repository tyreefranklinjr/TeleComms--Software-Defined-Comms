# flake.nix
#
# An alternative to the Dockerfile using the Nix package manager. Anyone
# with Nix and flakes enabled can get a matching development environment
# with one command:
#
#   nix develop
#
# This is optional. If Nix is not installed, use the CMake, Cargo, and pip
# instructions in the README instead.
{
  description = "Real-Time Software-Defined Communications and RF Processing Platform";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = [
          pkgs.cmake
          pkgs.gcc
          pkgs.ninja

          pkgs.cargo
          pkgs.rustc

          (pkgs.python3.withPackages (ps: [ ps.numpy ps.matplotlib ]))
        ];

        shellHook = ''
          echo "SDR platform dev shell ready."
          echo "Build the C++ program with:   mkdir -p build && cd build && cmake .. -G Ninja && cmake --build ."
          echo "Build the Rust supervisor with: cd rust_supervisor && cargo build"
        '';
      };
    };
}
