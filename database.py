import os
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    qq_id = Column(String, primary_key=True)
    steam_id = Column(String, nullable=False)

def get_db_session(data_dir: str):
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    db_path = os.path.join(data_dir, 'gokz.db')
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
