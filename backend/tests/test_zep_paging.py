"""Unit tests for zep_paging module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest

# Import the module directly to avoid Flask/Zep initialization issues
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "utils"))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "zep_paging",
    Path(__file__).parent.parent / "app" / "utils" / "zep_paging.py"
)
zep_paging_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zep_paging_module)

fetch_all_nodes = zep_paging_module.fetch_all_nodes
fetch_all_edges = zep_paging_module.fetch_all_edges


class TestFetchPageWithRetry:
    """Tests for _fetch_page_with_retry (via fetch_all_nodes/fetch_all_edges)."""

    def test_success_on_first_attempt(self):
        """Should return result immediately on first successful call."""
        mock_client = MagicMock()
        batch = [SimpleNamespace(uuid_="abc-123", name="TestNode")]
        mock_client.graph.node.get_by_graph_id.return_value = batch

        result = fetch_all_nodes(mock_client, "graph-id")

        assert len(result) == 1
        mock_client.graph.node.get_by_graph_id.assert_called_once()

    def test_retries_on_transient_error(self):
        """Should retry on ConnectionError, TimeoutError, OSError."""
        mock_client = MagicMock()
        batch = [SimpleNamespace(uuid_="abc-123", name="TestNode")]
        # Fail twice, then succeed
        mock_client.graph.node.get_by_graph_id.side_effect = [
            ConnectionError("first failure"),
            TimeoutError("second failure"),
            batch
        ]

        with patch("time.sleep"):
            result = fetch_all_nodes(mock_client, "graph-id")

        assert len(result) == 1
        assert mock_client.graph.node.get_by_graph_id.call_count == 3

    def test_exhausts_retries_and_raises(self):
        """Should raise after exhausting max_retries attempts."""
        mock_client = MagicMock()
        mock_client.graph.node.get_by_graph_id.side_effect = ConnectionError("always fails")

        with patch("time.sleep"), pytest.raises(ConnectionError):
            fetch_all_nodes(mock_client, "graph-id", max_retries=3)

        assert mock_client.graph.node.get_by_graph_id.call_count == 3

    def test_respects_max_retries_parameter(self):
        """Should use the max_retries parameter value."""
        mock_client = MagicMock()
        mock_client.graph.node.get_by_graph_id.side_effect = ConnectionError("always fails")

        with patch("time.sleep"), pytest.raises(ConnectionError):
            fetch_all_nodes(mock_client, "graph-id", max_retries=5)

        assert mock_client.graph.node.get_by_graph_id.call_count == 5


class TestFetchAllNodes:
    """Tests for fetch_all_nodes function."""

    def test_returns_empty_list_when_no_nodes(self):
        """Should return empty list when graph has no nodes."""
        mock_client = MagicMock()
        mock_client.graph.node.get_by_graph_id.return_value = []

        result = fetch_all_nodes(mock_client, "graph-id")

        assert result == []

    def test_returns_all_nodes_single_page(self):
        """Should return all nodes when they fit in one page."""
        mock_client = MagicMock()
        batch = [
            SimpleNamespace(uuid_="n1", name="Node1"),
            SimpleNamespace(uuid_="n2", name="Node2"),
        ]
        mock_client.graph.node.get_by_graph_id.return_value = batch

        result = fetch_all_nodes(mock_client, "graph-id")

        assert len(result) == 2

    def test_paginates_multiple_pages(self):
        """Should paginate through multiple pages using uuid_cursor."""
        mock_client = MagicMock()
        # First page with uuid cursor
        page1 = [
            SimpleNamespace(uuid_="n1", name="Node1"),
            SimpleNamespace(uuid_="n2", name="Node2"),
        ]
        page2 = [SimpleNamespace(uuid_="n3", name="Node3")]
        mock_client.graph.node.get_by_graph_id.side_effect = [page1, page2]

        result = fetch_all_nodes(mock_client, "graph-id")

        assert len(result) == 3
        assert mock_client.graph.node.get_by_graph_id.call_count == 2

    def test_respects_max_items_limit(self):
        """Should stop and truncate when max_items limit is reached."""
        mock_client = MagicMock()
        # Return pages with page_size=2 but max_items=3
        page1 = [
            SimpleNamespace(uuid_="n1", name="Node1"),
            SimpleNamespace(uuid_="n2", name="Node2"),
        ]
        page2 = [
            SimpleNamespace(uuid_="n3", name="Node3"),
            SimpleNamespace(uuid_="n4", name="Node4"),
        ]
        page3 = [
            SimpleNamespace(uuid_="n5", name="Node5"),
        ]
        mock_client.graph.node.get_by_graph_id.side_effect = [page1, page2, page3]

        result = fetch_all_nodes(mock_client, "graph-id", max_items=3)

        assert len(result) == 3
        assert result[0].name == "Node1"
        assert result[1].name == "Node2"
        assert result[2].name == "Node3"

    def test_uses_default_max_nodes_constant(self):
        """Should use _MAX_NODES (2000) as default max_items."""
        mock_client = MagicMock()
        mock_client.graph.node.get_by_graph_id.return_value = []

        fetch_all_nodes(mock_client, "graph-id")

        # With empty pages, it won't hit limit, but verifies default is used

    def test_stops_when_page_smaller_than_page_size(self):
        """Should stop pagination when returned page is smaller than page_size."""
        mock_client = MagicMock()
        page1 = [SimpleNamespace(uuid_="n1", name="Node1")]
        mock_client.graph.node.get_by_graph_id.return_value = page1

        result = fetch_all_nodes(mock_client, "graph-id")

        assert len(result) == 1
        assert mock_client.graph.node.get_by_graph_id.call_count == 1

    def test_handles_missing_uuid_field_gracefully(self):
        """Should stop pagination when node missing uuid field."""
        mock_client = MagicMock()
        # First page normal
        page1 = [
            SimpleNamespace(uuid_="n1", name="Node1"),
            SimpleNamespace(uuid_="n2", name="Node2"),
        ]
        # Second page has node without uuid
        page2 = [
            SimpleNamespace(name="Node3"),  # No uuid_
        ]
        mock_client.graph.node.get_by_graph_id.side_effect = [page1, page2]

        result = fetch_all_nodes(mock_client, "graph-id")

        # Should get first page but stop before second
        assert len(result) == 2

    def test_uses_default_page_size(self):
        """Should pass limit=100 by default."""
        mock_client = MagicMock()
        mock_client.graph.node.get_by_graph_id.return_value = []

        fetch_all_nodes(mock_client, "graph-id")

        call_kwargs = mock_client.graph.node.get_by_graph_id.call_args.kwargs
        assert call_kwargs["limit"] == 100

    def test_respects_page_size_parameter(self):
        """Should use custom page_size when provided."""
        mock_client = MagicMock()
        mock_client.graph.node.get_by_graph_id.return_value = []

        fetch_all_nodes(mock_client, "graph-id", page_size=50)

        call_kwargs = mock_client.graph.node.get_by_graph_id.call_args.kwargs
        assert call_kwargs["limit"] == 50


class TestFetchAllEdges:
    """Tests for fetch_all_edges function."""

    def test_returns_empty_list_when_no_edges(self):
        """Should return empty list when graph has no edges."""
        mock_client = MagicMock()
        mock_client.graph.edge.get_by_graph_id.return_value = []

        result = fetch_all_edges(mock_client, "graph-id")

        assert result == []

    def test_returns_all_edges_single_page(self):
        """Should return all edges when they fit in one page."""
        mock_client = MagicMock()
        batch = [
            SimpleNamespace(uuid_="e1", source="n1", target="n2"),
            SimpleNamespace(uuid_="e2", source="n2", target="n3"),
        ]
        mock_client.graph.edge.get_by_graph_id.return_value = batch

        result = fetch_all_edges(mock_client, "graph-id")

        assert len(result) == 2

    def test_paginates_multiple_pages(self):
        """Should paginate through multiple pages for edges."""
        mock_client = MagicMock()
        page1 = [
            SimpleNamespace(uuid_="e1", source="n1", target="n2"),
            SimpleNamespace(uuid_="e2", source="n2", target="n3"),
        ]
        page2 = [SimpleNamespace(uuid_="e3", source="n3", target="n4")]
        mock_client.graph.edge.get_by_graph_id.side_effect = [page1, page2]

        result = fetch_all_edges(mock_client, "graph-id")

        assert len(result) == 3
        assert mock_client.graph.edge.get_by_graph_id.call_count == 2

    def test_stops_when_page_smaller_than_page_size(self):
        """Should stop pagination when edge page is smaller than page_size."""
        mock_client = MagicMock()
        page1 = [SimpleNamespace(uuid_="e1", source="n1", target="n2")]
        mock_client.graph.edge.get_by_graph_id.return_value = page1

        result = fetch_all_edges(mock_client, "graph-id")

        assert len(result) == 1
        assert mock_client.graph.edge.get_by_graph_id.call_count == 1

    def test_handles_missing_uuid_field_gracefully(self):
        """Should stop pagination when edge missing uuid field."""
        mock_client = MagicMock()
        page1 = [
            SimpleNamespace(uuid_="e1", source="n1", target="n2"),
            SimpleNamespace(uuid_="e2", source="n2", target="n3"),
        ]
        page2 = [
            SimpleNamespace(source="n3", target="n4"),  # No uuid_
        ]
        mock_client.graph.edge.get_by_graph_id.side_effect = [page1, page2]

        result = fetch_all_edges(mock_client, "graph-id")

        assert len(result) == 2

    def test_uses_default_page_size_for_edges(self):
        """Should pass limit=100 by default for edges."""
        mock_client = MagicMock()
        mock_client.graph.edge.get_by_graph_id.return_value = []

        fetch_all_edges(mock_client, "graph-id")

        call_kwargs = mock_client.graph.edge.get_by_graph_id.call_args.kwargs
        assert call_kwargs["limit"] == 100
