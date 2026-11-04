import json
from pathlib import Path
import sys
import tempfile
from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api
import config
import core
import db
import render


@pytest.fixture()
def temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setattr(config, "DB_PATH", tmp.name)
    db.init_db(tmp.name)
    yield tmp.name
    Path(tmp.name).unlink(missing_ok=True)


def _seed_officers(db_path: str):
    with db.connect(db_path) as conn:
        ofc_rank = conn.execute("SELECT id FROM ranks WHERE name = 'Officer III'").fetchone()["id"]
        cid_rank = conn.execute("SELECT id FROM ranks WHERE name = 'CID'").fetchone()["id"]
        cpl_rank = conn.execute("SELECT id FROM ranks WHERE level = 5").fetchone()["id"]  # Corporal
        cmd_rank = conn.execute("SELECT id FROM ranks WHERE level = 11").fetchone()["id"]  # Commander

        conn.execute(
            "INSERT INTO officers (discord_id, rp_name, badge, status, rank_id, is_admin) VALUES ('1001', 'John Nolan', '4012', 'active', ?, 0)",
            (ofc_rank,),
        )
        conn.execute(
            "INSERT INTO officers (discord_id, rp_name, badge, status, rank_id, is_admin) VALUES ('1002', 'Tim Bradford', '2108', 'active', ?, 0)",
            (cpl_rank,),
        )
        conn.execute(
            "INSERT INTO officers (discord_id, rp_name, badge, status, rank_id, is_admin) VALUES ('1003', 'Wade Grey', '105', 'active', ?, 0)",
            (cmd_rank,),
        )
        conn.execute(
            "INSERT INTO officers (discord_id, rp_name, badge, status, rank_id, is_admin) VALUES ('1004', 'Zoe Andersen', '101', 'active', ?, 1)",
            (cmd_rank,),
        )
        conn.execute(
            "INSERT INTO officers (discord_id, rp_name, badge, status, rank_id, is_admin) VALUES ('1005', 'Pending Rookie', '9999', 'pending', ?, 0)",
            (ofc_rank,),
        )
        conn.execute(
            "INSERT INTO officers (discord_id, rp_name, badge, division, status, rank_id, is_admin) VALUES ('1006', 'Nyla Harper', '512', 'Criminal Investigation Division', 'active', ?, 0)",
            (cid_rank,),
        )


def test_permissions_and_workflow(temp_db):
    _seed_officers(temp_db)
    ofc = core.get_officer_by_discord("1001", temp_db)
    cpl = core.get_officer_by_discord("1002", temp_db)
    cmd = core.get_officer_by_discord("1003", temp_db)
    admin = core.get_officer_by_discord("1004", temp_db)
    pending = core.get_officer_by_discord("1005", temp_db)

    # Pending officer cannot issue anything
    with pytest.raises(PermissionError):
        core.create_draft(pending, "SW", {}, temp_db)

    # Officer III can issue Search Warrant (DOJ, min_issue=2, min_approve=11)
    sw_data = {
        "case_no": "26-CR-900",
        "target_subject": "Suspect X",
        "target_premises": "123 Grove St",
        "statutes_violated": "PC 187",
        "items_to_seize": "Firearms",
        "probable_cause": "Observed entering with weapon.",
        "night_service": "Daytime Only",
    }
    draft = core.create_draft(ofc, "SW", sw_data, temp_db)
    assert draft["status"] == "PENDING"
    assert draft["control_no"] is None

    # Self-approval is blocked for regular / low-command officers (e.g. Corporal level 5)
    cpl_draft = core.create_draft(cpl, "CM", {
        "recipient_name": "Officer Nolan #4012",
        "award_class": "Medal of Valor",
        "incident_date": "2026-10-31",
        "citation_narrative": "Bravery under fire."
    }, temp_db)
    with pytest.raises(PermissionError):
        core.approve_document(cpl_draft["id"], cpl, temp_db)

    # Corporal (level 5) CANNOT approve a DOJ document (requires Commander+ level 11)
    with pytest.raises(PermissionError):
        core.approve_document(draft["id"], cpl, temp_db)

    # Commander (level 11) CAN approve the Officer's DOJ document
    approved = core.approve_document(draft["id"], cmd, temp_db)
    assert approved["status"] == "APPROVED"
    assert approved["control_no"].startswith("UPD-SW-")
    assert approved["control_no"].endswith("-0001")

    # High Command (Commander level 11+ or Admin) CAN self-approve their own documents
    cmd_draft = core.create_draft(cmd, "SW", sw_data, temp_db)
    approved_self = core.approve_document(cmd_draft["id"], cmd, temp_db)
    assert approved_self["status"] == "APPROVED"
    assert approved_self["control_no"].endswith("-0002")
    assert approved_self["approver_id"] == cmd["id"]

    # Internal Commendation (CM) issued by Corporal can be approved by another Corporal+
    cm_data = {
        "recipient_name": "Officer John Nolan #4012",
        "award_class": "Medal of Valor",
        "incident_date": "2026-10-31",
        "citation_narrative": "Exceptional bravery under fire.",
    }
    cm_draft = core.create_draft(admin, "CM", cm_data, temp_db)
    cm_approved = core.approve_document(cm_draft["id"], cpl, temp_db)
    assert cm_approved["status"] == "APPROVED"
    assert cm_approved["control_no"].startswith("UPD-CM-")

    # CID officer CAN issue DOJ documents (including SW and SO) and CANNOT issue or approve internal documents (CM, FQ)
    cid = core.get_officer_by_discord("1006", temp_db)
    cid_sw = core.create_draft(cid, "SW", sw_data, temp_db)
    assert cid_sw["status"] == "PENDING"
    so_data = {
        "operation_name": "OP NIGHTFALL",
        "operational_window": "Nov 4 - Nov 6",
        "situation": "Armed gang activity.",
        "mission": "Execute warrants.",
        "execution": "Phase 1 & 2.",
        "roe_safeguards": "Bodycams active.",
    }
    cid_so = core.create_draft(cid, "SO", so_data, temp_db)
    assert cid_so["status"] == "PENDING"
    with pytest.raises(PermissionError):
        core.create_draft(cid, "CM", cm_data, temp_db)
    with pytest.raises(PermissionError):
        core.approve_document(cpl_draft["id"], cid, temp_db)


