let
  nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/archive/refs/heads/nixos-25.11.tar.gz";
  pkgs = import nixpkgs { config = {}; overlays = []; };
in
pkgs.mkShellNoCC {
  packages = with pkgs; [
    python314
    uv
    nodejs_22
    git
    docker-compose
  ];
}
