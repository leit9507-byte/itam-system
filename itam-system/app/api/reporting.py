import csv
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import user_context_from_request
from app.models.asset import Asset
from app.models.checkout import AssetCheckout
from app.models.repair import RepairRecord
from app.models.scrap import ScrapRequest
from app.models.stocktake import StocktakeItem, StocktakeTask
from app.models.user import UserDirectory
from app.services.asset_service import AssetService
from app.services.audit_engine import AuditEngine


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/assets.csv")
def export_assets_csv(request: Request, db: Session = Depends(get_db)):
    rows = [
        [asset.asset_id, asset.asset_no, asset.name, asset.category, asset.brand, asset.model, asset.sn, asset.status, asset.owner_user_id, asset.dept_id, asset.location, asset.purchase_price]
        for asset in scoped_assets_query(db, request).order_by(Asset.asset_id.asc()).all()
    ]
    return csv_response("assets.csv", ["asset_id", "asset_no", "name", "category", "brand", "model", "sn", "status", "owner_user_id", "dept_id", "location", "purchase_price"], rows)


@router.get("/department-assets.csv")
def export_department_assets_csv(request: Request, db: Session = Depends(get_db)):
    rows = [
        [
            asset.dept_id or "",
            asset.asset_id,
            asset.asset_no or "",
            asset.name,
            asset.category,
            asset.brand or "",
            asset.model or "",
            asset.sn or "",
            asset.status or "",
            asset.owner_user_id or "",
            asset.location or "",
            money(asset.purchase_price),
            date_text(asset.created_at),
        ]
        for asset in scoped_assets_query(db, request).order_by(Asset.dept_id.asc(), Asset.asset_id.asc()).all()
    ]
    return csv_response("department-assets.csv", ["部门", "资产ID", "资产编号", "名称", "类型", "品牌", "型号", "SN", "状态", "责任人", "位置", "资产价值", "创建时间"], rows)


@router.get("/person-holdings.csv")
def export_person_holdings_csv(request: Request, db: Session = Depends(get_db)):
    users = users_by_identity(db)
    rows = []
    query = (
        scoped_assets_query(db, request)
        .filter(Asset.owner_user_id.isnot(None), Asset.owner_user_id != "", ~Asset.status.in_(["scrapped", "disposed"]))
        .order_by(Asset.owner_user_id.asc(), Asset.asset_id.asc())
    )
    for asset in query.all():
        user = users.get(asset.owner_user_id or "")
        rows.append([
            asset.owner_user_id or "",
            user.display_name if user else "",
            (user.dept_name or user.dept_id) if user else asset.dept_id or "",
            asset.asset_id,
            asset.asset_no or "",
            asset.name,
            asset.category,
            asset.status or "",
            asset.location or "",
            money(asset.purchase_price),
            date_text(asset.created_at),
        ])
    return csv_response("person-holdings.csv", ["人员ID", "姓名", "部门", "资产ID", "资产编号", "名称", "类型", "状态", "位置", "资产价值", "创建时间"], rows)


