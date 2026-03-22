from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_google_user = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_pro = Column(Boolean, default=False)
    picture = Column(String, nullable=True)
    resume_latex = Column(Text, nullable=True)
