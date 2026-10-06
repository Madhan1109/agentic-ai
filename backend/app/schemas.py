from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = (value or "").strip().lower()
        if "@" not in email:
            raise ValueError("Enter a full work email, including @")
        return email


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee_id: str
    full_name: str
    email: str
    department: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


class ToolTraceItem(BaseModel):
    tool: str | None = None
    args: dict | None = None
    output: str | None = None
    type: str


class ChatResponse(BaseModel):
    answer: str
    employee_id: str
    tool_trace: list[ToolTraceItem] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str
    llm_provider: str = "local"
