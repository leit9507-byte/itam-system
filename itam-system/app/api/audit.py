from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.models.asset import Asset
from app.models.audit_response import AuditResponse
from app.models.audit_rule import AuditRule
from app.reports.generator import AuditReportGenerator
from app.services.audit_engine import AuditEngine
from app.services.asset_service import AssetService
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditRunRequest(BaseModel):
    users: list[dict] = []
    notify: bool = False


class AuditRulePayload(BaseModel):
    rule_code: str
    name: str
    severity: str = "medium"
    enabled: bool = True
    scope_category: str | None = None
    threshold_value: float | None = None
    threshold_days: int | None = None


class AuditResponsePayload(BaseModel):
    violation_key: str
    asset_id: str | None = None
    rule_code: str
    audit_scope: str = "asset"
    decision: str = "pending"
    reason: str | None = None
    responder: str | None = None


last_report_path: str | None = None
last_report_pdf_path: str | None = None


def default_rules() -> list[dict]:
    settings = get_settings()
    return [
        {
            "rule_code": "USER_ASSET_COUNT_LIMIT",
            "name": "人员资产数量超配",
            "severity": "medium",
            "enabled": True,
            "scope_category": "",
            "threshold_value": float(settings.max_assets_per_user),
            "threshold_days": None,
            "audit_scope": "person",
            "description": "按责任人统计名下资产数量，可限定某一设备类型。",
        },
        {
            "rule_code": "OFFBOARDING_ASSET_NOT_RETURNED",
            "name": "离职人员资产未回收",
            "severity": "high",
            "enabled": True,
            "scope_category": "",
            "threshold_value": None,
            "threshold_days": None,
            "audit_scope": "person",
            "description": "责任人已离职、停用或禁用，但资产仍在用、借出或出库时命中。",
        },
        {
            "rule_code": "BORROWED_ASSET_NOT_RETURNED",
            "name": "借用资产超期未回收",
            "severity": "medium",
            "enabled": True,
            "scope_category": "",
            "threshold_value": None,
            "threshold_days": 30,
            "audit_scope": "person",
            "description": "资产处于借出状态超过指定天数仍未回收时命中。",
        },
        {
            "rule_code": "SINGLE_OWNER_VALUE_LIMIT",
            "name": "人员名下资产价值超标",
            "severity": "high",
            "enabled": True,
            "scope_category": "",
            "threshold_value": float(settings.high_value_threshold * 2),
            "threshold_days": None,
            "audit_scope": "person",
            "description": "按责任人统计名下资产总价值，超过阈值时命中。",
        },
        {
            "rule_code": "HIGH_VALUE_PURCHASE",
            "name": "超价值采购",
            "severity": "high",
            "enabled": True,
            "scope_category": "",
            "threshold_value": float(settings.high_value_threshold),
            "threshold_days": None,
            "audit_scope": "asset",
            "description": "资产采购原值超过规则阈值时命中，用于复核审批和采购合理性。",
        },
        {
            "rule_code": "ASSET_IDLE_OVER_90_DAYS",
            "name": "长期闲置",
            "severity": "medium",
            "enabled": True,
            "scope_category": "",
            "threshold_value": None,
            "threshold_days": settings.idle_days_threshold,
            "audit_scope": "asset",
            "description": "库存中或闲置资产超过指定天数后命中。",
        },
        {
            "rule_code": "ASSET_RETIREMENT_OVERDUE",
            "name": "超期服役审计",
            "severity": "medium",
            "enabled": True,
            "scope_category": "",
            "threshold_value": None,
            "threshold_days": 0,
            "audit_scope": "asset",
            "description": "资产仍在使用、借出、出库或维修中，且已超过采购日期加退役年限后的预计退役日时命中。",
        },
        {
            "rule_code": "DEVICE_FAULT_AUDIT",
            "name": "设备故障审计",
            "severity": "medium",
            "enabled": True,
            "scope_category": "",
            "threshold_value": 2,
            "threshold_days": 180,
            "audit_scope": "asset",
            "description": "按设备统计指定时间内维修次数，并识别未修好、在保送修等故障风险。",
        },
    ]


def serialize_rule(rule: AuditRule, fallback: dict | None = None) -> dict:
    fallback = fallback or {}
    return {
        "id": rule.id,
        "rule_code": rule.rule_code,
        "name": rule.name or fallback.get("name") or rule.rule_code,
        "severity": rule.severity,
        "enabled": rule.enabled,
        "scope_category": rule.scope_category or "",
        "threshold_value": rule.threshold_value,
        "threshold_days": rule.threshold_days,
        "audit_scope": fallback.get("audit_scope") or infer_rule_scope(rule.rule_code),
        "description": fallback.get("description", ""),
    }


def infer_rule_scope(rule_code: str) -> str:
    if rule_code.startswith("CUSTOM_PERSON_COUNT_"):
        return "person"
    defaults = {item["rule_code"]: item for item in default_rules()}
    return defaults.get(rule_code, {}).get("audit_scope", "asset")


