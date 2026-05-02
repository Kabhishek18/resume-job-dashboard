"""Shared helpers for HTTP clients that optionally use JOBSPY_PROXY."""


def looks_like_proxy_failure(exc: BaseException, proxy: str) -> bool:
    msg = str(exc).lower()
    proxy_l = proxy.lower()
    proxy_host = proxy_l.split("://", 1)[-1]
    proxy_markers = ("proxy", "127.0.0.1", "localhost")
    failure_markers = (
        "proxyerror",
        "proxy error",
        "cannot connect to proxy",
        "failed to establish a new connection",
        "max retries exceeded",
        "connection refused",
        "connection aborted",
        "connect timeout",
        "timed out",
        "name or service not known",
        "nodename nor servname provided",
    )
    mentions_proxy = any(marker in msg for marker in proxy_markers) or any(
        marker in proxy_host for marker in proxy_markers
    )
    return mentions_proxy and any(marker in msg for marker in failure_markers)
