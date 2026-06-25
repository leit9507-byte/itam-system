from collections import Counter

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
            "audit_summary": self._summary(violations),
            "suggestions": self._suggestions(violations),
        }

    def _summary(self, violations: list[dict]) -> dict:
        scope_counter = Counter(item.get("audit_scope", "asset") for item in violations)
        rule_counter = Counter(item.get("rule") for item in violations)
        return {
            "person": scope_counter.get("person", 0),
            "asset": scope_counter.get("asset", 0),
            "rules": dict(rule_counter),
        }

    def _suggestions(self, violations: list[dict]) -> list[str]:
        rules = {item["rule"] for item in violations}
        suggestions = []
        if "USER_ASSET_COUNT_LIMIT" in rules:
            suggestions.append("人员资产数量超配建议按设备类型复核标准配置，并发起多余资产回收入库。")
        if "OFFBOARDING_ASSET_NOT_RETURNED" in rules:
            suggestions.append("离职未回收资产建议与 HR/SSO 状态联动，生成离职资产回收待办。")
        if "BORROWED_ASSET_NOT_RETURNED" in rules:
            suggestions.append("借用超期资产建议设置归还日期和自动提醒，超期后进入回收流程。")
        if "SINGLE_OWNER_VALUE_LIMIT" in rules:
            suggestions.append("人员名下资产价值过高建议复核审批依据、岗位配置标准和部门归属。")
        if "HIGH_VALUE_PURCHASE" in rules:
            suggestions.append("超价值采购资产建议复核采购审批单、供应商、合同和预算依据。")
        if "ASSET_IDLE_OVER_90_DAYS" in rules:
            suggestions.append("长期闲置资产建议优先调拨复用，无法复用时进入报废或处置流程。")
        if not suggestions:
            suggestions.append("当前未发现显著审计风险，建议保持月度盘点和季度审计节奏。")
        return suggestions
