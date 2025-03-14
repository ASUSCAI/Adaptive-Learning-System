from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
    func
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from .base import Base


# CATEGORY (Track)
class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    # One-to-many relationship: Category has many Questions
    questions = relationship('Question', back_populates='category', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"

# QUESTION
class Question(Base):
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)

    # Relationships
    category = relationship('Category', back_populates='questions')
    options = relationship('Option', back_populates='question', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Question(id={self.id}, text='{self.text[:30]}...')>"

# OPTION (Answers for Questions)
class Option(Base):
    __tablename__ = 'options'
    
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False)

    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    question = relationship('Question', back_populates='options')

    def __repr__(self):
        return f"<Option(id={self.id}, text='{self.text[:30]}...', is_correct={self.is_correct})>"

# USER (Learner)
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

    attempts = relationship('AttemptLog', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}')>"

# ATTEMPT LOG (User interactions)
class AttemptLog(Base):
    __tablename__ = 'attempt_logs'
    
    id = Column(Integer, primary_key=True)
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    option_id = Column(Integer, ForeignKey('options.id'))

    is_correct = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship('User', back_populates='attempts')
    question = relationship('Question')
    option = relationship('Option')

    def __repr__(self):
        return (
            f"<AttemptLog(user_id={self.user_id}, question_id={self.question_id}, "
            f"option_id={self.option_id}, is_correct={self.is_correct})>"
        )

# PROGRESS TRACKER (Optional - User progress per category)
class Progress(Base):
    __tablename__ = 'progress'
    
    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    
    # Accuracy as % or score for adaptive learning insights
    accuracy = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)

    user = relationship('User')
    category = relationship('Category')

    def __repr__(self):
        return (
            f"<Progress(user_id={self.user_id}, category_id={self.category_id}, "
            f"accuracy={self.accuracy}, completed={self.completed})>"
        )