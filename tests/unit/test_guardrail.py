"""Guardrail tests — verify banned methods raise immediately after install().

These tests use a mock class so the test suite doesn't require pywinauto
to be installed in the test environment.
"""

import pytest


def test_guardrail_raises_on_banned_method(monkeypatch):
    """After install(), any banned method raises RuntimeError."""
    # Build a minimal fake BaseWrapper so we can test the patching logic
    # without needing Windows + pywinauto installed.
    class FakeBaseWrapper:
        def click_input(self):
            pass

        def type_keys(self, keys):
            pass

    fake_module = type("pywinauto_module", (), {})()
    fake_bw_module = type("base_wrapper", (), {"BaseWrapper": FakeBaseWrapper})()

    import sys
    fake_pwa = type("pywinauto", (), {})()
    fake_pwa.base_wrapper = fake_bw_module
    monkeypatch.setitem(sys.modules, "pywinauto", fake_pwa)
    monkeypatch.setitem(sys.modules, "pywinauto.base_wrapper", fake_bw_module)

    from server import guardrail
    guardrail.install()

    obj = FakeBaseWrapper()
    with pytest.raises(RuntimeError, match="banned in background mode"):
        obj.click_input()
    with pytest.raises(RuntimeError, match="banned in background mode"):
        obj.type_keys("hello")


def test_guardrail_install_is_idempotent(monkeypatch):
    """Calling install() twice doesn't double-patch or raise."""
    class FakeBaseWrapper:
        def click_input(self):
            pass

    fake_bw_module = type("base_wrapper", (), {"BaseWrapper": FakeBaseWrapper})()
    import sys
    monkeypatch.setitem(sys.modules, "pywinauto", type("pwa", (), {"base_wrapper": fake_bw_module})())
    monkeypatch.setitem(sys.modules, "pywinauto.base_wrapper", fake_bw_module)

    from server import guardrail
    guardrail.install()
    guardrail.install()  # second call must not raise

    obj = FakeBaseWrapper()
    with pytest.raises(RuntimeError):
        obj.click_input()
