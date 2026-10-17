from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, Literal

class LoginIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class RoomBase(BaseModel):
    room_number: str = Field(min_length=1, max_length=20)
    capacity: int = Field(ge=1, le=100)
    room_type: str = Field(default="Standard", max_length=30)

class RoomCreate(RoomBase):
    pass

class RoomUpdate(BaseModel):
    room_number: Optional[str] = Field(default=None, min_length=1, max_length=20)
    capacity: Optional[int] = Field(default=None, ge=1, le=100)
    room_type: Optional[str] = Field(default=None, max_length=30)

class RoomOut(BaseModel):
    id: int
    room_number: str
    capacity: int
    occupied: int
    room_type: str
    status: str
    model_config = ConfigDict(from_attributes=True)

class StudentBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    course: Optional[str] = None
    room_id: Optional[int] = None

class StudentCreate(StudentBase):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    room_id: Optional[int] = None

class StudentOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: Optional[str]
    course: Optional[str]
    room_id: Optional[int]
    user_id: Optional[int]
    model_config = ConfigDict(from_attributes=True)
