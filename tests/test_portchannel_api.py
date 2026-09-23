import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app import app, project_state, get_enterprise_preset

client = TestClient(app)

def setup_function():
    global project_state
    preset = get_enterprise_preset()
    # Reset state to preset
    client.post("/api/project/new", json={"project_name": "Test PortChannel Suite"})

def test_add_single_link():
    res = client.post("/api/topology/link", json={
        "source_device": "DIST-02",
        "source_port": "GigabitEthernet1/0/3",
        "target_device": "ACC-02",
        "target_port": "GigabitEthernet1/0/3",
        "link_speed": "10G"
    })
    assert res.status_code == 200
    data = res.json()
    link = next((l for l in data["topology_links"] if l["source_device"] == "DIST-02" and l["source_port"] == "GigabitEthernet1/0/3"), None)
    assert link is not None
    assert link["link_speed"] == "10G"
    assert link["port_channel_id"] is None

def test_add_portchannel_multi_port_matching():
    res = client.post("/api/topology/link", json={
        "source_device": "CORE-01",
        "source_ports": ["GigabitEthernet1/0/21", "GigabitEthernet1/0/22"],
        "target_device": "CORE-02",
        "target_ports": ["GigabitEthernet1/0/21", "GigabitEthernet1/0/22"],
        "link_speed": "40G",
        "port_channel_id": "Po99"
    })
    assert res.status_code == 200
    data = res.json()
    po = next((p for p in data["port_channels"] if p["id"] == "Po99"), None)
    assert po is not None
    assert "GigabitEthernet1/0/21" in po["source_member_ports"]
    assert "GigabitEthernet1/0/22" in po["source_member_ports"]
    assert "GigabitEthernet1/0/21" in po["target_member_ports"]
    assert "GigabitEthernet1/0/22" in po["target_member_ports"]

def test_add_portchannel_mismatched_index_counts_fails():
    # 2 source ports vs 1 target port -> should be rejected with 400
    res = client.post("/api/topology/link", json={
        "source_device": "CORE-01",
        "source_ports": ["GigabitEthernet1/0/23", "GigabitEthernet1/0/24"],
        "target_device": "CORE-02",
        "target_ports": ["GigabitEthernet1/0/23"],
        "link_speed": "40G",
        "port_channel_id": "Po88"
    })
    assert res.status_code == 400
    assert "must match" in res.json()["detail"].lower()

if __name__ == "__main__":
    test_add_single_link()
    print("[OK] test_add_single_link passed")
    test_add_portchannel_multi_port_matching()
    print("[OK] test_add_portchannel_multi_port_matching passed")
    test_add_portchannel_mismatched_index_counts_fails()
    print("[OK] test_add_portchannel_mismatched_index_counts_fails passed")
    print("ALL API TESTS PASSED!")
