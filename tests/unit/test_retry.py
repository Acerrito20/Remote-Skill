import pytest

from core.retry import with_retry


def test_succeeds_first_attempt():
    calls = []

    @with_retry
    def fn():
        calls.append(1)
        return "ok"

    assert fn() == "ok"
    assert len(calls) == 1


def test_retries_on_failure():
    calls = []

    @with_retry(max_attempts=3, base_delay=0)
    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("not ready")
        return "ok"

    assert fn() == "ok"
    assert len(calls) == 3


def test_raises_after_max_attempts():
    @with_retry(max_attempts=2, base_delay=0)
    def fn():
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError, match="always fails"):
        fn()


def test_only_retries_specified_exceptions():
    calls = []

    @with_retry(max_attempts=3, base_delay=0, exceptions=(ValueError,))
    def fn():
        calls.append(1)
        raise TypeError("unexpected — should not retry")

    with pytest.raises(TypeError):
        fn()
    assert len(calls) == 1


def test_decorator_with_args():
    @with_retry(max_attempts=2, base_delay=0)
    def fn(x, y=1):
        return x + y

    assert fn(2, y=3) == 5
