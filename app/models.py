from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")
    student = relationship("Student", back_populates="user", uselist=False)

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String(20), unique=True, index=True, nullable=False)
    capacity = Column(Integer, nullable=False, default=1)
    occupied = Column(Integer, nullable=False, default=0)
    room_type = Column(String(30), nullable=False, default="Standard")
    status = Column(String(20), nullable=False, default="Available")
    students = relationship("Student", back_populates="room")

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    phone = Column(String(25), nullable=True)
    course = Column(String(100), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    room = relationship("Room", back_populates="students")
    user = relationship("User", back_populates="student")
