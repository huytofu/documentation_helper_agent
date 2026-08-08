import pytest

from ingestion.framework_arg import parse_framework_arg


def test_all():
    assert parse_framework_arg("all") == (True, [])


def test_comma_list_trims():
    assert parse_framework_arg("langgraph, llamaindex") == (
        False,
        ["langgraph", "llamaindex"],
    )


def test_single_namespace():
    assert parse_framework_arg("chub") == (False, ["chub"])


@pytest.mark.parametrize(
    "bad",
    ["", "  ", "foo", "langgraph,foo", "langgraph,", ",langgraph", "all,langgraph"],
)
def test_rejects_invalid(bad):
    with pytest.raises(ValueError):
        parse_framework_arg(bad)
