from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False, index=True)
    license_key = Column(String(64), unique=True, nullable=False, index=True)
    plan = Column(String(64), default="Standard")
    status = Column(String(32), default="active", index=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    max_devices = Column(Integer, default=1)
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    activations = relationship("Activation", back_populates="license", cascade="all, delete-orphan")
