"""Pydantic request/response schemas."""
from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------- auth

class SendOTPRequest(BaseModel):
    email: EmailStr
    full_name: str = ""


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=10)
    password: str = Field(default="", max_length=128)  # optional: set login password at signup


class SetPasswordRequest(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class PasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token (JWT) from GIS button / One Tap


class DirectSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(default="", max_length=120)


class OnboardingRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    standard: int = Field(default=10, ge=10, le=10)  # GSEB Std 10 only
    medium: str = "gujarati"
    preferred_language: str = "gu"


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    standard: int | None = Field(default=None, ge=9, le=10)
    medium: str | None = None
    preferred_language: str | None = None


# ---------------------------------------------------------------- chat

class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    mode: str = "ask"
    subject_id: str | None = None
    chapter_id: str | None = None
    upload_ids: list[str] = []
    stream: bool = False


class ChatTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str = Field(pattern="^(up|down)$")
    comment: str = ""


# --------------------------------------------------------------- quiz

class QuizGenerateRequest(BaseModel):
    standard: int = Field(ge=9, le=10)
    subject_id: str
    chapter_id: str | None = None
    count: int = Field(default=5, ge=3, le=20)


class QuizSubmitRequest(BaseModel):
    answers: list[dict]


# ------------------------------------------------------- subscription

class SubscriptionCreateRequest(BaseModel):
    plan_code: str = "premium"


class SubscriptionVerifyRequest(BaseModel):
    payment_id: str
    gateway_order_id: str = ""
    gateway_payment_id: str = ""
    gateway_signature: str = ""


# ------------------------------------------------------------- admin

class SubjectCreate(BaseModel):
    standard: int = Field(ge=9, le=12)
    name_en: str
    name_gu: str
    code: str = ""
    icon: str = "📘"
    sort_order: int = 0


class ChapterCreate(BaseModel):
    subject_id: str
    number: int
    name_en: str = ""
    name_gu: str
    description: str = ""


class DocumentMeta(BaseModel):
    title: str
    standard: int = Field(ge=9, le=12)
    subject_id: str | None = None
    chapter_id: str | None = None
    source_type: str = "curated"
    academic_year: str = "2026-27"
    language: str = "gu"


class AdminStudentUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str
    standard: int | None = None
    top_k: int = 5