@router.get("/overdue-borrowings.csv")
def export_overdue_borrowings_csv(request: Request, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    scoped_asset_ids = scoped_asset_id_query(db, request)
    rows = []
    query = (
        db.query(AssetCheckout, Asset)
        .join(Asset, AssetCheckout.asset_id == Asset.asset_id)
        .filter(Asset.asset_id.in_(scoped_asset_ids), AssetCheckout.status == "open", AssetCheckout.due_date.isnot(None), AssetCheckout.due_date < now)
        .order_by(AssetCheckout.due_date.asc(), AssetCheckout.asset_id.asc())
    )
    for checkout, asset in query.all():
        rows.append([
            checkout.asset_id,
            asset.asset_no or "",
            asset.name,
            checkout.checkout_type,
            checkout.assignee_user_id or "",
            checkout.assignee_name or "",
            checkout.dept_id or asset.dept_id or "",
            date_text(checkout.checked_out_at),
            date_text(checkout.due_date),
            (now.date() - checkout.due_date.date()).days if checkout.due_date else 0,
            checkout.location or asset.location or "",
            checkout.remark or "",
        ])
    return csv_response("overdue-borrowings.csv", ["资产ID", "资产编号", "名称", "领用类型", "持有人ID", "持有人", "部门", "领用时间", "到期时间", "逾期天数", "位置", "备注"], rows)


@router.get("/warranty-expiring.csv")
def export_warranty_expiring_csv(request: Request, days: int = 90, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    end_at = now + timedelta(days=max(days, 0))
    rows = [
        [
            asset.asset_id,
            asset.asset_no or "",
            asset.name,
            asset.category,
            asset.brand or "",
            asset.model or "",
            asset.sn or "",
            asset.status or "",
            asset.owner_user_id or "",
            asset.dept_id or "",
            asset.location or "",
            date_text(asset.purchase_date),
            date_text(asset.warranty_expire_date),
            (asset.warranty_expire_date.date() - now.date()).days if asset.warranty_expire_date else "",
        ]
        for asset in scoped_assets_query(db, request)
        .filter(Asset.warranty_expire_date.isnot(None), Asset.warranty_expire_date >= now, Asset.warranty_expire_date <= end_at)
        .order_by(Asset.warranty_expire_date.asc(), Asset.asset_id.asc())
        .all()
    ]
    return csv_response("warranty-expiring.csv", ["资产ID", "资产编号", "名称", "类型", "品牌", "型号", "SN", "状态", "责任人", "部门", "位置", "采购日期", "质保到期", "剩余天数"], rows)


@router.get("/scrap-disposal-ledger.csv")
def export_scrap_disposal_ledger_csv(request: Request, db: Session = Depends(get_db)):
    scoped_asset_ids = scoped_asset_id_query(db, request)
    rows = [
        [
            row.request_no,
            row.asset_id,
            row.asset_name,
            row.asset_sn or "",
            row.category or "",
            row.brand or "",
            row.model or "",
            row.owner_user_id or "",
            row.dept_id or "",
            row.location or "",
            money(row.purchase_price),
            row.status,
            row.applicant or "",
            row.reason or "",
            row.disposal_method or "",
            money(row.estimated_residual_value),
            money(row.final_residual_value),
            row.disposed_by or "",
            date_text(row.disposed_at),
            row.disposal_remark or "",
            date_text(row.created_at),
        ]
        for row in db.query(ScrapRequest)
        .filter(ScrapRequest.asset_id.in_(scoped_asset_ids))
        .order_by(ScrapRequest.created_at.desc(), ScrapRequest.id.desc())
        .all()
    ]
    return csv_response("scrap-disposal-ledger.csv", ["报废单号", "资产ID", "资产名称", "SN", "类型", "品牌", "型号", "责任人", "部门", "位置", "采购价值", "状态", "申请人", "报废原因", "处置方式", "预计残值", "最终残值", "处置人", "处置时间", "处置备注", "申请时间"], rows)


@router.get("/audit-report.xlsx")
def export_audit_report_excel(db: Session = Depends(get_db)):
    result = AuditEngine(db).run()
    workbook = Workbook()
    build_audit_summary_sheet(workbook.active, result)
    build_audit_violations_sheet(workbook.create_sheet("风险明细"), result.get("violations") or [])
    build_audit_responses_sheet(workbook.create_sheet("审计答复"), result.get("responses") or [])
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    filename = f"audit-report-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/assets.pdf")
def export_assets_pdf(request: Request, db: Session = Depends(get_db)):
    output_dir = Path(get_settings().upload_dir) / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "assets.pdf"
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "ITAM Asset Report")
    y -= 28
    c.setFont("Helvetica", 9)
    for asset in scoped_assets_query(db, request).order_by(Asset.asset_id.asc()).all():
        line = f"{asset.asset_id} | {asset.name} | {asset.category} | {asset.status} | {asset.owner_user_id or '-'} | {asset.location or '-'}"
        c.drawString(40, y, line[:120])
        y -= 16
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = height - 40
    c.save()
    return FileResponse(output_path, filename="assets.pdf", media_type="application/pdf")


@router.get("/analytics")
def report_analytics(request: Request, db: Session = Depends(get_db)):
    scoped_asset_ids = [row[0] for row in scoped_assets_query(db, request).with_entities(Asset.asset_id).all()]
    if not scoped_asset_ids:
        return {
            "department_occupancy": [],
            "per_capita_value": [],
            "idle_trend": [],
            "repair_cost_trend": [],
            "stocktake_diff_trend": [],
        }
    department_rows = (
        db.query(
            Asset.dept_id,
            func.count(Asset.asset_id),
            func.coalesce(func.sum(Asset.purchase_price), 0),
            func.count(func.distinct(Asset.owner_user_id)),
        )
        .filter(Asset.asset_id.in_(scoped_asset_ids), ~Asset.status.in_(["scrapped", "disposed"]))
        .group_by(Asset.dept_id)
        .order_by(func.count(Asset.asset_id).desc())
        .all()
    )
    department_occupancy = [
        {
            "dept_id": dept_id or "未绑定",
            "asset_count": int(asset_count or 0),
            "asset_value": float(asset_value or 0),
            "owner_count": int(owner_count or 0),
            "per_capita_value": float(asset_value or 0) / max(int(owner_count or 0), 1),
        }
        for dept_id, asset_count, asset_value, owner_count in department_rows
    ]
    months = month_windows(6)
    idle_trend = [
        {
            "month": month,
            "count": db.query(func.count(Asset.asset_id))
            .filter(Asset.asset_id.in_(scoped_asset_ids), Asset.status.in_(["idle", "in_stock"]), Asset.created_at <= end_at)
            .scalar()
            or 0,
        }
        for month, _start_at, end_at in months
    ]
    repair_cost_trend = [
        {
            "month": month,
            "cost": float(
                db.query(func.coalesce(func.sum(RepairRecord.repair_cost), 0))
                .filter(RepairRecord.asset_id.in_(scoped_asset_ids), RepairRecord.repair_time >= start_at, RepairRecord.repair_time < end_at)
                .scalar()
                or 0
            ),
        }
        for month, start_at, end_at in months
    ]
    stocktake_diff_trend = [
        {
            "month": month,
            "diff_count": int(
                db.query(func.count(StocktakeItem.id))
                .join(StocktakeTask, StocktakeItem.task_id == StocktakeTask.id)
                .filter(StocktakeItem.asset_id.in_(scoped_asset_ids), StocktakeTask.created_at >= start_at, StocktakeTask.created_at < end_at, StocktakeItem.result != "正常")
                .scalar()
                or 0
            ),
        }
        for month, start_at, end_at in months
    ]
    return {
        "department_occupancy": department_occupancy,
        "per_capita_value": department_occupancy,
        "idle_trend": idle_trend,
        "repair_cost_trend": repair_cost_trend,
        "stocktake_diff_trend": stocktake_diff_trend,
    }


