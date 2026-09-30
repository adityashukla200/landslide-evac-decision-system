"""Tests for Dimension 6: AI Disaster Copilot & Human-in-the-Loop Decision Support."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.copilot.rag_assistant import IncidentCommanderCopilot


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestCopilotEngine:
    def test_copilot_sitrep_generation(self):
        copilot = IncidentCommanderCopilot()
        sitrep = copilot.generate_sitrep()
        assert sitrep["threat_level"] == "RED_ALERT"
        assert len(sitrep["active_cloudburst_zones"]) >= 1
        assert "SHELTER_HARSIL_ARMY" in sitrep["critical_shelters_saturated"][0]

    def test_copilot_broadcast_proposal(self):
        copilot = IncidentCommanderCopilot()
        res = copilot.process_query("We need to broadcast an emergency warning to Harsil")
        assert len(res["proposed_actions"]) >= 1
        action = res["proposed_actions"][0]
        assert action["action_name"] == "DISPATCH_CELL_BROADCAST"
        assert action["requires_approval"] is True
        assert action["status"] == "PROPOSED"

    def test_copilot_shelter_diversion_proposal(self):
        copilot = IncidentCommanderCopilot()
        res = copilot.process_query("Check shelter capacity and divert people if needed")
        assert any(a["action_name"] == "DIVERT_SHELTER" for a in res["proposed_actions"])

    def test_action_execution_workflow(self):
        copilot = IncidentCommanderCopilot()
        query_res = copilot.process_query("Send alert to Harsil")
        act_id = query_res["proposed_actions"][0]["action_id"]

        # Confirm action
        exec_res = copilot.execute_action(
            action_id=act_id,
            approved=True,
            notes="Authorized by Commander Sharma",
        )
        assert exec_res["status"] == "EXECUTED"
        assert "Authorized by" in exec_res["result_message"]


class TestCopilotEndpoints:
    def test_copilot_chat_endpoint(self, client):
        payload = {
            "message": "Give me a briefing on the situation and recommend actions",
            "role": "INCIDENT_COMMANDER",
        }
        resp = client.post("/api/v1/copilot/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "response_text" in data
        assert "sitrep_summary" in data

    def test_copilot_execute_action_endpoint(self, client):
        # First trigger an action
        chat_resp = client.post("/api/v1/copilot/chat", json={"message": "Broadcast emergency alert"})
        assert chat_resp.status_code == 200
        actions = chat_resp.json()["proposed_actions"]
        assert len(actions) >= 1
        act_id = actions[0]["action_id"]

        exec_payload = {
            "action_id": act_id,
            "approved": True,
            "officer_notes": "Immediate execution granted"
        }
        resp = client.post("/api/v1/copilot/actions/execute", json=exec_payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "EXECUTED"

    def test_copilot_sitrep_endpoint(self, client):
        resp = client.get("/api/v1/copilot/sitrep")
        assert resp.status_code == 200
        assert "threat_level" in resp.json()
