from datetime import datetime, timezone
import html
import json
import re
from typing import Any
import db

_VAR_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")

ROLE_ALIASES: dict[str, list[str]] = {
    "Chief of Police": ["1252386803265048667", "1271485363545706531"],
    "Assistant Chief": ["1252390507540381737"],
    "Deputy Chief": ["1379182875253014548", "1563702065279148112"],
    "Commander": ["1342957283943907489", "1501714073744572456", "1252390660556722226"],
    "Captain": ["1252390830912835724"],
    "Lieutenant I": ["1252390961296703518"],
    "Sergeant I": ["1252391045514133514"],
    "Corporal": ["1252391088614805564"],
    "CID": [
        "1271041562880512095",
        "1486538433668317345",
        "1486538562408157234",
        "1486538668142497905",
        "1486538731908501597",
    ],
    "Officer III": ["1468210226497978388", "1252391303799635998"],
    "Officer II": ["1468209961124368425"],
    "Officer I": ["1374873966971195432"],
    "Cadet": ["1320941964081758329", "1305691171783311411"],
}


def parse_nickname_badge_and_name(nick_or_name: str, fallback_id: str) -> tuple[str, str]:
    raw = str(nick_or_name or "").strip()
    m = re.match(r"^\s*#?(\d{1,5})\s*(?:\||-|·|—|/)\s*(.+)$", raw)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return str(fallback_id)[-4:], raw or "Officer"


def match_rank_for_role_ids(conn, role_ids: set[str]) -> dict[str, Any] | None:
    ranks = conn.execute("SELECT id, name, level, discord_role_id FROM ranks ORDER BY level DESC").fetchall()
    matched = []
    for rk in ranks:
        cand = set()
        if rk["discord_role_id"]:
            for part in re.split(r"[\s,;]+", str(rk["discord_role_id"]).strip()):
                if part:
                    cand.add(part)
        for alias_id in ROLE_ALIASES.get(rk["name"], []):
            cand.add(alias_id)
        if cand & role_ids:
            matched.append(dict(rk))
    if not matched:
        return None
    matched.sort(key=lambda r: (r["level"], 1 if r["name"].upper() == "CID" else 0), reverse=True)
    return matched[0]


