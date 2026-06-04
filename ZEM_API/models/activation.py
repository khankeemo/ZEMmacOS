from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Activation(Base):
    __tablename__ = "activations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    license_id = Column(Integer, ForeignKey("licenses.id", ondelete="CASCADE"), nullable=False, index=True)
    hardware_id = Column(String(128), nullable=False, index=True)
    activated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_seen = Column(DateTime(timezone=True), default=datetime.utcnow)
    device_name = Column(String(255), default="")
    ip_address = Column(String(64), default="")

    license = relationship("License", back_populates="activations")
