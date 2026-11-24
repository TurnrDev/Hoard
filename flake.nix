{
  description = "Hoard application and frontend";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      ...
    }:
    let
      inherit (nixpkgs) lib;
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forSystems = lib.genAttrs systems;
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
      packageSets = forSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonSet =
            (pkgs.callPackage pyproject-nix.build.packages {
              python = pkgs.python314;
            }).overrideScope
              (
                lib.composeManyExtensions [
                  pyproject-build-systems.overlays.wheel
                  (workspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
                ]
              );
          pythonEnv = pythonSet.mkVirtualEnv "hoard-python-env" workspace.deps.default;
          application = pkgs.callPackage ./nix/package.nix { inherit pythonEnv; };
        in
        {
          default = application;
          hoard = application;
          frontend = application.frontend;
          python-env = pythonEnv;
        }
      );
    in
    {
      packages = packageSets;
      checks = forSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          app = packageSets.${system}.hoard;
        in
        {
          runtime = pkgs.runCommand "hoard-runtime-check" { } ''
            export HOARD_STATIC_ROOT=/tmp/hoard-static
            ${app}/bin/hoard-python - <<'PY'
            from pathlib import Path
            import celery
            import channels_redis
            import daphne
            import django
            import psycopg
            from hoard import settings
            assert settings.STATIC_ROOT == Path('/tmp/hoard-static')
            assert (settings.VITE_DIST_DIR / '.vite' / 'manifest.json').is_file()
            from asgiref.sync import async_to_sync
            from channels.testing import HttpCommunicator
            from hoard.staticfiles import serve_static_files
            async def fallback(scope, receive, send):
                await send({'type': 'http.response.start', 'status': 404, 'headers': []})
                await send({'type': 'http.response.body', 'body': b""})
            application = serve_static_files(fallback, settings.VITE_DIST_DIR)
            communicator = HttpCommunicator(application, 'GET', '/static/favicon.svg')
            communicator.scope["root_path"] = ""
            response = async_to_sync(communicator.get_response)()
            assert response['status'] == 200
            assert b'<svg' in response['body']
            PY
            touch "$out"
          '';
        }
      );
      devShells = forSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShellNoCC {
            packages = [
              pkgs.python314
              pkgs.uv
              pkgs.nodejs_24
            ];
          };
        }
      );
      formatter = forSystems (system: nixpkgs.legacyPackages.${system}.nixfmt);
    };
}