def custom_rule_fallback(rule: AuditRule) -> dict:
    if rule.rule_code.startswith("CUSTOM_PERSON_COUNT_"):
        return {
            "audit_scope": "person",
            "description": "按责任人统计全部设备类型或多个指定设备类型的资产数量，超过阈值时命中。",
        }
    return {"audit_scope": infer_rule_scope(rule.rule_code)}


def serialize_response(row: AuditResponse) -> dict:
    return {
        "id": row.id,
        "violation_key": row.violation_key,
        "asset_id": row.asset_id,
        "rule_code": row.rule_code,
        "audit_scope": row.audit_scope,
        "decision": row.decision,
        "reason": row.reason or "",
        "responder": row.responder or "",
        "updated_at": row.updated_at,
        "created_at": row.created_at,
    }


@router.get("/rules")
def list_audit_rules(db: Session = Depends(get_db)):
    persisted = {item.rule_code: item for item in db.query(AuditRule).all()}
    rows = []
    changed = False
    for item in default_rules():
        saved = persisted.get(item["rule_code"])
        if saved:
            if saved.name != item["name"]:
                saved.name = item["name"]
                changed = True
            rows.append(serialize_rule(saved, item))
        else:
            rows.append(item)
    default_codes = {item["rule_code"] for item in default_rules()}
    custom_rows = [
        serialize_rule(item, custom_rule_fallback(item))
        for item in persisted.values()
        if item.rule_code not in default_codes
    ]
    rows.extend(sorted(custom_rows, key=lambda item: item["id"] or 0))
    if changed:
        db.commit()
    return rows


@router.post("/rules")
def save_audit_rules(payload: list[AuditRulePayload], db: Session = Depends(get_db)):
    defaults = {item["rule_code"]: item for item in default_rules()}
    for item in payload:
        rule = db.query(AuditRule).filter(AuditRule.rule_code == item.rule_code).first()
        if not rule:
            rule = AuditRule(rule_code=item.rule_code)
            db.add(rule)
        rule.name = defaults.get(item.rule_code, {}).get("name", item.name)
        rule.severity = item.severity
        rule.enabled = item.enabled
        rule.scope_category = item.scope_category or ""
        rule.threshold_value = item.threshold_value
        rule.threshold_days = item.threshold_days
    db.commit()
    return list_audit_rules(db)


@router.get("/responses")
def list_audit_responses(request: Request, db: Session = Depends(get_db)):
    asset_ids = AssetService.apply_data_scope(db.query(Asset), user_context_from_request(request)).with_entities(Asset.asset_id)
    rows = db.query(AuditResponse).filter(AuditResponse.asset_id.in_(asset_ids)).order_by(AuditResponse.updated_at.desc()).all()
    return [serialize_response(row) for row in rows]


@router.post("/responses")
def save_audit_response(payload: AuditResponsePayload, request: Request, db: Session = Depends(get_db)):
    if not payload.asset_id:
        raise HTTPException(status_code=400, detail="asset_id is required for scoped audit responses")
    try:
        AssetService.get_scoped_asset(db, payload.asset_id, user_context_from_request(request))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="asset not found") from exc
    row = db.query(AuditResponse).filter(AuditResponse.violation_key == payload.violation_key).first()
    if not row:
        row = AuditResponse(violation_key=payload.violation_key)
        db.add(row)
    row.asset_id = payload.asset_id
    row.rule_code = payload.rule_code
    row.audit_scope = payload.audit_scope
    row.decision = payload.decision
    row.reason = payload.reason or ""
    row.responder = operator_from_request(request)
    db.commit()
    db.refresh(row)
    return serialize_response(row)