def test_xml_escape_and_pdf_png_render(temp_db):
    _seed_officers(temp_db)
    cpl = core.get_officer_by_discord("1002", temp_db)
    cmd = core.get_officer_by_discord("1003", temp_db)

    # Attempt markup/format injection in field values
    malicious_data = {
        "recipient_name": "<script>alert(1)</script> & {__class__}",
        "award_class": "<b>Unclosed Bold & <font color='red'>Injected",
        "incident_date": "2026-10-31",
        "citation_narrative": "Normal narrative with XML chars < > & \" ' {issuer_name}",
    }
    draft = core.create_draft(cpl, "CM", malicious_data, temp_db)
    approved = core.approve_document(draft["id"], cmd, temp_db)
    pdf_b, png_b = render.render_document_bundle(approved)
    assert pdf_b.startswith(b"%PDF-")
    assert png_b.startswith(b"\x89PNG")


def test_api_security_and_bola(temp_db):
    _seed_officers(temp_db)
    client = TestClient(api.app)

    # Unauthenticated request -> 401
    assert client.get("/api/me").status_code == 401

    tok_ofc1 = api.create_jwt("1001")
    tok_pending = api.create_jwt("1005")
    tok_cmd = api.create_jwt("1003")

    # Pending officer gets 403 on active endpoints
    assert client.get("/api/templates", headers={"Authorization": f"Bearer {tok_pending}"}).status_code == 403

    # Officer 1 creates a draft via API
    sw_payload = {
        "template_code": "SW",
        "data": {
            "case_no": "26-CR-999",
            "target_subject": "Confidential Target",
            "target_premises": "999 Secret Ave",
            "statutes_violated": "PC 187",
            "items_to_seize": "Devices",
            "probable_cause": "Confidential informant statement.",
            "night_service": "Standard",
        },
    }
    res = client.post("/api/documents", json=sw_payload, headers={"Authorization": f"Bearer {tok_ofc1}"})
    assert res.status_code == 200
    doc_id = res.json()["id"]

    # Another regular Officer (not issuer, not supervisor for SW) cannot read Officer 1's DOJ warrant (BOLA check)
    with db.connect(temp_db) as conn:
        ofc_rank = conn.execute("SELECT id FROM ranks WHERE level = 4").fetchone()["id"]
        conn.execute(
            "INSERT INTO officers (discord_id, rp_name, badge, status, rank_id, is_admin) VALUES ('1099', 'Other Officer', '4099', 'active', ?, 0)",
            (ofc_rank,),
        )
    tok_other = api.create_jwt("1099")
    assert client.get(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {tok_other}"}).status_code == 403

    # Commander approves via API
    app_res = client.post(f"/api/documents/{doc_id}/approve", headers={"Authorization": f"Bearer {tok_cmd}"})
    assert app_res.status_code == 200
    ctrl = app_res.json()["control_no"]

    # Public verification endpoint returns metadata ONLY (never exposes confidential data_json)
    ver_res = client.get(f"/api/verify/{ctrl}")
    assert ver_res.status_code == 200
    ver_body = ver_res.json()
    assert ver_body["status"] == "APPROVED"
    assert "Confidential Target" not in json.dumps(ver_body)
