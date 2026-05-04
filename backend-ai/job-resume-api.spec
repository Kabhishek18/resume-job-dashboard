# -*- mode: python ; coding: utf-8 -*-
# Run from backend-ai/: pyinstaller job-resume-api.spec
# Output: dist/job-resume-api/

import os
import sys

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_submodules


def _resolve_root() -> str:
    sp = globals().get("SPECPATH") or globals().get("SPEC")
    if sp:
        path = os.path.abspath(os.path.expanduser(str(sp)))
        return path if os.path.isdir(path) else os.path.dirname(path)
    for _a in reversed(sys.argv):
        if isinstance(_a, str) and _a.endswith(".spec"):
            path = os.path.abspath(_a)
            return os.path.dirname(path)
    return os.getcwd()


ROOT = _resolve_root()

block_cipher = None


def tls_binaries_for_build():
    """Ship only the tls_client native lib for the OS/arch running PyInstaller."""
    import platform
    import sys

    import tls_client
    from pathlib import Path

    dep = Path(tls_client.__file__).resolve().parent / "dependencies"
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        name = "tls-client-arm64.dylib" if machine in ("arm64", "aarch64") else "tls-client-x86.dylib"
    elif sys.platform == "win32":
        name = "tls-client-64.dll"
    else:
        name = "tls-client-amd64.so"
    candidate = dep / name
    if not candidate.is_file():
        raise FileNotFoundError("tls_client dependency not found: {}".format(candidate))
    return [(str(candidate), "tls_client/dependencies")]


def datas():
    alembic_dir = os.path.join(ROOT, "alembic")
    alembic_ini = os.path.join(ROOT, "alembic.ini")
    out = [(alembic_dir, "alembic"), (alembic_ini, ".")]
    return out


# Uvicorn & ASGI stacks need explicit submodule hooks on some installs.
_HIDDEN = [
    "tls_client",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]
_HIDDEN += collect_submodules("app")
_HIDDEN += collect_submodules("alembic")

_TLS_BINARIES = tls_binaries_for_build()

a = Analysis(
    [os.path.join(ROOT, "desktop_run.py")],
    pathex=[ROOT],
    binaries=_TLS_BINARIES,
    datas=datas(),
    hiddenimports=_HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="job-resume-api",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_trace=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="job-resume-api",
)
