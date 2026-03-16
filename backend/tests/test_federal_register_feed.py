import io
import json
import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[2]
SERVICES_ROOT = Path(__file__).resolve().parents[1] / "app" / "services"

app_pkg = types.ModuleType("app")
app_pkg.__path__ = []
services_pkg = types.ModuleType("app.services")
services_pkg.__path__ = [str(SERVICES_ROOT)]
sys.modules["app"] = app_pkg
sys.modules["app.services"] = services_pkg

# Load query profiles first (dependency of federal_register_feed)
profiles_full_name = "app.services.federal_register_query_profiles"
profiles_spec = spec_from_file_location(profiles_full_name, SERVICES_ROOT / "federal_register_query_profiles.py")
profiles_module = module_from_spec(profiles_spec)
sys.modules[profiles_full_name] = profiles_module
assert profiles_spec.loader is not None
profiles_spec.loader.exec_module(profiles_module)

# Load relevance scorer (dependency of federal_register_feed)
relevance_full_name = "app.services.federal_register_relevance"
relevance_spec = spec_from_file_location(relevance_full_name, SERVICES_ROOT / "federal_register_relevance.py")
relevance_module = module_from_spec(relevance_spec)
sys.modules[relevance_full_name] = relevance_module
assert relevance_spec.loader is not None
relevance_spec.loader.exec_module(relevance_module)

