import argparse
import csv
from pathlib import Path


def clean_text(value) -> str:
    return str(value or "").strip()


def sql_quote(value: str) -> str:
    return "'" + clean_text(value).replace("\\", "\\\\").replace("'", "''") + "'"


def read_assets(path: Path) -> list[dict]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"cannot decode {path}")


def write_csv(path: Path, rows: list[dict]) -> None:
    headers = ["asset_id", "scan_raw", "scan_key", "scan_type", "status", "remark"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_sql(path: Path, rows: list[dict]) -> None:
    lines = [
        "START TRANSACTION;",
        "",
        "-- Bind legacy asset id as scan content. Legacy asset URLs ending in",
        "-- /hardware/1602 are also resolved by extracting 1602.",
        "",
    ]
    for row in rows:
        asset_id = sql_quote(row["asset_id"])
        scan_raw = sql_quote(row["scan_raw"])
        scan_key = sql_quote(row["scan_key"])
        scan_type = sql_quote(row["scan_type"])
        status = sql_quote(row["status"])
        remark = sql_quote(row["remark"])
        lines.append(
            "INSERT INTO asset_scan_bindings "
            "(asset_id, scan_key, scan_raw, scan_type, status, remark, created_by, created_at, updated_at) "
            f"SELECT {asset_id}, {scan_key}, {scan_raw}, {scan_type}, {status}, {remark}, "
            "'legacy-scan-binding', UTC_TIMESTAMP(), UTC_TIMESTAMP() "
            f"WHERE EXISTS (SELECT 1 FROM assets WHERE asset_id = {asset_id}) "
            f"ON DUPLICATE KEY UPDATE asset_id = VALUES(asset_id), scan_raw = VALUES(scan_raw), "
            "scan_type = VALUES(scan_type), status = 'active', remark = VALUES(remark), updated_at = UTC_TIMESTAMP();"
        )
    lines.extend(["", "COMMIT;", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-file", required=True, help="Cleaned asset import CSV")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    assets = read_assets(Path(args.asset_file))
    rows = []
    seen = set()
    for asset in assets:
        asset_id = clean_text(asset.get("asset_id"))
        if not asset_id or asset_id in seen:
            continue
        seen.add(asset_id)
        rows.append({
            "asset_id": asset_id,
            "scan_raw": asset_id,
            "scan_key": asset_id.lower(),
            "scan_type": "legacy",
            "status": "active",
            "remark": "legacy asset id scan binding",
        })

    csv_path = out_dir / "legacy_scan_bindings.csv"
    sql_path = out_dir / "legacy_scan_bindings.sql"
    write_csv(csv_path, rows)
    write_sql(sql_path, rows)

    print(f"binding_rows: {len(rows)}")
    print(f"csv: {csv_path}")
    print(f"sql: {sql_path}")


if __name__ == "__main__":
    main()
