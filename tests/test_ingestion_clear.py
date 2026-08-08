from unittest.mock import MagicMock, patch

import pytest

from ingestion.clear import clear_namespaces


@patch("ingestion.clear._get_index")
def test_clear_listed_namespaces(mock_get_index):
    index = MagicMock()
    mock_get_index.return_value = (index, "documentation-helper-agent")
    cleared = clear_namespaces(is_all=False, namespaces=["langgraph", "chub"])
    assert cleared == ["langgraph", "chub"]
    assert index.delete.call_count == 2
    index.delete.assert_any_call(delete_all=True, namespace="langgraph")
    index.delete.assert_any_call(delete_all=True, namespace="chub")


@patch("ingestion.clear._get_index")
def test_clear_all_lists_namespaces(mock_get_index):
    index = MagicMock()
    index.describe_index_stats.return_value = {
        "namespaces": {
            "langgraph": {"vector_count": 1},
            "chub": {"vector_count": 2},
        }
    }
    mock_get_index.return_value = (index, "documentation-helper-agent")
    cleared = clear_namespaces(is_all=True, namespaces=[])
    assert set(cleared) == {"langgraph", "chub"}
    assert index.delete.call_count == 2


@patch.dict("os.environ", {}, clear=True)
def test_missing_creds():
    with pytest.raises(ValueError, match="PINECONE"):
        clear_namespaces(is_all=False, namespaces=["langgraph"])
