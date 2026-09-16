"""Invoke the official RPGScript system builder distributed by Blastervla."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


def configured_compiler() -> Path:
    """Return the configured or platform-appropriate RPGScript compiler."""
    configured = os.environ.get("RPG_COMPANION_COMPILER", "").strip()
    if configured:
        compiler = Path(configured).expanduser()
        if compiler.is_file():
            return compiler
        raise ValidationError(
            "RPG_COMPANION_COMPILER does not point to a compiler executable."
        )

    architecture = platform.machine().lower()
    if platform.system() == "Linux" and architecture in {"amd64", "x86_64"}:
        compiler = (
            Path(settings.BASE_DIR)
            / "hoard"
            / "compendium"
            / "native"
            / "tools"
            / "linux-x64"
            / "refresh_system_builder"
        )
        if compiler.is_file():
            return compiler

    raise ValidationError(
        "No RPGScript compiler is available for "
        f"{platform.system()} {platform.machine()}. Install the official RPGScript "
        "VS Code extension and set RPG_COMPANION_COMPILER to its "
        "refresh_system_builder executable."
    )


def compile_native_systems(source: Path, output: Path) -> None:
    """Compile one RPG Companion development `systems` directory."""
    compiler = configured_compiler()
    command = [
        str(compiler),
        f"--base={source}",
        f"--output={output}",
        "--clean",
        "--structured-diagnostics",
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValidationError("The RPGScript compiler could not be executed.") from error

    if result.returncode == 0:
        return

    diagnostic = compiler_diagnostic(result.stdout, result.stderr)
    raise ValidationError(f"RPGScript compilation failed: {diagnostic}")


def compiler_diagnostic(stdout: str, stderr: str) -> str:
    """Extract a bounded, useful compiler failure for command feedback."""
    lines = [line.strip() for line in (*stderr.splitlines(), *stdout.splitlines())]
    meaningful = [line for line in lines if line]
    if not meaningful:
        return "the compiler did not provide a diagnostic"
    return " ".join(meaningful[-5:])[:2000]
