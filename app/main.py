from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .database import Base, engine, get_db
from . import models, schemas
from .security import hash_password, verify_password, create_access_token
from .dependencies import get_current_user, require_admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Create a starter admin account only when no admin exists.
    db = next(get_db())
    try:
        if not db.query(models.User).filter(models.User.role == "admin").first():
            db.add(models.User(username="admin", password_hash=hash_password("Admin@123"), role="admin"))
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(title="Hostel Management API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def refresh_room_status(room):
    if room:
        room.status = "Full" if room.occupied >= room.capacity else "Available"

def assign_room(db: Session, student, new_room_id):
    old_room = db.query(models.Room).filter(models.Room.id == student.room_id).first() if student.room_id else None
    new_room = db.query(models.Room).filter(models.Room.id == new_room_id).first() if new_room_id else None
    if new_room_id and not new_room:
        raise HTTPException(status_code=404, detail="Room not found")
    if new_room and (not old_room or new_room.id != old_room.id) and new_room.occupied >= new_room.capacity:
        raise HTTPException(status_code=400, detail="Selected room is full")
    if old_room and (not new_room or old_room.id != new_room.id):
        old_room.occupied = max(0, old_room.occupied - 1)
        refresh_room_status(old_room)
    if new_room and (not old_room or new_room.id != old_room.id):
        new_room.occupied += 1
        refresh_room_status(new_room)
    student.room_id = new_room.id if new_room else None

@app.get("/")
def root():
    return {"message": "Hostel Management API is running", "docs": "/docs"}

@app.post("/api/auth/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"access_token": create_access_token(user.username), "token_type": "bearer", "user": user}

@app.get("/api/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user

@app.get("/api/students", response_model=list[schemas.StudentOut])
def list_students(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    return db.query(models.Student).order_by(models.Student.id.desc()).all()

@app.post("/api/students", response_model=schemas.StudentOut, status_code=201)
def create_student(payload: schemas.StudentCreate, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    if db.query(models.Student).filter(models.Student.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = models.User(username=payload.username, password_hash=hash_password(payload.password), role="student")
    db.add(user)
    db.flush()
    student = models.Student(full_name=payload.full_name, email=payload.email, phone=payload.phone,
                              course=payload.course, user_id=user.id)
    db.add(student)
    if payload.room_id:
        assign_room(db, student, payload.room_id)
    db.commit()
    db.refresh(student)
    return student

@app.get("/api/students/me", response_model=schemas.StudentOut)
def my_student_record(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student

@app.put("/api/students/{student_id}", response_model=schemas.StudentOut)
def update_student(student_id: int, payload: schemas.StudentUpdate, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data:
        duplicate = db.query(models.Student).filter(models.Student.email == data["email"], models.Student.id != student_id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Email already exists")
    if "room_id" in data:
        assign_room(db, student, data.pop("room_id"))
    for key, value in data.items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student

@app.delete("/api/students/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.room_id:
        room = db.query(models.Room).filter(models.Room.id == student.room_id).first()
        if room:
            room.occupied = max(0, room.occupied - 1)
            refresh_room_status(room)
    if student.user_id:
        user = db.query(models.User).filter(models.User.id == student.user_id).first()
        if user:
            db.delete(user)
    db.delete(student)
    db.commit()
    return None

@app.get("/api/rooms", response_model=list[schemas.RoomOut])
def list_rooms(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Room).order_by(models.Room.room_number).all()

@app.post("/api/rooms", response_model=schemas.RoomOut, status_code=201)
def create_room(payload: schemas.RoomCreate, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    if db.query(models.Room).filter(models.Room.room_number == payload.room_number).first():
        raise HTTPException(status_code=409, detail="Room number already exists")
    room = models.Room(**payload.model_dump(), occupied=0, status="Available")
    db.add(room)
    db.commit()
    db.refresh(room)
    return room

@app.put("/api/rooms/{room_id}", response_model=schemas.RoomOut)
def update_room(room_id: int, payload: schemas.RoomUpdate, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    data = payload.model_dump(exclude_unset=True)
    if "room_number" in data:
        duplicate = db.query(models.Room).filter(models.Room.room_number == data["room_number"], models.Room.id != room_id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Room number already exists")
    if "capacity" in data and data["capacity"] < room.occupied:
        raise HTTPException(status_code=400, detail="Capacity cannot be lower than current occupancy")
    for key, value in data.items():
        setattr(room, key, value)
    refresh_room_status(room)
    db.commit()
    db.refresh(room)
    return room

@app.delete("/api/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.occupied:
        raise HTTPException(status_code=400, detail="Cannot delete a room that has students assigned")
    db.delete(room)
    db.commit()
    return None
