from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .base import Base
class DatabaseEngine:

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.Base = Base


    def get_session(self):
        return self.Session()

    def get_base(self):
        return self.Base
        
    def add(self, obj):
        session = self.get_session()
        session.add(obj)
        session.commit()
        session.close()
    
    def get(self, model, id):
        session = self.get_session()
        obj = session.query(model).get(id)
        session.close()
        return obj
    
    def get_all(self, model):
        session = self.get_session()
        objs = session.query(model).all()
        session.close()
        return objs