def get_officer_by_discord(discord_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    with db.connect(db_path) as conn:
        row = conn.execute(
            """SELECT o.*, r.name AS rank_name, COALESCE(r.level, 0) AS rank_level
               FROM officers o
               LEFT JOIN ranks r ON r.id = o.rank_id
               WHERE o.discord_id = ?""",
            (str(discord_id),),
        ).fetchone()
        return db.row_to_dict(row)


def get_officer_by_id(officer_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    with db.connect(db_path) as conn:
        row = conn.execute(
            """SELECT o.*, r.name AS rank_name, COALESCE(r.level, 0) AS rank_level
               FROM officers o
               LEFT JOIN ranks r ON r.id = o.rank_id
               WHERE o.id = ?""",
            (officer_id,),
        ).fetchone()
        return db.row_to_dict(row)


def is_cid_officer(officer: dict[str, Any] | None) -> bool:
    if not officer:
        return False
    return str(officer.get("rank_name") or "").strip().upper() == "CID"


def can_issue(officer: dict[str, Any] | None, template: dict[str, Any]) -> bool:
    if not officer or officer.get("status") != "active" or not template.get("active", 1):
        return False
    if officer.get("is_admin"):
        return True
    if is_cid_officer(officer):
        return template.get("category") == "doj"
    return int(officer.get("rank_level") or 0) >= int(template["min_issue_level"])


def is_high_command(officer: dict[str, Any] | None) -> bool:
    if not officer or officer.get("status") != "active":
        return False
    if officer.get("is_admin"):
        return True
    if is_cid_officer(officer):
        return False
    return int(officer.get("rank_level") or 0) >= 11


def can_approve(officer: dict[str, Any] | None, doc: dict[str, Any]) -> bool:
    if not officer or officer.get("status") != "active":
        return False
    is_self = int(officer["id"]) == int(doc["issuer_id"])
    if is_self and not is_high_command(officer):
        return False  # Self-approval proibido para patentes regulares; High Command pode se autoaprovar
    snap = json.loads(doc["template_snapshot"]) if isinstance(doc["template_snapshot"], str) else doc["template_snapshot"]
    if officer.get("is_admin"):
        return True
    if is_cid_officer(officer):
        return False
    return int(officer.get("rank_level") or 0) >= int(snap["min_approve_level"])


def can_view_document(officer: dict[str, Any] | None, doc: dict[str, Any]) -> bool:
    if not officer or officer.get("status") != "active":
        return False
    if officer.get("is_admin"):
        return True
    snap = json.loads(doc["template_snapshot"]) if isinstance(doc["template_snapshot"], str) else doc["template_snapshot"]
    if is_cid_officer(officer) and snap.get("category") != "doj":
        return False
    if int(officer["id"]) in (int(doc["issuer_id"]), int(doc.get("approver_id") or -1)):
        return True
    return int(officer.get("rank_level") or 0) >= int(snap["min_approve_level"])


def validate_fields(template: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    fields = json.loads(template["fields_json"]) if isinstance(template["fields_json"], str) else template["fields_json"]
    cleaned: dict[str, str] = {}
    for f in fields:
        key = f["key"]
        val = str(data.get(key, "") or "").strip()
        if f.get("required", True) and not val:
            raise ValueError(f"Missing required field: {f['label']} ({key})")
        max_len = int(f.get("max_length", 4000))
        if len(val) > max_len:
            raise ValueError(f"Field '{f['label']}' exceeds maximum length of {max_len} characters")
        cleaned[key] = val
    if "_lang" in data:
        cleaned["_lang"] = str(data["_lang"]).lower().strip()
    return cleaned


def fill_template_body(body: str, variables: dict[str, Any]) -> str:
    """Safely replace {var} placeholders with XML-escaped values (prevents ReportLab markup/attribute injection)."""
    def _repl(match: re.Match[str]) -> str:
        k = match.group(1)
        raw = str(variables.get(k, f"[{k}]"))
        return html.escape(raw, quote=True)

    return _VAR_RE.sub(_repl, body)


def next_control_no(conn, code: str, year: int | None = None) -> str:
    yr = year or datetime.now(timezone.utc).year
    prefix = f"UPD-{code.upper()}-{yr}-"
    row = conn.execute(
        "SELECT control_no FROM documents WHERE control_no LIKE ? ORDER BY control_no DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    if row and row["control_no"]:
        try:
            seq = int(row["control_no"].rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def create_draft(
    officer: dict[str, Any],
    template_code: str,
    data: dict[str, Any],
    db_path: str | None = None,
) -> dict[str, Any]:
    with db.connect(db_path) as conn:
        t_row = conn.execute("SELECT * FROM templates WHERE code = ?", (template_code.upper(),)).fetchone()
        if not t_row:
            raise ValueError(f"Template '{template_code}' not found")
        template = db.row_to_dict(t_row)
        if not can_issue(officer, template):
            raise PermissionError("Officer lacks permission or active status to issue this document")
        cleaned = validate_fields(template, data)
        snap = {
            "code": template["code"],
            "name": template["name"],
            "category": template["category"],
            "min_issue_level": template["min_issue_level"],
            "min_approve_level": template["min_approve_level"],
            "title": template["title"],
            "court_header": template["court_header"],
            "body": template["body"],
            "fields": json.loads(template["fields_json"]),
            "version": template["version"],
        }
        cur = conn.execute(
            """INSERT INTO documents (template_code, template_snapshot, data_json, issuer_id, status)
               VALUES (?, ?, ?, ?, 'PENDING')""",
            (
                template["code"],
                json.dumps(snap, ensure_ascii=False),
                json.dumps(cleaned, ensure_ascii=False),
                officer["id"],
            ),
        )
        doc_id = cur.lastrowid
        conn.execute(
            "INSERT INTO audit_log (actor_id, action, target, detail) VALUES (?, 'CREATE_DRAFT', ?, ?)",
            (officer["id"], f"doc:{doc_id}", template["code"]),
        )
    return get_document_full(doc_id, db_path)


def approve_document(
    doc_id: int,
    approver: dict[str, Any],
    db_path: str | None = None,
) -> dict[str, Any]:
    with db.connect(db_path) as conn:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not row:
                raise ValueError("Document not found")
            doc = db.row_to_dict(row)
            if doc["status"] != "PENDING":
                raise ValueError(f"Document cannot be approved from status '{doc['status']}'")
            if not can_approve(approver, doc):
                raise PermissionError("Approver lacks required rank or cannot self-approve")
            ctrl = next_control_no(conn, doc["template_code"])
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.execute(
                """UPDATE documents
                   SET control_no = ?, approver_id = ?, status = 'APPROVED', approved_at = ?, reject_reason = NULL
                   WHERE id = ?""",
                (ctrl, approver["id"], now, doc_id),
            )
            conn.execute(
                "INSERT INTO audit_log (actor_id, action, target, detail) VALUES (?, 'APPROVE', ?, ?)",
                (approver["id"], f"doc:{doc_id}", ctrl),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return get_document_full(doc_id, db_path)


def reject_document(
    doc_id: int,
    approver: dict[str, Any],
    reason: str,
    db_path: str | None = None,
) -> dict[str, Any]:
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Rejection reason is required")
    with db.connect(db_path) as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            raise ValueError("Document not found")
        doc = db.row_to_dict(row)
        if doc["status"] != "PENDING":
            raise ValueError(f"Document cannot be rejected from status '{doc['status']}'")
        if not can_approve(approver, doc):
            raise PermissionError("Approver lacks required rank or cannot self-reject")
        conn.execute(
            "UPDATE documents SET approver_id = ?, status = 'REJECTED', reject_reason = ? WHERE id = ?",
            (approver["id"], reason[:1000], doc_id),
        )
        conn.execute(
            "INSERT INTO audit_log (actor_id, action, target, detail) VALUES (?, 'REJECT', ?, ?)",
            (approver["id"], f"doc:{doc_id}", reason[:200]),
        )
    return get_document_full(doc_id, db_path)


def revoke_document(
    control_no_or_id: str | int,
    admin_officer: dict[str, Any],
    reason: str,
    db_path: str | None = None,
) -> dict[str, Any]:
    if not admin_officer or not admin_officer.get("is_admin"):
        raise PermissionError("Only system administrators can revoke approved documents")
    with db.connect(db_path) as conn:
        if isinstance(control_no_or_id, int) or str(control_no_or_id).isdigit():
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (int(control_no_or_id),)).fetchone()
        else:
            row = conn.execute("SELECT * FROM documents WHERE control_no = ?", (str(control_no_or_id).upper(),)).fetchone()
        if not row:
            raise ValueError("Document not found")
        doc = db.row_to_dict(row)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "UPDATE documents SET status = 'REVOKED', revoked_at = ?, reject_reason = ? WHERE id = ?",
            (now, (reason or "Revoked by Command Staff")[:500], doc["id"]),
        )
        conn.execute(
            "INSERT INTO audit_log (actor_id, action, target, detail) VALUES (?, 'REVOKE', ?, ?)",
            (admin_officer["id"], f"doc:{doc['id']}", reason[:200]),
        )
    return get_document_full(doc["id"], db_path)


def get_document_full(doc_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    with db.connect(db_path) as conn:
        row = conn.execute(
            """SELECT d.*,
                      i.rp_name AS issuer_name, i.badge AS issuer_badge, i.division AS issuer_division,
                       COALESCE(ir.name, 'Officer') AS issuer_rank,
                      i.discord_id AS issuer_discord_id,
                      a.rp_name AS approver_name, a.badge AS approver_badge, a.division AS approver_division,
                      COALESCE(ar.name, 'Command Staff') AS approver_rank,
                      a.discord_id AS approver_discord_id
               FROM documents d
               JOIN officers i ON i.id = d.issuer_id
               LEFT JOIN ranks ir ON ir.id = i.rank_id
               LEFT JOIN officers a ON a.id = d.approver_id
               LEFT JOIN ranks ar ON ar.id = a.rank_id
               WHERE d.id = ?""",
            (doc_id,),
        ).fetchone()
        return db.row_to_dict(row)
