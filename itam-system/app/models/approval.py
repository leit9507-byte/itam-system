from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text

from app.core.database import Base


class ApprovalRule(Base):
    __tablename__ = "approval_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flow_type = Column(String(32), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    min_amount = Column(Numeric(12, 2, asdecimal=False), nullable=True)
    max_amount = Column(Numeric(12, 2, asdecimal=False), nullable=True)
    dept_id = Column(String(64), nullable=True, index=True)
    approver_role = Column(String(64), nullable=True)
    approver_user_id = Column(String(64), nullable=True)
    level = Column(Integer, default=1, nullable=False, index=True)
    require_all = Column(Boolean, default=False, nullable=False)
    provider = Column(String(32), default="feishu", nullable=False, index=True)
    approval_code = Column(String(128), nullable=True, index=True)
    app_id = Column(String(128), nullable=True)
    app_secret = Column(String(255), nullable=True)
    tenant_access_token_url = Column(String(255), default="https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", nullable=True)
    instance_create_url = Column(String(255), default="https://open.feishu.cn/open-apis/approval/v4/instances", nullable=True)
    submitter_user_id = Column(String(128), nullable=True)
    submitter_open_id = Column(String(128), nullable=True)
    form_template = Column(Text, nullable=True)
    callback_token = Column(String(255), nullable=True)
    callback_encrypt_key = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ApprovalInstanceLog(Base):
    __tablename__ = "approval_instance_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flow_type = Column(String(32), nullable=False, index=True)
    config_id = Column(Integer, nullable=True, index=True)
    business_id = Column(String(128), nullable=True, index=True)
    approval_code = Column(String(128), nullable=True, index=True)
    instance_code = Column(String(128), nullable=True, index=True)
    status = Column(String(32), default="submitted", nullable=False, index=True)
    requester = Column(String(128), nullable=True)
    request_payload = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
