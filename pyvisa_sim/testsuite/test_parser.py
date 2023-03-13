# -*- coding: utf-8 -*-
from typing import Dict, Tuple

import pytest

from pyvisa_sim import parser
from pyvisa_sim.component import NoResponse, OptionalStr


@pytest.mark.parametrize(
    "dialogue_dict, want",
    [
        ({"q": "foo", "r": "bar"}, ("foo", "bar")),
        ({"q": "foo ", "r": " bar"}, ("foo", "bar")),
        ({"q": " foo", "r": "bar "}, ("foo", "bar")),
        ({"q": " foo ", "r": " bar "}, ("foo", "bar")),
        # Make sure to support queries that don't have responses
        ({"q": "foo"}, ("foo", NoResponse)),
        # Ignore other keys
        ({"q": "foo", "bar": "bar"}, ("foo", NoResponse)),
    ],
)
def test_get_pair(dialogue_dict: Dict[str, str], want: Tuple[str, OptionalStr]) -> None:
    got = parser._get_pair(dialogue_dict)
    assert got == want


def test_get_pair_requires_query_key() -> None:
    with pytest.raises(KeyError):
        parser._get_pair({"r": "bar"})


@pytest.mark.parametrize(
    "dialogue_dict, want",
    [
        ({"q": "foo", "r": "bar", "e": "baz"}, ("foo", "bar", "baz")),
        ({"q": "foo ", "r": " bar", "e": " baz "}, ("foo", "bar", "baz")),
        ({"q": " foo", "r": "bar ", "e": "baz "}, ("foo", "bar", "baz")),
        ({"q": " foo ", "r": " bar ", "e": " baz"}, ("foo", "bar", "baz")),
        # Make sure to support queries that don't have responses
        ({"q": "foo"}, ("foo", NoResponse, NoResponse)),
        ({"q": "foo", "r": "bar"}, ("foo", "bar", NoResponse)),
        ({"q": "foo", "e": "bar"}, ("foo", NoResponse, "bar")),
        # Ignore other keys
        ({"q": "foo", "bar": "bar"}, ("foo", NoResponse, NoResponse)),
    ],
)
def test_get_triplet(
    dialogue_dict: Dict[str, str], want: Tuple[str, OptionalStr, OptionalStr]
) -> None:
    got = parser._get_triplet(dialogue_dict)
    assert got == want


def test_get_triplet_requires_query_key() -> None:
    with pytest.raises(KeyError):
        parser._get_triplet({"r": "bar"})
