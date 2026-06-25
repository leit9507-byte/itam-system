from collections import Counter

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.audit_response import AuditResponse
from app.models.user import UserDirectory
from app.rules.rule_engine import RuleEngine


class AuditEngine:
    severity_scores = {"high": 30, "medium": 15, "low": 5}

    def __init__(self, db: Session):
        self.db = db

    def run(self, users: list[dict] | None = None) -> dict:
        assets = self.db.query(Asset).all()
        asset_map = {asset.asset_id: asset for asset in assets}
        user_map = {user.user_id: user for user in self.db.query(UserDirectory).all()}
        responses = {item.violation_key: item for item in self.db.query(AuditResponse).all()}
        violations = RuleEngine(self.db).run()
        enriched = [self._enrich_violation(item, asset_map, user_map, responses) for item in violations]
        risk_score = min(
            100,
            sum(self.severity_scores.get(item.get("severity"), 0) for item in enriched),
        )
        return {
            "total_assets": len(assets),
            "users": users or [],
            "violations": enriched,
            "risk_score": risk_score,
            "audit_summary": self._summary(enriched),
            "person_groups": self._person_groups(enriched, responses),
            "asset_violations": [item for item in enriched if item.get("audit_scope") == "asset"],
            "responses": [self._serialize_response(item) for item in responses.values()],
            "suggestions": self._suggestions(enriched),
        }

    def _enrich_violation(
        self,
        item: dict,
        asset_map: dict[str, Asset],
        user_map: dict[str, UserDirectory],
        responses: dict[str, AuditResponse],
    ) -> dict:
        asset = asset_map.get(item.get("asset_id"))
        owner_id = item.get("owner_user_id") or (asset.owner_user_id if asset else "")
        user = user_map.get(owner_id or "")
        audit_scope = item.get("audit_scope", "asset")
        violation_key = self._violation_key(item.get("rule", ""), item.get("asset_id", ""), owner_id, audit_scope)
        person_group_key = self._person_group_key(item.get("rule", ""), owner_id)
        response = responses.get(violation_key) or responses.get(person_group_key)
        return {
            **item,
            "violation_key": violation_key,
            "person_group_key": person_group_key,
            "asset_name": asset.name if asset else "",
            "category": asset.category if asset else "",
            "brand": asset.brand if asset else "",
            "model": asset.model if asset else "",
            "sn": asset.sn if asset else "",
            "owner_name": user.display_name if user else owner_id,
            "owner_user_id": owner_id,
            "dept": (user.dept_name or user.dept_id) if user else (asset.dept_id if asset else ""),
            "price": asset.purchase_price if asset else 0,
            "decision": response.decision if response else "pending",
            "response_reason": response.reason if response else "",
            "responder": response.responder if response else "",
            "response_updated_at": response.updated_at if response else None,
        }

    def _person_groups(self, violations: list[dict], responses: dict[str, AuditResponse]) -> list[dict]:
        grouped = {}
        for item in violations:
            if item.get("audit_scope") != "person":
                continue
            key = item.get("person_group_key")
            response = responses.get(key)
            row = grouped.setdefault(
                key,
                {
                    "violation_key": key,
                    "rule": item.get("rule"),
                    "type": item.get("type") or item.get("rule"),
                    "severity": item.get("severity"),
                    "owner_user_id": item.get("owner_user_id"),
                    "owner_name": item.get("owner_name"),
                    "dept": item.get("dept"),
                    "assets": [],
                    "asset_count": 0,
                    "total_price": 0,
                    "decision": response.decision if response else item.get("decision", "pending"),
                    "response_reason": response.reason if response else item.get("response_reason", ""),
                    "responder": response.responder if response else item.get("responder", ""),
                    "response_updated_at": response.updated_at if response else item.get("response_updated_at"),
                },
            )
            row["assets"].append(item)
            row["asset_count"] += 1
            row["total_price"] += float(item.get("price") or 0)
            if self.severity_scores.get(item.get("severity"), 0) > self.severity_scores.get(row.get("severity"), 0):
                row["severity"] = item.get("severity")
        return list(grouped.values())

    def _serialize_response(self, item: AuditResponse) -> dict:
        return {
            "violation_key": item.violation_key,
            "asset_id": item.asset_id,
            "rule_code": item.rule_code,
            "audit_scope": item.audit_scope,
            "decision": item.decision,
            "reason": item.reason or "",
            "responder": item.responder or "",
            "updated_at": item.updated_at,
        }

    def _violation_key(self, rule: str, asset_id: str, owner_id: str | None, audit_scope: str) -> str:
        return "|".join([rule or "", asset_id or "", owner_id or "", audit_scope or "asset"])

    def _person_group_key(self, rule: str, owner_id: str | None) -> str:
        return "|".join([rule or "", owner_id or "", "person_group"])

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
