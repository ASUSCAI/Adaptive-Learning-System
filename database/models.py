from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

base = declarative_base()

class Question(base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    question = Column(String)
    options = relationship('Option', back_populates='question')



class Option(base):
    __tablename__ = 'options'
    id = Column(Integer, primary_key=True)
    option = Column(String)
    question_id = Column(Integer, ForeignKey('questions.id'))
    question = relationship('Question', back_populates='options')
    correct = Column(Boolean, default=False)

class Category(base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    questions = relationship('Question', back_populates='category')

class User(base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    section = relationship('Section', back_populates='users')

class Section(base):
    __tablename__ = 'sections'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    categories = relationship('Category', back_populates='section')

class Logs(base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User')
    action = Column(String)
    timestamp = Column(DateTime)

