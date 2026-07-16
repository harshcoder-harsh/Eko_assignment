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
from contextlib import contextmanager, ExitStack

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
            # Fail fast if Langfuse cloud is slow/unreachable. Without this,
            # a blocking API call (trace.list / observations.get_many) can hang
            # a request indefinitely and exhaust the server's threadpool.
            timeout=int(os.getenv("LANGFUSE_TIMEOUT", "8")),
        )
    except Exception:
        # Package missing, bad keys, network/OTel setup issue — never fatal.
        _client = None

    return _client


def is_enabled() -> bool:
    return _get_client() is not None


def get_client():
    """Public accessor for the shared Langfuse client (or None if disabled).

    Used by the observability API routes to *read* traces back out of
    Langfuse. Returns the same lazily-initialised client used for writing.
    """
    return _get_client()


@contextmanager
def observation(name: str, as_type: str = "span", input=None, metadata=None,
                 user_id: str | None = None, tags: list[str] | None = None):
    """Context manager yielding a Langfuse span (or a no-op span).

    ``as_type`` accepts the Langfuse observation types, e.g. "span",
    "agent", "chain", "retriever", "generation". Set the result on the span
    with ``span.update(output=...)`` inside the block.

    Pass ``user_id``/``tags`` on the *root* observation of a trace (the one
    opened with as_type="agent") to stamp trace-level identity used for
    tenant isolation. These use Langfuse's ``propagate_attributes`` context
    manager under the hood — the SDK has no ``update_trace`` method on the
    span object itself (there was previously a bug here that called one).
    ``propagate_attributes`` must be entered *before* the observation is
    created so the attributes land on the trace and propagate to children.
    """
    client = _get_client()
    if client is None:
        yield _NOOP
        return

    # Only the setup (opening the propagation context / starting the
    # observation) is guarded — if either fails we fall back to a no-op
    # span. Once we have a real span, exceptions raised by the caller's own
    # code inside the `with` block must propagate normally, not be
    # swallowed here. (Catching Exception around the yield and yielding
    # again in the except branch is illegal generator/contextmanager
    # behaviour and raises "generator didn't stop after throw()".)
    stack = ExitStack()
    try:
        if user_id is not None or tags is not None:
            from langfuse import propagate_attributes
            stack.enter_context(propagate_attributes(user_id=user_id, tags=tags))
        span = stack.enter_context(
            client.start_as_current_observation(
                name=name, as_type=as_type, input=input, metadata=metadata
            )
        )
    except Exception:
        stack.close()
        yield _NOOP
        return

    try:
        yield span
    finally:
        stack.close()


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