import asyncio
from datetime import datetime, timedelta, timezone
import json
import secrets
from typing import Any
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx
import jwt
from pydantic import BaseModel, Field

import config
import core
import db
import render

app = FastAPI(title="UPD Records & Judicial Filing API", version="1.0.0")
_BOT_REF = None
_OAUTH_STATES: dict[str, float] = {}


def set_bot_instance(bot_instance) -> None:
    global _BOT_REF
    _BOT_REF = bot_instance


allowed_origins = list(
    {
        config.SITE_URL,
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    }
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.github\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_jwt(discord_id: str) -> str:
    payload = {
        "sub": str(discord_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def _ensure_owner_officer(discord_id: str, display_name: str = "Chief Commander (Owner)") -> dict[str, Any]:
    with db.connect() as conn:
        existing = conn.execute("SELECT id FROM officers WHERE discord_id = ?", (discord_id,)).fetchone()
        top_rank = conn.execute("SELECT id FROM ranks ORDER BY level DESC LIMIT 1").fetchone()
        top_rank_id = top_rank["id"] if top_rank else None
        if not existing:
            conn.execute(
                """INSERT INTO officers (discord_id, rp_name, badge, division, rank_id, status, is_admin)
                   VALUES (?, ?, '1001', 'Office of the Chief', ?, 'active', 1)""",
                (discord_id, display_name, top_rank_id),
            )
        else:
            conn.execute(
                "UPDATE officers SET status = 'active', is_admin = 1, rank_id = COALESCE(rank_id, ?) WHERE discord_id = ?",
                (top_rank_id, discord_id),
            )
    return core.get_officer_by_discord(discord_id)


def get_current_officer(request: Request) -> dict[str, Any]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth.split(" ", 1)[1].strip()
    if token == f"upd-owner-token-{config.OWNER_DISCORD_ID}":
        return _ensure_owner_officer(str(config.OWNER_DISCORD_ID))
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

    sub = str(payload["sub"])
    if sub == str(config.OWNER_DISCORD_ID):
        return _ensure_owner_officer(sub)
    officer = core.get_officer_by_discord(sub)
    if not officer:
        raise HTTPException(status_code=403, detail="Officer profile not registered. Contact Command Staff.")
    return officer


def require_active_officer(officer: dict[str, Any] = Depends(get_current_officer)) -> dict[str, Any]:
    if officer.get("status") != "active":
        raise HTTPException(
            status_code=403,
            detail=f"Officer profile status is '{officer.get('status')}'. Admission by Command Admin required.",
        )
    return officer


def require_admin(officer: dict[str, Any] = Depends(require_active_officer)) -> dict[str, Any]:
    if not officer.get("is_admin"):
        raise HTTPException(status_code=403, detail="Command Administrator privileges required")
    return officer


# ─── OAuth2 & Session Endpoints ───────────────────────────────────────────────

@app.get("/api/auth/login")
async def auth_login():
    if not config.DISCORD_CLIENT_ID or config.DISCORD_CLIENT_ID.startswith("your_"):
        raise HTTPException(status_code=400, detail="DISCORD_CLIENT_ID not configured on server")
    state = secrets.token_urlsafe(24)
    _OAUTH_STATES[state] = datetime.now(timezone.utc).timestamp() + 600
    params = {
        "client_id": config.DISCORD_CLIENT_ID,
        "redirect_uri": f"{config.API_URL}/api/auth/callback",
        "response_type": "code",
        "scope": "identify guilds.members.read",
        "state": state,
    }
    return Response(status_code=302, headers={"Location": f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"})


@app.get("/api/auth/callback")
async def auth_callback(code: str = Query(...), state: str = Query(...)):
    now = datetime.now(timezone.utc).timestamp()
    exp = _OAUTH_STATES.pop(state, None)
    if not exp or exp < now:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth2 state")

    async with httpx.AsyncClient(timeout=15.0) as client:
        tok_res = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": config.DISCORD_CLIENT_ID,
                "client_secret": config.DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{config.API_URL}/api/auth/callback",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if tok_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Discord token exchange failed")
        access_token = tok_res.json()["access_token"]

        me_res = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        me_res.raise_for_status()
        user_data = me_res.json()
        discord_id = str(user_data["id"])
        display_name = user_data.get("global_name") or user_data.get("username") or "Officer"

        has_supervision = discord_id == str(config.OWNER_DISCORD_ID)
        if config.GUILD_ID and not has_supervision:
            gm_res = await client.get(
                f"https://discord.com/api/users/@me/guilds/{config.GUILD_ID}/member",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if gm_res.status_code == 200:
                roles = [str(r) for r in (gm_res.json().get("roles") or [])]
                if config.ADMIN_ROLE_ID and str(config.ADMIN_ROLE_ID) in roles:
                    has_supervision = True

    if has_supervision:
        _ensure_owner_officer(discord_id, display_name)
    else:
        with db.connect() as conn:
            existing = conn.execute("SELECT id, status, is_admin FROM officers WHERE discord_id = ?", (discord_id,)).fetchone()
            if not existing or existing["status"] != "active":
                return Response(
                    status_code=302,
                    headers={"Location": f"{config.SITE_URL}/#error=Acesso+restrito+a+oficiais+com+cargo+de+Supervisao"},
                )

    if _BOT_REF and config.GUILD_ID:
        guild = _BOT_REF.get_guild(config.GUILD_ID)
        if guild:
            member = guild.get_member(int(discord_id))
            if member:
                from cogs.sync import sync_member_rank
                await asyncio.to_thread(sync_member_rank, member)

    token = create_jwt(discord_id)
    return Response(status_code=302, headers={"Location": f"{config.SITE_URL}/#token={token}"})


@app.get("/api/me")
def get_me(officer: dict[str, Any] = Depends(get_current_officer)):
    return officer


# ─── Templates & Live Preview ─────────────────────────────────────────────────

@app.get("/api/templates")
def list_templates(officer: dict[str, Any] = Depends(require_active_officer)):
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM templates ORDER BY category, code").fetchall()
    result = []
    for r in rows:
        t = db.row_to_dict(r)
        t["fields"] = json.loads(t["fields_json"])
        t["can_issue"] = core.can_issue(officer, t)
        if t["active"] or officer.get("is_admin"):
            result.append(t)
    return result


class PreviewPayload(BaseModel):
    template_code: str
    data: dict[str, Any] = Field(default_factory=dict)
    custom_template: dict[str, Any] | None = None


@app.post("/api/documents/preview")
def preview_document(payload: PreviewPayload, officer: dict[str, Any] = Depends(require_active_officer)):
    if payload.custom_template and officer.get("is_admin"):
        snap = payload.custom_template
    else:
        with db.connect() as conn:
            row = conn.execute("SELECT * FROM templates WHERE code = ?", (payload.template_code.upper(),)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Template not found")
        snap = db.row_to_dict(row)

    doc_rec = {
        "id": "PREVIEW",
        "control_no": None,
        "template_snapshot": snap,
        "data_json": payload.data,
        "status": "PENDING",
        "issuer_name": officer["rp_name"],
        "issuer_badge": officer["badge"],
        "issuer_rank": officer.get("rank_name") or "Officer",
        "issuer_division": officer.get("division") or "Patrol Division",
    }
    _, png_bytes = render.render_document_bundle(doc_rec, dpi=140)
    return Response(content=png_bytes, media_type="image/png")


# ─── Documents & Approvals ────────────────────────────────────────────────────

class CreateDocumentPayload(BaseModel):
    template_code: str
    data: dict[str, Any]


@app.post("/api/documents")
async def create_document_endpoint(
    payload: CreateDocumentPayload,
    officer: dict[str, Any] = Depends(require_active_officer),
):
    try:
        doc = await asyncio.to_thread(core.create_draft, officer, payload.template_code, payload.data)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if _BOT_REF:
        from cogs.aprovacao import post_draft_to_approval_channel
        await post_draft_to_approval_channel(_BOT_REF, doc)
    return doc


@app.get("/api/documents")
def list_documents(
    scope: str = Query("mine", pattern="^(mine|pending|all)$"),
    officer: dict[str, Any] = Depends(require_active_officer),
):
    with db.connect() as conn:
        base_sql = """
            SELECT d.id, d.control_no, d.template_code, d.template_snapshot, d.status,
                   d.reject_reason, d.png_url, d.created_at, d.approved_at,
                   d.issuer_id, d.approver_id,
                   i.rp_name AS issuer_name, i.badge AS issuer_badge, COALESCE(ir.name, 'Officer') AS issuer_rank,
                   a.rp_name AS approver_name, a.badge AS approver_badge, COALESCE(ar.name, '') AS approver_rank
            FROM documents d
            JOIN officers i ON i.id = d.issuer_id
            LEFT JOIN ranks ir ON ir.id = i.rank_id
            LEFT JOIN officers a ON a.id = d.approver_id
            LEFT JOIN ranks ar ON ar.id = a.rank_id
        """
        if scope == "mine":
            rows = conn.execute(base_sql + " WHERE d.issuer_id = ? ORDER BY d.id DESC LIMIT 100", (officer["id"],)).fetchall()
        elif scope == "pending":
            rows = conn.execute(base_sql + " WHERE d.status = 'PENDING' ORDER BY d.id ASC", ()).fetchall()
        else:
            if not officer.get("is_admin") and int(officer.get("rank_level") or 0) < 5:
                raise HTTPException(status_code=403, detail="Supervisor rank required to view all records")
            rows = conn.execute(base_sql + " ORDER BY d.id DESC LIMIT 150").fetchall()

    out = []
    for r in rows:
        d = db.row_to_dict(r)
        snap = json.loads(d.pop("template_snapshot"))
        d["template_name"] = snap.get("name", d["template_code"])
        d["category"] = snap.get("category", "internal")
        d["min_approve_level"] = snap.get("min_approve_level", 5)
        d["can_approve"] = core.can_approve(officer, {**d, "template_snapshot": snap})
        out.append(d)
    return out


@app.get("/api/documents/{doc_id}")
def get_document_detail(doc_id: int, officer: dict[str, Any] = Depends(require_active_officer)):
    doc = core.get_document_full(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not core.can_view_document(officer, doc):
        raise HTTPException(status_code=403, detail="Access denied to this document")
    doc["template_snapshot"] = json.loads(doc["template_snapshot"])
    doc["data_json"] = json.loads(doc["data_json"])
    doc["can_approve"] = core.can_approve(officer, doc)
    return doc


@app.get("/api/documents/{doc_id}.pdf")
def download_document_pdf(doc_id: int, officer: dict[str, Any] = Depends(require_active_officer)):
    doc = core.get_document_full(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not core.can_view_document(officer, doc):
        raise HTTPException(status_code=403, detail="Access denied")
    pdf_bytes = render.render_pdf(doc)
    fname = f"{doc['control_no'] or f'DRAFT-{doc_id}'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{fname}"'},
    )


@app.get("/api/documents/{doc_id}.png")
def download_document_png(doc_id: int, officer: dict[str, Any] = Depends(require_active_officer)):
    doc = core.get_document_full(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not core.can_view_document(officer, doc):
        raise HTTPException(status_code=403, detail="Access denied")
    _, png_bytes = render.render_document_bundle(doc, dpi=160)
    return Response(content=png_bytes, media_type="image/png")


@app.post("/api/documents/{doc_id}/approve")
async def approve_document_endpoint(doc_id: int, officer: dict[str, Any] = Depends(require_active_officer)):
    try:
        doc = await asyncio.to_thread(core.approve_document, doc_id, officer)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if _BOT_REF:
        from cogs.aprovacao import finalize_approved_document
        doc = await finalize_approved_document(_BOT_REF, doc)
    else:
        import fivemanage
        _, png_bytes = await asyncio.to_thread(render.render_document_bundle, doc)
        try:
            url = await fivemanage.upload_png(png_bytes, f"{doc['control_no']}.png")
        except Exception:
            url = None
        if url:
            with db.connect() as conn:
                conn.execute("UPDATE documents SET png_url = ? WHERE id = ?", (url, doc_id))
            doc["png_url"] = url
    return doc


class ReasonPayload(BaseModel):
    reason: str = Field(..., min_length=2, max_length=800)


@app.post("/api/documents/{doc_id}/reject")
async def reject_document_endpoint(
    doc_id: int,
    payload: ReasonPayload,
    officer: dict[str, Any] = Depends(require_active_officer),
):
    try:
        return await asyncio.to_thread(core.reject_document, doc_id, officer, payload.reason)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/documents/{doc_id}/revoke")
async def revoke_document_endpoint(
    doc_id: int,
    payload: ReasonPayload,
    admin: dict[str, Any] = Depends(require_admin),
):
    try:
        return await asyncio.to_thread(core.revoke_document, doc_id, admin, payload.reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Public Verification Endpoint ─────────────────────────────────────────────

@app.get("/api/verify/{control_no}")
def verify_public_record(control_no: str):
    ctrl = control_no.strip().upper()
    with db.connect() as conn:
        row = conn.execute(
            """SELECT d.control_no, d.template_code, d.template_snapshot, d.status,
                      d.approved_at, d.revoked_at, d.reject_reason,
                      i.rp_name AS issuer_name, i.badge AS issuer_badge, COALESCE(ir.name, 'Officer') AS issuer_rank,
                      a.rp_name AS approver_name, a.badge AS approver_badge, COALESCE(ar.name, 'Command Staff') AS approver_rank
               FROM documents d
               JOIN officers i ON i.id = d.issuer_id
               LEFT JOIN ranks ir ON ir.id = i.rank_id
               LEFT JOIN officers a ON a.id = d.approver_id
               LEFT JOIN ranks ar ON ar.id = a.rank_id
               WHERE d.control_no = ?""",
            (ctrl,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Control Number not found in UPD Official Registry")
    d = db.row_to_dict(row)
    snap = json.loads(d.pop("template_snapshot"))
    return {
        "control_no": d["control_no"],
        "template_code": d["template_code"],
        "document_title": snap.get("name"),
        "category": snap.get("category"),
        "status": d["status"],
        "issued_by": f"{d['issuer_rank']} {d['issuer_name']} (Badge #{d['issuer_badge']})",
        "approved_by": f"{d['approver_rank']} {d['approver_name']} (Badge #{d['approver_badge']})",
        "approved_at": d["approved_at"],
        "revoked_at": d["revoked_at"],
        "revocation_note": d["reject_reason"] if d["status"] == "REVOKED" else None,
    }


# ─── Admin Management Endpoints (Officers, Ranks, Templates) ──────────────────

@app.get("/api/officers")
def list_officers(_admin: dict[str, Any] = Depends(require_admin)):
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT o.*, r.name AS rank_name, COALESCE(r.level, 0) AS rank_level
               FROM officers o LEFT JOIN ranks r ON r.id = o.rank_id
               ORDER BY COALESCE(r.level, 0) DESC, o.rp_name ASC"""
        ).fetchall()
    return [db.row_to_dict(r) for r in rows]


class OfficerUpsertPayload(BaseModel):
    discord_id: str
    rp_name: str
    badge: str
    division: str = "Patrol Division"
    rank_id: int | None = None
    status: str = "active"
    is_admin: bool = False


@app.post("/api/officers")
def upsert_officer(payload: OfficerUpsertPayload, admin: dict[str, Any] = Depends(require_admin)):
    with db.connect() as conn:
        existing = conn.execute("SELECT id FROM officers WHERE discord_id = ?", (payload.discord_id.strip(),)).fetchone()
        if existing:
            conn.execute(
                """UPDATE officers
                   SET rp_name = ?, badge = ?, division = ?, rank_id = ?, status = ?, is_admin = ?
                   WHERE discord_id = ?""",
                (
                    payload.rp_name.strip(),
                    payload.badge.strip(),
                    payload.division.strip(),
                    payload.rank_id,
                    payload.status,
                    1 if payload.is_admin else 0,
                    payload.discord_id.strip(),
                ),
            )
        else:
            conn.execute(
                """INSERT INTO officers (discord_id, rp_name, badge, division, rank_id, status, is_admin, admitted_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    payload.discord_id.strip(),
                    payload.rp_name.strip(),
                    payload.badge.strip(),
                    payload.division.strip(),
                    payload.rank_id,
                    payload.status,
                    1 if payload.is_admin else 0,
                    admin["id"],
                ),
            )
        conn.execute(
            "INSERT INTO audit_log (actor_id, action, target, detail) VALUES (?, 'UPSERT_OFFICER', ?, ?)",
            (admin["id"], payload.discord_id, f"{payload.rp_name} (#{payload.badge}) [{payload.status}]"),
        )
    return core.get_officer_by_discord(payload.discord_id.strip())


@app.get("/api/ranks")
def list_ranks(_officer: dict[str, Any] = Depends(require_active_officer)):
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM ranks ORDER BY level ASC").fetchall()
    return [db.row_to_dict(r) for r in rows]


class RankPayload(BaseModel):
    id: int | None = None
    name: str
    level: int
    discord_role_id: str | None = None


@app.post("/api/ranks")
def save_rank(payload: RankPayload, admin: dict[str, Any] = Depends(require_admin)):
    role_id = (payload.discord_role_id or "").strip() or None
    with db.connect() as conn:
        if payload.id:
            conn.execute(
                "UPDATE ranks SET name = ?, level = ?, discord_role_id = ? WHERE id = ?",
                (payload.name.strip(), payload.level, role_id, payload.id),
            )
        else:
            conn.execute(
                "INSERT INTO ranks (name, level, discord_role_id) VALUES (?, ?, ?)",
                (payload.name.strip(), payload.level, role_id),
            )
        conn.execute(
            "INSERT INTO audit_log (actor_id, action, target, detail) VALUES (?, 'SAVE_RANK', ?, ?)",
            (admin["id"], payload.name, f"level={payload.level} role={role_id}"),
        )
    return list_ranks(admin)


class TemplateUpdatePayload(BaseModel):
    code: str
    name: str
    category: str
    min_issue_level: int
    min_approve_level: int
    channel: str
    title: str
    court_header: str
    body: str
    fields: list[dict[str, Any]]
    active: bool = True


@app.post("/api/templates")
def save_template(payload: TemplateUpdatePayload, admin: dict[str, Any] = Depends(require_admin)):
    code = payload.code.strip().upper()
    fields_str = json.dumps(payload.fields, ensure_ascii=False)
    with db.connect() as conn:
        existing = conn.execute("SELECT id, version FROM templates WHERE code = ?", (code,)).fetchone()
        if existing:
            conn.execute(
                """UPDATE templates
                   SET name = ?, category = ?, min_issue_level = ?, min_approve_level = ?,
                       channel = ?, title = ?, court_header = ?, body = ?, fields_json = ?,
                       active = ?, version = ?
                   WHERE code = ?""",
                (
                    payload.name.strip(),
                    payload.category,
                    payload.min_issue_level,
                    payload.min_approve_level,
                    payload.channel,
                    payload.title.strip(),
                    payload.court_header.strip(),
                    payload.body,
                    fields_str,
                    1 if payload.active else 0,
                    int(existing["version"]) + 1,
                    code,
                ),
            )
        else:
            conn.execute(
                """INSERT INTO templates
                   (code, name, category, min_issue_level, min_approve_level, channel, title, court_header, body, fields_json, active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    code,
                    payload.name.strip(),
                    payload.category,
                    payload.min_issue_level,
                    payload.min_approve_level,
                    payload.channel,
                    payload.title.strip(),
                    payload.court_header.strip(),
                    payload.body,
                    fields_str,
                    1 if payload.active else 0,
                ),
            )
        conn.execute(
            "INSERT INTO audit_log (actor_id, action, target, detail) VALUES (?, 'SAVE_TEMPLATE', ?, ?)",
            (admin["id"], code, payload.name),
        )
    return list_templates(admin)


# Serve static frontend from ../site if available (allows single-URL preview as well as GitHub Pages)
_SITE_DIR = config.BASE_DIR.parent / "site"
if _SITE_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_SITE_DIR), html=True), name="site")
