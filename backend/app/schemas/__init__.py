from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class EmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize(cls, value: str) -> str:
        return value.lower()


class Register(EmailInput):
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("name")
    @classmethod
    def meaningful_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Escribe tu nombre")
        return value.strip()


class Login(EmailInput):
    password: str = Field(min_length=1, max_length=128)


class TokenInput(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class PasswordReset(TokenInput):
    password: str = Field(min_length=12, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str | None
    name: str
    role: str
    email_verified: bool
    orcid_id: str | None


class RoleInput(BaseModel):
    role: str = Field(pattern="^(admin|curator|subscriber)$")
