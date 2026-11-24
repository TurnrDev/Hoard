{
  lib,
  stdenvNoCC,
  buildNpmPackage,
  nodejs_24,
  makeWrapper,
  pythonEnv,
}:
let
  root = ../.;
  # Use an allowlist at the repository root so local .env files, database dumps
  # and deployment state cannot enter the application package or npm build.
  source = lib.cleanSourceWith {
    src = root;
    filter =
      path: type:
      let
        relative = lib.removePrefix "${toString root}/" (toString path);
        parts = lib.splitString "/" relative;
        name = builtins.baseNameOf path;
      in
      (builtins.elem (builtins.head parts) [
        "hoard"
        "manage.py"
        "pyproject.toml"
        "uv.lock"
        "README.md"
        "package.json"
        "package-lock.json"
        "index.html"
        "vite.config.ts"
        "tsconfig.json"
        "tsconfig.app.json"
        "tsconfig.node.json"
      ])
      && !(builtins.elem name [
        "__pycache__"
        "dist"
        "node_modules"
        ".cache"
      ])
      && !(lib.hasPrefix ".env" name)
      && !(lib.hasSuffix ".pyc" name)
      && !(lib.hasSuffix ".tsbuildinfo" name)
      && !(lib.hasInfix ".sqlite3" name);
  };
  version = (lib.importTOML (root + "/pyproject.toml")).project.version;
  frontend = buildNpmPackage {
    pname = "hoard-frontend";
    inherit version;
    src = source;
    nodejs = nodejs_24;
    npmDepsHash = "sha256-0nxgG8d2CBfknoVtxQA0i0NHpaSbUrnLl6H7Dbtwkn4=";
    installPhase = ''
      runHook preInstall
      mkdir -p "$out"
      cp -r hoard/dist/. "$out/"
      runHook postInstall
    '';
  };
in
stdenvNoCC.mkDerivation {
  pname = "hoard";
  inherit version;
  src = source;
  nativeBuildInputs = [ makeWrapper ];
  dontBuild = true;
  installPhase = ''
    runHook preInstall
    mkdir -p "$out/share/hoard" "$out/bin"
    cp -r hoard manage.py pyproject.toml "$out/share/hoard/"
    ln -s ${frontend} "$out/share/hoard/hoard/dist"
    makeWrapper ${pythonEnv}/bin/python "$out/bin/hoard-python" \
      --set PYTHONPATH "$out/share/hoard" \
      --set PYTHONDONTWRITEBYTECODE 1
    makeWrapper ${pythonEnv}/bin/python "$out/bin/hoard-manage" \
      --add-flags "$out/share/hoard/manage.py" \
      --set PYTHONPATH "$out/share/hoard" \
      --set PYTHONDONTWRITEBYTECODE 1
    makeWrapper ${pythonEnv}/bin/daphne "$out/bin/hoard-server" \
      --set PYTHONPATH "$out/share/hoard" \
      --set PYTHONDONTWRITEBYTECODE 1
    for command in worker beat; do
      makeWrapper ${pythonEnv}/bin/celery "$out/bin/hoard-$command" \
        --add-flags "-A hoard $command" \
        --set PYTHONPATH "$out/share/hoard" \
        --set PYTHONDONTWRITEBYTECODE 1
    done
    runHook postInstall
  '';
  passthru = { inherit frontend pythonEnv; };
  meta = {
    description = "D&D campaign companion";
    homepage = "https://github.com/TurnrDev/Hoard";
    platforms = lib.platforms.linux;
    mainProgram = "hoard-server";
  };
}
