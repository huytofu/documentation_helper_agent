from unittest.mock import patch

from ingestion.cli import main


def test_clear_requires_framework():
    assert main(["--clear"]) != 0


def test_clear_only_no_source(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    with (
        patch("ingestion.clear.clear_namespaces", return_value=["langgraph"]) as clear,
        patch("ingestion.pipeline.run_ingestion") as ingest,
    ):
        code = main(["--clear", "--framework", "langgraph"])
        assert code == 0
        clear.assert_called_once()
        ingest.assert_not_called()


def test_clear_then_ingest_when_source_passed():
    with (
        patch("ingestion.clear.clear_namespaces", return_value=["langgraph"]) as clear,
        patch(
            "ingestion.pipeline.run_ingestion",
            return_value={"firecrawl": {}},
        ) as ingest,
    ):
        code = main(
            ["--clear", "--framework", "langgraph", "--source", "firecrawl", "-y"]
        )
        assert code == 0
        clear.assert_called_once()
        ingest.assert_called_once()
        assert ingest.call_args.kwargs["source"] == "firecrawl"
        assert ingest.call_args.kwargs["frameworks"] == ["langgraph"]


def test_decline_confirm_aborts(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "no")
    with (
        patch("ingestion.clear.clear_namespaces") as clear,
        patch("ingestion.pipeline.run_ingestion") as ingest,
    ):
        code = main(["--clear", "--framework", "all"])
        assert code != 0
        clear.assert_not_called()
        ingest.assert_not_called()


def test_ingest_default_source_without_clear():
    with patch(
        "ingestion.pipeline.run_ingestion",
        return_value={"firecrawl": {}, "chub": {}},
    ) as ingest:
        code = main([])
        assert code == 0
        assert ingest.call_args.kwargs["source"] == "all"