def scoped_assets_query(db: Session, request: Request):
    return AssetService.apply_data_scope(db.query(Asset), user_context_from_request(request))


def scoped_asset_id_query(db: Session, request: Request) -> list[str]:
    return [row[0] for row in scoped_assets_query(db, request).with_entities(Asset.asset_id).all()]


def users_by_identity(db: Session) -> dict[str, UserDirectory]:
    users = db.query(UserDirectory).all()
    result = {}
    for user in users:
        for key in [user.user_id, user.username, user.email, user.external_id]:
            if key:
                result[str(key)] = user
    return result


def csv_response(filename: str, headers: list[str], rows: list[list]) -> PlainTextResponse:
    output = StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def date_text(value) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def money(value) -> float:
    return float(value or 0)


def build_audit_summary_sheet(sheet, result: dict) -> None:
    sheet.title = "审计概览"
    rows = [
        ["指标", "值"],
        ["资产总数", result.get("total_assets", 0)],
        ["风险评分", result.get("risk_score", 0)],
        ["风险总数", len(result.get("violations") or [])],
        ["人员风险", (result.get("audit_summary") or {}).get("person", 0)],
        ["资产风险", (result.get("audit_summary") or {}).get("asset", 0)],
    ]
    for row in rows:
        sheet.append(row)
    style_sheet(sheet)


def build_audit_violations_sheet(sheet, violations: list[dict]) -> None:
    sheet.append(["范围", "规则", "等级", "资产ID", "资产名称", "责任人", "部门", "说明", "处理结论", "答复原因", "答复人"])
    for item in violations:
        sheet.append([
            item.get("audit_scope", ""),
            item.get("rule", ""),
            item.get("severity", ""),
            item.get("asset_id", ""),
            item.get("asset_name", ""),
            item.get("owner_name") or item.get("owner_user_id") or "",
            item.get("dept", ""),
            item.get("message") or item.get("description") or item.get("type") or "",
            item.get("decision", ""),
            item.get("response_reason", ""),
            item.get("responder", ""),
        ])
    style_sheet(sheet)


def build_audit_responses_sheet(sheet, responses: list[dict]) -> None:
    sheet.append(["风险Key", "资产ID", "规则", "范围", "结论", "原因", "答复人", "更新时间"])
    for item in responses:
        sheet.append([
            item.get("violation_key", ""),
            item.get("asset_id", ""),
            item.get("rule_code", ""),
            item.get("audit_scope", ""),
            item.get("decision", ""),
            item.get("reason", ""),
            item.get("responder", ""),
            date_text(item.get("updated_at")),
        ])
    style_sheet(sheet)


def style_sheet(sheet) -> None:
    fill = PatternFill("solid", fgColor="D9EAF7")
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = fill
    for column_cells in sheet.columns:
        width = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 42)
        sheet.column_dimensions[column_cells[0].column_letter].width = width


def month_windows(count: int) -> list[tuple[str, datetime, datetime]]:
    today = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    starts = []
    current = today
    for _ in range(count - 1):
        starts.append(current)
        current = (current - timedelta(days=1)).replace(day=1)
    starts.append(current)
    starts = list(reversed(starts))
    windows = []
    for start in starts:
        end = datetime(start.year + 1, 1, 1) if start.month == 12 else datetime(start.year, start.month + 1, 1)
        windows.append((start.strftime("%Y-%m"), start, end))
    return windows
