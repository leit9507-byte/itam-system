import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook


IMPORT_HEADERS = [
    "asset_id",
    "asset_no",
    "name",
    "category",
    "brand",
    "model",
    "sn",
    "purchase_price",
    "purchase_date",
    "purchase_approval_no",
    "purchase_supplier_name",
    "warranty_years",
    "status",
    "owner_user_id",
    "dept_id",
    "location",
    "company",
    "spec",
    "payment_time",
    "payment_no",
    "remark",
]

CONFIG_FIELDS = ["CPU", "内存", "硬盘", "显卡", "分辨率", "操作系统", "IP地址", "MAC地址", "IMEI"]


def read_csv(path: Path) -> list[dict]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"cannot decode {path}")


def clean_text(value) -> str:
    return str(value or "").strip()


def clean_price(value) -> str:
    raw = clean_text(value)
    if not raw:
        return "0"
    raw = raw.replace(",", "").replace("￥", "").replace("¥", "").replace("元", "").strip()
    if raw in {"-", "'-"}:
        return "0"
    try:
        return f"{float(raw):.2f}"
    except ValueError:
        return "0"


def clean_date(value) -> str:
    raw = clean_text(value)
    if not raw or raw in {"0", "-", "'-"}:
        return ""
    raw = raw.split()[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def warranty_years(row: dict) -> str:
    warranty = clean_text(row.get("质保"))
    if warranty:
        match = re.search(r"(\d+)", warranty)
        if match:
            months = int(match.group(1))
            return str(round(months / 12, 2)) if months else ""
    expire = clean_date(row.get("质保"))
    purchase = clean_date(row.get("购买日期"))
    if expire and purchase:
        start = datetime.strptime(purchase, "%Y-%m-%d")
        end = datetime.strptime(expire, "%Y-%m-%d")
        return str(max(0, round((end - start).days / 365, 2)))
    return ""


def normalize_status(value: str) -> tuple[str, str]:
    raw = clean_text(value)
    compact = raw.replace(" ", "")
    if not raw:
        return "in_stock", "空状态按在库导入"
    if "待退役" in compact:
        return "ready_scrap", ""
    if "已退役" in compact or "出售二手" in compact or "已报废" in compact:
        return "disposed", ""
    if "待分配" in compact:
        return "in_stock", ""
    if "已分配" in compact or "在用" in compact:
        return "in_use", ""
    if "维修" in compact:
        return "repair", ""
    if "借" in compact:
        return "borrowed", ""
    if "丢失" in compact or "遗失" in compact:
        return "lost", ""
    if "待报废" in compact:
        return "ready_scrap", ""
    if "待验收" in compact:
        return "pending_acceptance", ""
    if "库存" in compact or "在库" in compact:
        return "in_stock", ""
    return "in_stock", f"未识别状态：{raw}，按在库导入"


def build_spec(row: dict) -> str:
    parts = []
    for field in CONFIG_FIELDS:
        value = clean_text(row.get(field))
        if value and value not in {"-", "'-"}:
            parts.append(f"{field}:{value}")
    return "；".join(parts)


def merge_remark(row: dict, issues: list[str]) -> str:
    parts = []
    for field in ("备注", "收货单号", "寿命", "保修期已过", "默认位置", "上一次盘点", "下一次盘点时间", "盘点时间"):
        value = clean_text(row.get(field))
        if value and value not in {"0", "-", "'-"}:
            parts.append(f"{field}:{value}")
    if issues:
        parts.append("清洗提示:" + "；".join(issues))
    return "；".join(parts)


def clean_row(row: dict, source_file: str) -> tuple[dict, list[dict]]:
    issues = []
    asset_id = clean_text(row.get("编号"))
    asset_no = clean_text(row.get("资产标签"))
    if not asset_id:
        issues.append("缺少旧系统编号")
    if not asset_no:
        asset_no = f"LEGACY-{asset_id or 'UNKNOWN'}"
        issues.append("缺少资产标签，已使用临时标签")

    status, status_issue = normalize_status(row.get("状态"))
    if status_issue:
        issues.append(status_issue)

    purchase_date = clean_date(row.get("购买日期"))
    if clean_text(row.get("购买日期")) and not purchase_date:
        issues.append(f"购买日期无法识别：{row.get('购买日期')}")

    price = clean_price(row.get("采购价格"))
    if clean_text(row.get("采购价格")) and price == "0":
        issues.append(f"采购价格无法识别：{row.get('采购价格')}")

    owner = clean_text(row.get("借出至"))
    dept = clean_text(row.get("部门"))
    if status == "in_use" and not owner and not clean_text(row.get("位置")):
        issues.append("在用资产缺少责任人和位置")

    cleaned = {
        "asset_id": asset_id,
        "asset_no": asset_no,
        "name": clean_text(row.get("资产名称")) or "Unnamed Asset",
        "category": clean_text(row.get("类别")) or "Other",
        "brand": clean_text(row.get("制造商")),
        "model": clean_text(row.get("型号")),
        "sn": clean_text(row.get("序列号")),
        "purchase_price": price,
        "purchase_date": purchase_date,
        "purchase_approval_no": clean_text(row.get("付款单号")) or clean_text(row.get("收货单号")),
        "purchase_supplier_name": clean_text(row.get("供应商")),
        "warranty_years": warranty_years(row),
        "status": status,
        "owner_user_id": owner,
        "dept_id": dept,
        "location": clean_text(row.get("位置")) or clean_text(row.get("默认位置")),
        "company": clean_text(row.get("公司")),
        "spec": build_spec(row),
        "payment_time": clean_date(row.get("付款时间")),
        "payment_no": clean_text(row.get("付款单号")),
        "remark": "",
    }
    cleaned["remark"] = merge_remark(row, issues)

    issue_rows = [
        {
            "source_file": source_file,
            "asset_id": asset_id,
            "asset_no": asset_no,
            "name": cleaned["name"],
            "issue": issue,
        }
        for issue in issues
    ]
    return cleaned, issue_rows


def is_empty_export_row(row: dict) -> bool:
    important_fields = ["编号", "资产名称", "资产标签", "序列号", "型号", "类别", "状态"]
    return not any(clean_text(row.get(field)) for field in important_fields)


def write_csv(path: Path, rows: list[dict], headers: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, rows: list[dict], headers: list[str]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "assets"
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header, "") for header in headers])
    workbook.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    issues = []
    source_counts = Counter()
    raw_status_counts = Counter()

    for file_name in args.files:
        path = Path(file_name)
        rows = read_csv(path)
        rows = [row for row in rows if not is_empty_export_row(row)]
        source_counts[path.name] = len(rows)
        for row in rows:
            raw_status_counts[clean_text(row.get("状态")) or "(空)"] += 1
            cleaned, row_issues = clean_row(row, path.name)
            all_rows.append(cleaned)
            issues.extend(row_issues)

    duplicate_issues = []
    for field in ("asset_id", "asset_no", "sn"):
        values = defaultdict(list)
        for row in all_rows:
            value = clean_text(row.get(field))
            if value:
                values[value].append(row)
        for value, rows in values.items():
            if len(rows) > 1:
                for row in rows:
                    duplicate_issues.append({
                        "source_file": "",
                        "asset_id": row["asset_id"],
                        "asset_no": row["asset_no"],
                        "name": row["name"],
                        "issue": f"{field} 重复：{value}",
                    })
    issues.extend(duplicate_issues)

    status_counts = Counter(row["status"] for row in all_rows)

    import_csv = out_dir / "legacy_assets_import_ready.csv"
    import_xlsx = out_dir / "legacy_assets_import_ready.xlsx"
    issue_csv = out_dir / "legacy_assets_cleaning_issues.csv"
    summary_txt = out_dir / "legacy_assets_cleaning_summary.txt"

    write_csv(import_csv, all_rows, IMPORT_HEADERS)
    write_xlsx(import_xlsx, all_rows, IMPORT_HEADERS)
    write_csv(issue_csv, issues, ["source_file", "asset_id", "asset_no", "name", "issue"])

    with summary_txt.open("w", encoding="utf-8") as handle:
        handle.write(f"total_rows: {len(all_rows)}\n")
        handle.write("\nsource_counts:\n")
        for key, value in source_counts.items():
            handle.write(f"- {key}: {value}\n")
        handle.write("\nnormalized_status_counts:\n")
        for key, value in status_counts.items():
            handle.write(f"- {key}: {value}\n")
        handle.write("\nraw_status_counts:\n")
        for key, value in raw_status_counts.items():
            handle.write(f"- {key}: {value}\n")
        handle.write(f"\nissue_rows: {len(issues)}\n")
        handle.write(f"import_csv: {import_csv}\n")
        handle.write(f"import_xlsx: {import_xlsx}\n")
        handle.write(f"issues_csv: {issue_csv}\n")

    print(summary_txt.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
