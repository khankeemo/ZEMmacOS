from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from database import Base


class Trial(Base):
    __tablename__ = "trials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hardware_id = Column(String(128), unique=True, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), default="active", index=True)