full_name = "app.services.federal_register_feed"
spec = spec_from_file_location(full_name, SERVICES_ROOT / "federal_register_feed.py")
module = module_from_spec(spec)
sys.modules[full_name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


def _load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


# ---------------------------------------------------------------------------
# URL building
# ---------------------------------------------------------------------------

def test_build_federal_register_documents_url():
    url = module.build_federal_register_documents_url(
        query="rare earth robotics",
        agencies=["bureau-of-industry-and-security"],
        document_types=["RULE"],
        published_gte="2026-01-01",
        per_page=15,
        page=2,
    )
    assert "conditions%5Bterm%5D=rare+earth+robotics" in url
    assert "conditions%5Bagencies%5D%5B%5D=bureau-of-industry-and-security" in url
    assert "conditions%5Btype%5D%5B%5D=RULE" in url
    assert "conditions%5Bpublication_date%5D%5Bgte%5D=2026-01-01" in url
    assert "per_page=15" in url
    assert "page=2" in url


def test_build_url_strips_invalid_agencies():
    """Invalid agency slugs must be silently dropped to prevent HTTP 400."""
    url = module.build_federal_register_documents_url(
        query="test",
        agencies=["INVALID_AGENCY", "bureau-of-industry-and-security", "nonsense"],
    )
    assert "bureau-of-industry-and-security" in url
    assert "INVALID_AGENCY" not in url
    assert "nonsense" not in url


def test_build_url_resolves_agency_aliases():
    """Common abbreviations like 'BIS' should resolve to the canonical slug."""
    url = module.build_federal_register_documents_url(
        query="test",
        agencies=["BIS", "DOE"],
    )
    assert "bureau-of-industry-and-security" in url
    assert "energy-department" in url


def test_build_url_no_agencies_when_all_invalid():
    """When every supplied agency is invalid, no conditions[agencies][] param appears."""
    url = module.build_federal_register_documents_url(
        query="test",
        agencies=["fake-one", "fake-two"],
    )
    assert "conditions%5Bagencies%5D" not in url


# ---------------------------------------------------------------------------
# Profile resolution
# ---------------------------------------------------------------------------

def test_list_query_profiles():
    names = profiles_module.list_query_profiles()
    assert "critical_materials" in names
    assert "semiconductors" in names
    assert "robotics" in names
    # New narrower profiles
    assert "rare_earths" in names
    assert "processed_critical_minerals" in names
    assert "stockpile_and_section232" in names
    assert "entity_list_export_controls" in names


def test_get_query_profile_returns_deep_copy():
    p1 = profiles_module.get_query_profile("critical_materials")
    p2 = profiles_module.get_query_profile("critical_materials")
    assert p1 is not p2
    assert p1 == p2
    p1["query"] = "modified"
    assert p2["query"] != "modified"


def test_get_query_profile_unknown_returns_none():
    assert profiles_module.get_query_profile("nonexistent") is None


def test_resolve_query_profile_merges_overrides():
    resolved = profiles_module.resolve_query_profile(
        "critical_materials",
        overrides={"query": "custom query", "per_page": 5},
    )
    assert resolved["query"] == "custom query"
    assert resolved["per_page"] == 5
    # Profile defaults still present where not overridden
    assert "critical_materials" in resolved["target_themes"]


def test_resolve_query_profile_no_profile():
    """With no profile name, only overrides are returned."""
    resolved = profiles_module.resolve_query_profile(
        None,
        overrides={"query": "standalone"},
    )
    assert resolved == {"query": "standalone"}


def test_resolve_query_profile_validates_agencies():
    """Invalid agencies in the merged result must be stripped."""
    resolved = profiles_module.resolve_query_profile(
        None,
        overrides={"agencies": ["BIS", "INVALID", "DOE"]},
    )
    assert "bureau-of-industry-and-security" in resolved["agencies"]
    assert "energy-department" in resolved["agencies"]
    assert "INVALID" not in resolved["agencies"]


def test_narrow_profiles_resolve_correctly():
    """Each narrow profile should have its own query and markers."""
    re_profile = profiles_module.get_query_profile("rare_earths")
    assert re_profile is not None
    assert "rare earth" in re_profile["query"]
    assert "positive_markers" in re_profile
    assert "negative_markers" in re_profile

    s232 = profiles_module.get_query_profile("stockpile_and_section232")
    assert s232 is not None
    assert "section 232" in s232["query"]

    el = profiles_module.get_query_profile("entity_list_export_controls")
    assert el is not None
    assert "entity list" in el["query"]


# ---------------------------------------------------------------------------
# Agency slug validation
# ---------------------------------------------------------------------------

def test_validate_agency_slug_canonical():
    assert profiles_module.validate_agency_slug("bureau-of-industry-and-security") == "bureau-of-industry-and-security"


def test_validate_agency_slug_alias():
    assert profiles_module.validate_agency_slug("BIS") == "bureau-of-industry-and-security"
    assert profiles_module.validate_agency_slug("bis") == "bureau-of-industry-and-security"


def test_validate_agency_slug_freeform():
    assert profiles_module.validate_agency_slug("Bureau of Industry and Security") == "bureau-of-industry-and-security"


def test_validate_agency_slug_unknown():
    assert profiles_module.validate_agency_slug("unknown-agency") is None


def test_validate_agency_slugs_dedupes():
    result = profiles_module.validate_agency_slugs(["BIS", "bis", "bureau-of-industry-and-security"])
    assert result == ["bureau-of-industry-and-security"]


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------

def test_relevance_scoring_relevant_document():
    """A clearly relevant doc about critical minerals should score high."""
    doc = {
        "title": "Final 2025 List of Critical Minerals",
        "abstract": "Identifies critical minerals including rare earth elements, cobalt, lithium.",
        "topics": ["Critical Materials", "Mining"],
    }
    result = relevance_module.score_document_relevance(doc)
    assert result["relevance_score"] >= 50
    assert result["relevance_class"] == "directly_relevant"
    assert len(result["positive_markers"]) >= 3
    assert len(result["negative_markers"]) == 0


def test_relevance_scoring_noise_document():
    """A wildlife/endangered species doc should score as noise."""
    doc = {
        "title": "Endangered and Threatened Wildlife and Plants; Status for Black-Capped Vireo",
        "abstract": "Determination of endangered species status under the Endangered Species Act.",
        "topics": ["Wildlife", "Endangered Species"],
    }
    result = relevance_module.score_document_relevance(doc)
    assert result["relevance_class"] == "noise"
    assert result["relevance_score"] < 20
    assert len(result["negative_markers"]) >= 2


def test_relevance_scoring_consumer_furnace_is_noise():
    doc = {
        "title": "Energy Conservation Standards for Consumer Furnaces",
        "abstract": "Standards for consumer furnaces to improve energy efficiency.",
        "topics": ["Energy Conservation"],
    }
    result = relevance_module.score_document_relevance(doc)
    assert result["relevance_class"] == "noise"


def test_relevance_scoring_adjacent_document():
    """A doc that mentions supply chain but isn't specifically about critical minerals."""
    doc = {
        "title": "Notice on Supply Chain Resilience Requirements",
        "abstract": "New requirements for supply chain disclosure affecting national security.",
        "topics": ["National Security"],
    }
    result = relevance_module.score_document_relevance(doc)
    assert result["relevance_class"] in ("adjacent", "directly_relevant")
    assert result["relevance_score"] >= 20


# ---------------------------------------------------------------------------
# Conditional process-layer enrichment
# ---------------------------------------------------------------------------

def test_match_process_layers_only_when_markers_present():
    """Process layers should only be assigned when document text matches markers."""
    doc_mining = {
        "title": "Rare Earth Mining Expansion in Western Australia",
        "abstract": "New rare earth mining operations with ore processing facilities.",
    }
    layers = relevance_module.match_process_layers(
        doc_mining,
        ["Rare Earth Mining", "Rare Earth Separation", "Cobalt Refining", "Lithium Processing"],
    )
    assert "Rare Earth Mining" in layers
    assert "Cobalt Refining" not in layers
    assert "Lithium Processing" not in layers


def test_match_process_layers_empty_for_irrelevant():
    """An irrelevant doc should match no process layers."""
    doc_noise = {
        "title": "Consumer Furnace Efficiency Standards",
        "abstract": "Residential heating appliance regulations.",
    }
    layers = relevance_module.match_process_layers(
        doc_noise,
        ["Rare Earth Mining", "Cobalt Refining"],
    )
    assert layers == []


def test_match_process_layers_semiconductor():
    doc = {
        "title": "Wafer Fabrication Export Controls",
        "abstract": "New controls on semiconductor equipment and wafer fabrication technology.",
    }
    layers = relevance_module.match_process_layers(
        doc,
        ["Wafer Fabrication", "Semiconductor Equipment", "Rare Earth Mining"],
    )
    assert "Wafer Fabrication" in layers
    assert "Semiconductor Equipment" in layers
    assert "Rare Earth Mining" not in layers


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def test_filter_documents_excludes_noise():
    """Noise documents must not survive the default filter."""
    mixed = _load_json("research/templates/federal-register-api-mixed-relevance-sample-v1.json")
    results = mixed["results"]
    filtered = relevance_module.filter_documents_by_relevance(results)
    titles = [d["title"] for d in filtered]
    # The three relevant docs should survive
    assert any("Critical Minerals" in t for t in titles)
    assert any("Entity List" in t for t in titles)
    # The noise docs should be gone
    assert not any("Vireo" in t for t in titles)
    assert not any("Consumer Furnaces" in t for t in titles)


def test_filter_no_adjacent():
    """With include_adjacent=False, only directly_relevant docs survive."""
    mixed = _load_json("research/templates/federal-register-api-mixed-relevance-sample-v1.json")
    results = mixed["results"]
    filtered = relevance_module.filter_documents_by_relevance(
        results, include_adjacent=False,
    )
    for doc in filtered:
        assert doc["_relevance"]["relevance_class"] == "directly_relevant"


# ---------------------------------------------------------------------------
# Live-fetch normalization (mocked)
# ---------------------------------------------------------------------------

def test_fetch_federal_register_policy_feed_normalizes_results(monkeypatch):
    api_payload = _load_json("research/templates/federal-register-api-sample-response-v1.json")

    def fake_urlopen(request, timeout=20):
        return _FakeResponse(api_payload)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    payload = module.fetch_federal_register_policy_feed(
        query="rare earth robotics",
        agencies=["bureau-of-industry-and-security"],
        target_themes=["robotics_supply_chain", "critical_materials"],
        focus_process_layers=["Neodymium Processing"],
        focus_geographies=["China"],
        ticker_refs=["MP", "UUUU"],
        policy_scope=["export_control"],
        per_page=5,
        minimum_relevance_score=0,  # don't filter for this legacy test
    )

    assert payload["synthetic_sample"] is False
    assert payload["fetch_metadata"]["result_count"] == 2
    assert len(payload["feed_documents"]) == 2
    first = payload["feed_documents"][0]
    assert first["source_target_id"] == "src_target_federal_register_notices"
    assert first["source_class"] == "government_policy_enforcement"
    assert first["ticker_refs"] == ["MP", "UUUU"]


def test_fetch_with_query_profile(monkeypatch):
    """Fetching with a named profile should populate query and metadata from the profile."""
    api_payload = _load_json("research/templates/federal-register-api-sample-response-v1.json")

    def fake_urlopen(request, timeout=20):
        return _FakeResponse(api_payload)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    payload = module.fetch_federal_register_policy_feed(
        query_profile="semiconductors",
        minimum_relevance_score=0,
    )

    assert payload["fetch_metadata"]["query_profile"] == "semiconductors"
    assert "semiconductors" in payload["theme"]
    assert "semiconductor" in payload["notes"][2].lower()
    assert len(payload["feed_documents"]) == 2
    first = payload["feed_documents"][0]
    assert "semiconductors" in first["theme_refs"]
    assert "NVDA" in first["ticker_refs"]


def test_fetch_profile_with_override(monkeypatch):
    """Explicit query should override the profile default."""
    api_payload = _load_json("research/templates/federal-register-api-sample-response-v1.json")

    def fake_urlopen(request, timeout=20):
        return _FakeResponse(api_payload)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    payload = module.fetch_federal_register_policy_feed(
        query_profile="semiconductors",
        query="custom override query",
        minimum_relevance_score=0,
    )

    assert "custom override query" in payload["notes"][2]


def test_fetch_graceful_fallback_on_400(monkeypatch):
    """If the API returns 400 with agencies, the fetch should retry without agencies."""
    api_payload = _load_json("research/templates/federal-register-api-sample-response-v1.json")
    call_count = {"n": 0}

    def fake_urlopen(request, timeout=20):
        call_count["n"] += 1
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if call_count["n"] == 1 and "agencies" in url:
            raise HTTPError(url, 400, "Bad Request", {}, io.BytesIO(b""))
        return _FakeResponse(api_payload)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    payload = module.fetch_federal_register_policy_feed(
        query="test",
        agencies=["bureau-of-industry-and-security"],
        minimum_relevance_score=0,
    )

    assert call_count["n"] == 2
    assert payload["fetch_metadata"]["result_count"] == 2


def test_fetch_non_400_error_propagates(monkeypatch):
    """Non-400 HTTP errors should not be swallowed."""
    def fake_urlopen(request, timeout=20):
        raise HTTPError("http://example.com", 500, "Server Error", {}, io.BytesIO(b""))

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    import pytest
    with pytest.raises(HTTPError) as exc_info:
        module.fetch_federal_register_policy_feed(query="test")
    assert exc_info.value.code == 500


# ---------------------------------------------------------------------------
# End-to-end: mixed sample with filtering
# ---------------------------------------------------------------------------

def test_end_to_end_mixed_sample_filters_noise(monkeypatch):
    """Mixed FR results should produce fewer, cleaner normalized documents."""
    mixed = _load_json("research/templates/federal-register-api-mixed-relevance-sample-v1.json")

    def fake_urlopen(request, timeout=20):
        return _FakeResponse(mixed)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    payload = module.fetch_federal_register_policy_feed(
        query_profile="critical_materials",
    )

    # Should have filtered out noise (vireo, furnaces)
    assert payload["fetch_metadata"]["raw_result_count"] == 5
    assert payload["fetch_metadata"]["filtered_out"] >= 2
    titles = [d["title"] for d in payload["feed_documents"]]
    assert not any("Vireo" in t for t in titles)
    assert not any("Consumer Furnaces" in t for t in titles)
    # Relevant docs should survive
    assert any("Critical Minerals" in t for t in titles)


def test_end_to_end_conditional_process_layers(monkeypatch):
    """Process layers should only be assigned when text markers match."""
    mixed = _load_json("research/templates/federal-register-api-mixed-relevance-sample-v1.json")

    def fake_urlopen(request, timeout=20):
        return _FakeResponse(mixed)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    payload = module.fetch_federal_register_policy_feed(
        query_profile="critical_materials",
    )

    for doc in payload["feed_documents"]:
        matched_layers = doc.get("matched_process_layers", [])
        # Each doc should only have layers that actually match its content
        if "Entity List" in doc["title"]:
            # Entity list doc doesn't talk about lithium processing
            assert "Lithium Processing" not in matched_layers
        # No doc should get ALL 5 profile layers blindly stamped
        assert len(matched_layers) < 5


def test_end_to_end_relevance_metadata_persisted(monkeypatch):
    """Each normalized doc should carry relevance metadata."""
    mixed = _load_json("research/templates/federal-register-api-mixed-relevance-sample-v1.json")

    def fake_urlopen(request, timeout=20):
        return _FakeResponse(mixed)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    payload = module.fetch_federal_register_policy_feed(
        query_profile="critical_materials",
    )

    for doc in payload["feed_documents"]:
        assert "relevance_score" in doc
        assert "relevance_class" in doc
        assert doc["relevance_class"] in ("directly_relevant", "adjacent")
        assert "positive_markers" in doc
        assert "matched_profile" in doc


def test_end_to_end_adjacent_docs_get_weaker_relationships(monkeypatch):
    """Adjacent docs should have weaker relationship expansion."""
    mixed = _load_json("research/templates/federal-register-api-mixed-relevance-sample-v1.json")

    def fake_urlopen(request, timeout=20):
        return _FakeResponse(mixed)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    payload = module.fetch_federal_register_policy_feed(
        query_profile="critical_materials",
    )

    for doc in payload["feed_documents"]:
        if doc["relevance_class"] == "adjacent":
            for rel in doc["relationship_hints"]:
                assert rel["relationship_strength"] == "low"
                assert rel["confidence"] == "low"
                # Adjacent docs should not have CONSTRAINED_BY expansion
                assert rel["relationship_type"] != "CONSTRAINED_BY"
