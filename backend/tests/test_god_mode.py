import os
import tempfile
import pytest
from app.services.narrative.god_mode import inject_event
from app.services.narrative.story_store import StoryStore
from app.services.narrative.world_state import WorldStateStore


@pytest.fixture
def temp_sim_dir():
    with tempfile.TemporaryDirectory() as d:
        sim_dir = os.path.join(d, "sim_test")
        os.makedirs(sim_dir)
        yield sim_dir


def test_inject_event_appends_to_log(temp_sim_dir):
    evt = inject_event(temp_sim_dir, description="A storm arrives.", round_num=5)
    assert evt["description"] == "A storm arrives."
    assert evt["round"] == 5
    assert evt["id"] == "evt_1"
    assert evt["type"] == "god_mode_injection"

    log = WorldStateStore(temp_sim_dir).load()["event_log"]
    assert len(log) == 1


def test_inject_event_defaults_round_to_beats_plus_one(temp_sim_dir):
    store = StoryStore(temp_sim_dir)
    store.append_beat({"round": 3, "prose": "beat 3"})

    evt = inject_event(temp_sim_dir, description="auto round")
    assert evt["round"] == 4


def test_inject_event_defaults_round_to_one_when_no_beats(temp_sim_dir):
    evt = inject_event(temp_sim_dir, description="first event")
    assert evt["round"] == 1
