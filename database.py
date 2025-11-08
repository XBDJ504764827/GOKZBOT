import os
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from contextlib import contextmanager

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    qq_id = Column(String, primary_key=True)
    steam_id = Column(String, nullable=True)
    steam_id_64 = Column(String, nullable=True, unique=True)
    steam_name = Column(String, nullable=False)
    default_mode = Column(String, nullable=True, default='kzt')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

db_url = "postgresql+psycopg2://qqbot:qqbotqqbot@103.120.89.225/qqbot"
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
