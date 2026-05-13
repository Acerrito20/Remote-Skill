import pytest

from core.selector import Attr, SelectorError, Step, parse


def test_parse_single_step():
    steps = parse("Edit[auto_id='15']")
    assert len(steps) == 1
    assert steps[0].control_type == "Edit"
    assert steps[0].attrs[0].key == "auto_id"
    assert steps[0].attrs[0].op == "="
    assert steps[0].attrs[0].value == "15"


def test_parse_multi_step():
    steps = parse("Window[title='Notepad'] > Edit[auto_id='15']")
    assert len(steps) == 2
    assert steps[0].control_type == "Window"
    assert steps[1].control_type == "Edit"


def test_parse_fuzzy_op():
    steps = parse("Button[title~='Save']")
    assert steps[0].attrs[0].op == "~="


def test_parse_contains_op():
    steps = parse("Button[title*='Save']")
    assert steps[0].attrs[0].op == "*="


def test_parse_multiple_attrs():
    steps = parse("Edit[auto_id='15',class_name='Edit']")
    assert len(steps[0].attrs) == 2


def test_parse_invalid_raises():
    with pytest.raises(SelectorError):
        parse("NotAValidStep")


def test_parse_empty_raises():
    with pytest.raises(SelectorError):
        parse("")
