"""
PyInstaller entry: run FastAPI via uvicorn without --reload (desktop / production local).
"""
from __future__ import annotations

import multiprocessing


def _patch_tls_client_dylib_aliases() -> None:
    """Frozen app: tls shim depends on @rpath/tls-client-darwin-*; add a same-dir symlink PyInstaller omits."""
    import platform
    import sys
    from pathlib import Path

    if not getattr(sys, "frozen", False) or sys.platform != "darwin":
        return
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return
    deps = Path(base) / "tls_client" / "dependencies"
    mach = platform.machine().lower()
    if mach in ("arm64", "aarch64"):
        src_name, alias = "tls-client-arm64.dylib", "tls-client-darwin-arm64-v1.7.2.dylib"
    elif "x86" in mach or mach == "amd64":
        src_name, alias = "tls-client-x86.dylib", "tls-client-darwin-amd64-v1.7.2.dylib"
    else:
        return
    src = deps / src_name
    tgt = deps / alias
    try:
        if src.is_file() and not tgt.exists():
            tgt.symlink_to(src.name)
    except OSError:
        pass


def main() -> None:
    import os

    _patch_tls_client_dylib_aliases()

    import uvicorn

    import app.main  # noqa: F401 — ensure PyInstaller collects the `app` package (string import is not traced).

    host = os.environ.get("UVICORN_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    log_level = os.environ.get("LOG_LEVEL", "info").lower()
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,
        factory=False,
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
