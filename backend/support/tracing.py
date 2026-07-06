"""Langfuse observability for the Support Escalation Claw.

Design principle (same as the rest of this project): observability must be
*optional* and must never break the workflow. If Langfuse is not installed
or not configured (no LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY), every helper
here degrades to a no-op and the support workflow runs exactly as before.

Usage in the orchestrator::

    from support import tracing

    with tracing.observation("run_support_workflow", as_type="agent",
                             input={"query": query}) as root:
        ...
        with tracing.observation("classify", input={"query": query}) as span:
            classification = classify_query(query)
            span.update(output=classification)
        ...
        root.update(output={"state": final_state})

The Langfuse v4 SDK (OpenTelemetry-based) is used. Spans opened via
``start_as_current_observation`` nest automatically by context, so the child
``observation(...)`` blocks below become children of the root workflow span.
"""
import os
from contextlib import contextmanager

# Resolved lazily on first use so importing this module is always safe.
_client = None
_initialised = False


class _NoopSpan:
    """Stand-in span used when tracing is disabled. All methods are no-ops."""

    def update(self, *args, **kwargs):
        return self

    def update_trace(self, *args, **kwargs):
        return self

    def end(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


_NOOP = _NoopSpan()


def _get_client():
    """Return a configured Langfuse client, or None if tracing is disabled.

    Enabled only when the langfuse package is importable AND both keys are
    present in the environment. Any failure to initialise disables tracing
    rather than raising.
    """
    global _client, _initialised
    if _initialised:
        return _client

    _initialised = True  # only attempt once

    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        _client = None
        return None

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except Exception:
        # Package missing, bad keys, network/OTel setup issue — never fatal.
        _client = None

    return _client


def is_enabled() -> bool:
    return _get_client() is not None


@contextmanager
def observation(name: str, as_type: str = "span", input=None, metadata=None):
    """Context manager yielding a Langfuse span (or a no-op span).

    ``as_type`` accepts the Langfuse observation types, e.g. "span",
    "agent", "chain", "retriever", "generation". Set the result on the span
    with ``span.update(output=...)`` inside the block.
    """
    client = _get_client()
    if client is None:
        yield _NOOP
        return

    try:
        with client.start_as_current_observation(
            name=name, as_type=as_type, input=input, metadata=metadata
        ) as span:
            yield span
    except Exception:
        # If anything in the tracing path fails, don't take the workflow down.
        yield _NOOP


def flush():
    """Flush buffered spans to Langfuse. Safe to call when disabled.

    Langfuse batches spans on a background thread; in short-lived request
    handlers it's worth flushing at the end of a run so traces appear
    promptly. No-op when tracing is disabled.
    """
    client = _get_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        pass
