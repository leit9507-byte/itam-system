from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.number_sequence import NumberSequence


class NumberService:
    @staticmethod
    def next(db: Session, key: str, prefix: str, width: int) -> str:
        dialect = db.bind.dialect.name if db.bind else ""
        if dialect in {"mysql", "mariadb"}:
            db.execute(
                text("INSERT IGNORE INTO number_sequences (`key`, current_value, updated_at) VALUES (:key, 0, CURRENT_TIMESTAMP)"),
                {"key": key},
            )
        elif dialect == "sqlite":
            db.execute(
                text("INSERT OR IGNORE INTO number_sequences (`key`, current_value, updated_at) VALUES (:key, 0, CURRENT_TIMESTAMP)"),
                {"key": key},
            )
        row = db.query(NumberSequence).filter(NumberSequence.key == key).with_for_update().first()
        if not row:
            row = NumberSequence(key=key, current_value=0)
            db.add(row)
            db.flush()
        row.current_value += 1
        db.flush()
        return f"{prefix}{row.current_value:0{width}d}"
