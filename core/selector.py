"""Selector language parser and resolver.

Grammar:
    selector := step ( '>' step )*
    step     := type '[' attr ( ',' attr )* ']'
    type     := identifier
    attr     := key op value
    op       := '=' | '~=' | '*='
    key      := identifier
    value    := quoted-string | identifier

Example:
    "Window[title~='Notepad'] > Edit[auto_id='15']"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Attr:
    key: str
    op: str   # '=', '~=', '*='
    value: str


@dataclass
class Step:
    control_type: str
    attrs: list[Attr] = field(default_factory=list)


class SelectorError(Exception):
    pass


_STEP_RE = re.compile(
    r"(\w+)\[([^\]]+)\]"
)
_ATTR_RE = re.compile(
    r"(\w+)\s*(~=|\*=|=)\s*['\"]?([^'\">,\]]+)['\"]?"
)


def parse(selector: str) -> list[Step]:
    """Parse a selector string into a list of Steps."""
    steps = []
    for raw_step in selector.split(">"):
        raw_step = raw_step.strip()
        m = _STEP_RE.match(raw_step)
        if not m:
            raise SelectorError(f"Cannot parse selector step: {raw_step!r}")
        control_type = m.group(1)
        attr_block = m.group(2)
        attrs = []
        for am in _ATTR_RE.finditer(attr_block):
            attrs.append(Attr(key=am.group(1), op=am.group(2), value=am.group(3).strip()))
        steps.append(Step(control_type=control_type, attrs=attrs))
    return steps


def _attr_to_kwarg(attr: Attr) -> dict:
    """Translate one Attr to pywinauto find_elements kwargs."""
    key_map = {
        "auto_id": "auto_id",
        "title": "title",
        "name": "title",
        "class_name": "class_name",
        "control_type": "control_type",
    }
    pwa_key = key_map.get(attr.key, attr.key)
    if attr.op == "~=":
        pwa_key = f"{pwa_key}_re"
        value = f".*{re.escape(attr.value)}.*"
    elif attr.op == "*=":
        pwa_key = f"{pwa_key}_re"
        value = f".*{re.escape(attr.value)}.*"
    else:
        value = attr.value
    return {pwa_key: value}


def resolve(selector: str, root) -> object:
    """Resolve a selector against a pywinauto root element/window.

    Returns the matching wrapper element or raises SelectorError.
    """
    steps = parse(selector)
    current = root
    for i, step in enumerate(steps):
        kwargs: dict = {}
        if step.control_type.lower() not in ("window", "any", "*"):
            kwargs["control_type"] = step.control_type
        for attr in step.attrs:
            kwargs.update(_attr_to_kwarg(attr))
        try:
            if i == 0:
                current = current.window(**kwargs)
            else:
                current = current.child_window(**kwargs)
        except Exception as exc:
            raise SelectorError(
                f"Step {i} ({step!r}) failed: {exc}"
            ) from exc
    return current
