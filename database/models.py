from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
    func,
    event,
    Table,
    PickleType
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from .base import Base
from bkt.engine import BKTEngine, IBKTEngine
import uuid

# Section-User association table (many-to-many)
section_users = Table('section_users', Base.metadata,
    Column('section_id', Integer, ForeignKey('sections.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

# Section-Category association table (many-to-many)
section_categories = Table('section_categories', Base.metadata,
    Column('section_id', Integer, ForeignKey('sections.id'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id'), primary_key=True)
)

# SECTION
class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Many-to-many relationship with users
    users = relationship("User", secondary=section_users, back_populates="sections")
    
    # Many-to-many relationship with categories
    categories = relationship("Category", secondary=section_categories, back_populates="sections")
    
    def __repr__(self):
        return f"<Section(id={self.id}, name='{self.name}')>"

# CATEGORY (Track)
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    uuid = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Add questions relationship
    questions = relationship("Question", back_populates="category", cascade="all, delete-orphan")
    
    # Add relationship to UserCategory
    user_categories = relationship("UserCategory", back_populates="category", cascade="all, delete-orphan")
    
    # Add relationship to Section (many-to-many)
    sections = relationship("Section", secondary=section_categories, back_populates="categories")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"

# QUESTION
class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    uuid = Column(String, unique=True, nullable=False)
    
    # Update the relationship to match Category model
    category = relationship("Category", back_populates="questions")
    
    options = relationship(
        "Option", back_populates="question", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Question(id={self.id}, text='{self.text[:30]}...')>"

# OPTION (Answers for Questions)
class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False)

    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question = relationship("Question", back_populates="options")
    uuid = Column(String, unique=True, nullable=False)

    def __repr__(self):
        return f"<Option(id={self.id}, text='{self.text[:30]}...', is_correct={self.is_correct})>"


# USER (Learner)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)  # For authentication
    is_admin = Column(Boolean, default=False)  # Admin flag

    attempts = relationship(
        "AttemptLog", back_populates="user", cascade="all, delete-orphan"
    )
    user_categories = relationship("UserCategory", back_populates="user", cascade="all, delete-orphan")
    
    # Add relationship to Section (many-to-many)
    sections = relationship("Section", secondary=section_users, back_populates="users")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}')>"

    def get_or_create_category_state(self, category_id: int, session) -> 'UserCategory':
        """Get or create a UserCategory state for a given category."""
        user_category = session.query(UserCategory).filter_by(
            user_id=self.id,
            category_id=category_id
        ).first()
        
        if not user_category:
            user_category = UserCategory(
                user_id=self.id,
                category_id=category_id
            )
            session.add(user_category)
            session.commit()
        
        return user_category

    def update_knowledge_state(self, category_id: int, is_correct: bool, session) -> None:
        """Update the knowledge state for a category based on user performance."""
        user_category = self.get_or_create_category_state(category_id, session)
        user_category.update_knowledge_state(is_correct)
        session.commit()

# USER CATEGORY (BKT State per User-Category)
class UserCategory(Base):
    __tablename__ = "user_categories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    
    # BKT parameters with updated defaults for significantly slower learning
    current_knowledge = Column(Float, default=0.15)  # Initial knowledge matches p_init
    p_init = Column(Float, default=0.15)  # Lower initial knowledge
    p_transit = Column(Float, default=0.15)  # Much slower learning rate
    p_slip = Column(Float, default=0.15)  # Higher chance of slipping
    p_guess = Column(Float, default=0.08)  # Lower chance of guessing
    p_lapse = Column(Float, default=0.30)  # Unchanged lapse probability
    consecutive_correct = Column(Integer, default=0)  # Track consecutive correct answers
    
    # IBKT additional parameters
    performance_history = Column(PickleType, default=list)  # Store performance history as list
    total_attempts = Column(Integer, default=0)  # Total number of attempts
    correct_attempts = Column(Integer, default=0)  # Number of correct attempts
    
    # Learning style metrics
    consistency_score = Column(Float, default=0.0)
    improvement_rate = Column(Float, default=0.0)
    error_recovery = Column(Float, default=0.0)
    
    # Parameter adjustments
    transit_adjustment = Column(Float, default=0.0)
    slip_adjustment = Column(Float, default=0.0)
    guess_adjustment = Column(Float, default=0.0)
    
    # Adaptation settings
    learning_rate = Column(Float, default=0.05)
    adaptivity_threshold = Column(Integer, default=10)
    adaptation_rate = Column(Float, default=0.05)
    
    # Question manager settings
    question_history = Column(PickleType, default=dict)  # Store history of question attempts
    
    # Relationships
    user = relationship("User", back_populates="user_categories")
    category = relationship("Category", back_populates="user_categories")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_ibkt_engine()
        self._init_question_manager()

    def _init_ibkt_engine(self):
        """Initialize the IBKT engine with current parameters"""
        self.ibkt_engine = IBKTEngine(
            p_init=self.p_init,
            p_transit=self.p_transit,
            p_slip=self.p_slip,
            p_guess=self.p_guess,
            p_lapse=self.p_lapse,
            learning_rate=self.learning_rate,
            adaptivity_threshold=self.adaptivity_threshold,
            performance_history=self.performance_history,
            adaptation_rate=self.adaptation_rate
        )
        # Set counters and metrics
        self.ibkt_engine.consecutive_correct = self.consecutive_correct
        self.ibkt_engine.total_attempts = self.total_attempts
        self.ibkt_engine.correct_attempts = self.correct_attempts
        self.ibkt_engine.consistency_score = self.consistency_score
        self.ibkt_engine.improvement_rate = self.improvement_rate
        self.ibkt_engine.error_recovery = self.error_recovery
        self.ibkt_engine.transit_adjustment = self.transit_adjustment
        self.ibkt_engine.slip_adjustment = self.slip_adjustment
        self.ibkt_engine.guess_adjustment = self.guess_adjustment
        
    def _init_question_manager(self):
        """Initialize the QuestionManager for question selection"""
        from bkt.engine import QuestionManager
        
        # Create question manager with settings
        self.question_manager = QuestionManager(
            spacing_factor=2.5,      # Higher value = faster spacing increase
            error_priority=0.85,     # Higher value = more frequent repetition of wrong answers
            knowledge_penalty=0.35   # Higher value = bigger knowledge drop for previously correct items
        )
        
        # Restore question history from database if available
        if self.question_history:
            self.question_manager.question_history = self.question_history.get('history', {})
            self.question_manager.last_seen = self.question_history.get('last_seen', {})
            self.question_manager.correct_streak = self.question_history.get('streak', {})
            self.question_manager.attempt_counter = self.question_history.get('counter', 0)

    def update_knowledge_state(self, is_correct: bool, question_id=None) -> None:
        """
        Update the knowledge state using IBKT.
        
        Args:
            is_correct: Whether the answer was correct
            question_id: Optional question ID for tracking history
        """
        # First predict the new state
        predicted_knowledge = self.ibkt_engine.predict(self.current_knowledge)
        # Then update based on the actual performance
        self.current_knowledge = self.ibkt_engine.update(predicted_knowledge, is_correct)
        
        # If a question ID was provided, register the attempt with the question manager
        if question_id:
            self.register_question_attempt(question_id, is_correct, self.current_knowledge)
        
        # Save engine state back to model
        self.consecutive_correct = self.ibkt_engine.consecutive_correct
        self.performance_history = self.ibkt_engine.performance_history
        self.total_attempts = self.ibkt_engine.total_attempts
        self.correct_attempts = self.ibkt_engine.correct_attempts
        self.consistency_score = self.ibkt_engine.consistency_score
        self.improvement_rate = self.ibkt_engine.improvement_rate
        self.error_recovery = self.ibkt_engine.error_recovery
        self.transit_adjustment = self.ibkt_engine.transit_adjustment
        self.slip_adjustment = self.ibkt_engine.slip_adjustment
        self.guess_adjustment = self.ibkt_engine.guess_adjustment
        
        # Reinitialize IBKT engine with updated parameters
        self._init_ibkt_engine()
    
    def register_question_attempt(self, question_id, is_correct, knowledge_level):
        """
        Register an attempt at a specific question and update the question history.
        
        Args:
            question_id: The question's unique identifier
            is_correct: Whether the answer was correct
            knowledge_level: Current knowledge level
        """
        # Ensure the question manager is initialized
        if not hasattr(self, 'question_manager'):
            self._init_question_manager()
            
        # Register the attempt with the question manager
        adjusted_knowledge = self.question_manager.register_attempt(
            question_id, is_correct, knowledge_level
        )
        
        # If knowledge was adjusted (due to regression), update the current knowledge
        if adjusted_knowledge != knowledge_level:
            self.current_knowledge = adjusted_knowledge
            
        # Save question manager state back to the database
        self.question_history = {
            'history': self.question_manager.question_history,
            'last_seen': self.question_manager.last_seen,
            'streak': self.question_manager.correct_streak,
            'counter': self.question_manager.attempt_counter
        }

    def select_next_question(self, available_question_ids):
        """
        Select the next question to present to the user based on performance history.
        
        Args:
            available_question_ids: List of question IDs available for selection
            
        Returns:
            str: Selected question ID
        """
        # Ensure the question manager is initialized
        if not hasattr(self, 'question_manager'):
            self._init_question_manager()
            
        # Use question manager to select the next question
        return self.question_manager.select_next_question(available_question_ids)
    
    def get_question_stats(self, question_id):
        """
        Get statistics for a specific question.
        
        Args:
            question_id: The question ID to get stats for
            
        Returns:
            dict: Question statistics
        """
        # Ensure the question manager is initialized
        if not hasattr(self, 'question_manager'):
            self._init_question_manager()
            
        return self.question_manager.get_question_stats(question_id)

    def is_mastered(self, threshold: float = 0.985) -> bool:
        """Check if the user has mastered this category using a very high threshold."""
        if not hasattr(self, 'ibkt_engine'):
            self._init_ibkt_engine()
        return self.ibkt_engine.is_mastered(self.current_knowledge, threshold)

    def __repr__(self):
        return f"<UserCategory(user_id={self.user_id}, category_id={self.category_id}, knowledge={self.current_knowledge:.2f})>"

# Add event listener to initialize IBKT engine when UserCategory is loaded
@event.listens_for(UserCategory, 'load')
def init_ibkt_engine(target, context):
    target._init_ibkt_engine()
    target._init_question_manager()

# ATTEMPT LOG (User interactions)
class AttemptLog(Base):
    __tablename__ = "attempt_logs"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("options.id"))

    is_correct = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="attempts")
    question = relationship("Question")
    option = relationship("Option")

    def __repr__(self):
        return (
            f"<AttemptLog(user_id={self.user_id}, question_id={self.question_id}, "
            f"option_id={self.option_id}, is_correct={self.is_correct})>"
        )


# PROGRESS TRACKER (Optional - User progress per category)
class Progress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Accuracy as % or score for adaptive learning insights
    accuracy = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)

    user = relationship("User")
    category = relationship("Category")

    def __repr__(self):
        return (
            f"<Progress(user_id={self.user_id}, category_id={self.category_id}, "
            f"accuracy={self.accuracy}, completed={self.completed})>"
        )
