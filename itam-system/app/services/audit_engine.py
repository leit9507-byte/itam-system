from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.rules.rule_engine import RuleEngine


class AuditEngine:
    severity_scores = {"high": 30, "medium": 15, "low": 5}

    def __init__(self, db: Session):
        self.db = db

    def run(self, users: list[dict] | None = None) -> dict:
        assets = self.db.query(Asset).all()
        violations = RuleEngine(self.db).run()
        risk_score = min(
            100,
            sum(self.severity_scores.get(item.get("severity"), 0) for item in violations),
        )
        return {
            "total_assets": len(assets),
            "users": users or [],
            "violations": violations,
            "risk_score": risk_score,
            "suggestions": self._suggestions(violations),
        }

    def _suggestions(self, violations: list[dict]) -> list[str]:
        rules = {item["rule"] for item in violations}
        suggestions = []
        if "HIGH_VALUE_WITHOUT_DEPT" in rules:
            suggestions.append("为高价值资产补齐部门归属，并纳入部门负责人审批。")
        if "ASSET_IDLE_OVER_90_DAYS" in rules:
            suggestions.append("建立闲置资产调拨流程，优先复用库存资产。")
        if "USER_ASSET_COUNT_LIMIT" in rules or "SINGLE_OWNER_VALUE_LIMIT" in rules:
            suggestions.append("复核个人名下资产数量与价值，必要时调整责任人或回收资产。")
        if not suggestions:
            suggestions.append("未发现显著风险，建议保持周期性盘点。")
        return suggestions