@router.post("/run")
def run_audit(request: Request, payload: AuditRunRequest | None = None, db: Session = Depends(get_db)):
    global last_report_path, last_report_pdf_path
    asset_ids = set(
        row[0]
        for row in AssetService.apply_data_scope(db.query(Asset), user_context_from_request(request)).with_entities(Asset.asset_id).all()
    )
    result = AuditEngine(db).run(users=payload.users if payload else [], asset_ids=asset_ids)
    last_report_path = AuditReportGenerator().generate(result)
    last_report_pdf_path = None
    violations = result.get("violations") or []
    if payload and payload.notify and violations:
        summary = result.get("audit_summary") or {}
        NotificationService.send_event(
            db,
            "risk",
            "审计发现风险",
            [
                f"风险总数：{len(violations)} 条",
                f"风险评分：{result.get('risk_score', 0)}",
                f"人员风险：{summary.get('person', 0)} 条",
                f"资产风险：{summary.get('asset', 0)} 条",
                f"高风险：{len([item for item in violations if item.get('severity') == 'high'])} 条",
                "处理建议：请进入审计中心查看明细并分派整改",
                f"审计时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            ],
        )
    return result


@router.get("/report")
def get_audit_report(db: Session = Depends(get_db)):
    global last_report_path
    if not last_report_path:
        result = AuditEngine(db).run()
        last_report_path = AuditReportGenerator().generate(result)
    return FileResponse(last_report_path, media_type="text/html", filename="audit_report.html")


@router.get("/report.pdf")
def get_audit_report_pdf(db: Session = Depends(get_db)):
    global last_report_pdf_path
    if not last_report_pdf_path or not Path(last_report_pdf_path).exists():
        result = AuditEngine(db).run()
        last_report_pdf_path = generate_audit_pdf(result)
    return FileResponse(last_report_pdf_path, media_type="application/pdf", filename="audit_report.pdf")


def generate_audit_pdf(result: dict) -> str:
    output_dir = Path(get_settings().upload_dir) / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"audit_report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("AuditTitle", parent=styles["Title"], fontName="STSong-Light", fontSize=20, leading=26, alignment=TA_CENTER, spaceAfter=10)
    heading_style = ParagraphStyle("AuditHeading", parent=styles["Heading2"], fontName="STSong-Light", fontSize=13, leading=18, spaceBefore=12, spaceAfter=8)
    body_style = ParagraphStyle("AuditBody", parent=styles["BodyText"], fontName="STSong-Light", fontSize=9, leading=14)
    cell_style = ParagraphStyle("AuditCell", parent=body_style, fontSize=8, leading=11)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="ITAM 审计报告",
    )
    story = [
        Paragraph("ITAM 资产审计报告", title_style),
        Paragraph(f"生成时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", body_style),
        Spacer(1, 8),
    ]

    violations = result.get("violations") or []
    summary = result.get("audit_summary") or {}
    high_count = len([item for item in violations if item.get("severity") == "high"])
    medium_count = len([item for item in violations if item.get("severity") == "medium"])
    low_count = len([item for item in violations if item.get("severity") == "low"])
    response_count = len([item for item in violations if item.get("response_reason") or item.get("decision") not in (None, "", "pending")])

    story.append(Paragraph("一、审计概览", heading_style))
    story.append(build_table([
        ["资产总数", "风险评分", "风险总数", "人员风险", "资产风险", "已答复"],
        [
            str(result.get("total_assets", 0)),
            str(result.get("risk_score", 0)),
            str(len(violations)),
            str(summary.get("person", 0)),
            str(summary.get("asset", 0)),
            str(response_count),
        ],
        ["高风险", "中风险", "低风险", "审计范围", "报告格式", "生成方式"],
        [str(high_count), str(medium_count), str(low_count), "人员 + 资产", "PDF", "系统自动生成"],
    ], cell_style))

    story.append(Paragraph("二、风险规则统计", heading_style))
    rule_rows = [["规则", "命中数"]]
    for rule, count in sorted((summary.get("rules") or {}).items(), key=lambda item: item[1], reverse=True):
        rule_rows.append([safe_text(rule), str(count)])
    if len(rule_rows) == 1:
        rule_rows.append(["当前无规则命中", "0"])
    story.append(build_table(rule_rows, cell_style, col_widths=[120 * mm, 40 * mm]))

    story.append(Paragraph("三、处置建议", heading_style))
    for item in result.get("suggestions") or ["当前未发现显著审计风险，建议保持月度盘点和季度审计节奏。"]:
        story.append(Paragraph(f"• {safe_text(item)}", body_style))

    story.append(Paragraph("四、风险明细（最多显示前 100 条）", heading_style))
    detail_rows = [["对象", "资产/责任人", "风险类型", "等级", "答复状态", "说明"]]
    for item in violations[:100]:
        target = "人员" if item.get("audit_scope") == "person" else "资产"
        subject = item.get("owner_name") or item.get("owner_user_id") if target == "人员" else item.get("asset_id")
        decision = decision_label(item.get("decision"))
        if item.get("response_reason"):
            decision = f"{decision}：{item.get('response_reason')}"
        detail_rows.append([
            target,
            safe_text(subject or "-"),
            safe_text(item.get("type") or item.get("rule") or "-"),
            severity_label(item.get("severity")),
            safe_text(decision),
            safe_text(item.get("message") or "-"),
        ])
    if len(detail_rows) == 1:
        detail_rows.append(["-", "-", "无风险", "-", "-", "当前无审计命中记录"])
    story.append(build_table(detail_rows, cell_style, repeat_rows=1))

    doc.build(story)
    return str(output_path)


def build_table(rows: list[list[str]], cell_style: ParagraphStyle, col_widths: list[float] | None = None, repeat_rows: int = 0) -> Table:
    wrapped = [[Paragraph(safe_text(cell), cell_style) for cell in row] for row in rows]
    table = Table(wrapped, colWidths=col_widths, repeatRows=repeat_rows)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef6f5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f3f3a")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d7e3e8")),
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def safe_text(value) -> str:
    return str(value if value is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def severity_label(value: str | None) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(value or "", value or "-")


def decision_label(value: str | None) -> str:
    return {"accepted": "合规有理由", "non_compliant": "不合规", "pending": "待确认"}.get(value or "pending", "待确认")
