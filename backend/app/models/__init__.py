"""Import all models so Base.metadata knows every table."""
from app.models.user import User
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk
from app.models.conversation import Conversation, Message
from app.models.upload import Upload
from app.models.subscription import Plan, Subscription, Payment, Usage
from app.models.quiz import QuizQuestion, QuizAttempt
from app.models.progress import StudentProgress, Feedback

__all__ = [
    "User", "Subject", "Chapter", "KnowledgeDocument", "KnowledgeChunk",
    "Conversation", "Message", "Upload", "Plan", "Subscription", "Payment",
    "Usage", "QuizQuestion", "QuizAttempt", "StudentProgress", "Feedback",
]
