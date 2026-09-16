let
  nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/archive/refs/heads/nixos-25.11.tar.gz";
  pkgs = import nixpkgs { config = {}; overlays = []; };
in
pkgs.mkShellNoCC {
  packages = with pkgs; [
    python314
    uv
    nodejs_24
    git
    docker_29
    docker-compose
  ];

  shellHook = ''
    echo "Hoard development: Docker Compose is the preferred full-stack environment."
    echo "Run: docker compose up --build"
    echo "This shell provides Python 3.14, uv, Node 24, Git, and Docker 29 tooling for host-side work."
  '';
}
