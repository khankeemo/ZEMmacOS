from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(64), nullable=False, index=True)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    ip_address = Column(String(64), default="")
    license_key = Column(String(64), default="")
    hardware_id = Column(String(128), default="")
