import os
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    qq_id = Column(String, primary_key=True)
    steam_id_64 = Column(String, nullable=False, unique=True)
    steam_name = Column(String, nullable=False)
    default_mode = Column(String, nullable=False, default='kzt')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

def get_db_session():
    db_url = "postgresql+psycopg2://qqbot:qqbotqqbot@103.120.89.225/qqbot"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
