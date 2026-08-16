"""Tests for caps transforms."""

from __future__ import annotations

import pytest

from versa_note.transforms import (
    CAPS_TRANSFORMS,
    caps_initial,
    caps_lower,
    caps_sentence,
    caps_upper,
)


def test_caps_transforms_registry_keys() -> None:
    assert set(CAPS_TRANSFORMS) == {"upper", "lower", "initial", "sentence"}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", ""),
        ("Hello", "HELLO"),
        ("café", "CAFÉ"),
        ("aBc", "ABC"),
    ],
)
def test_caps_upper(text: str, expected: str) -> None:
    assert caps_upper(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", ""),
        ("Hello", "hello"),
        ("ABC", "abc"),
    ],
)
def test_caps_lower(text: str, expected: str) -> None:
    assert caps_lower(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", ""),
        ("hello. world!", "Hello. World!"),
        ("already. Fine?", "Already. Fine?"),
        ("line one\nline two", "Line one\nLine two"),
        ("wait... what", "Wait... What"),
    ],
)
def test_caps_initial(text: str, expected: str) -> None:
    assert caps_initial(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", ""),
        ("hello world", "Hello World"),
        ("well-known path", "Well-Known Path"),
        ("a  b", "A  B"),
    ],
)
def test_caps_sentence(text: str, expected: str) -> None:
    assert caps_sentence(text) == expected
