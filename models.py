from fastapi import FastAPI, WebSocket
from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator, conint, confloat
from typing import Literal, Optional, List
from datetime import datetime
import pytz
from bson import ObjectId

class Admin(BaseModel):
    id: str = Field(..., alias="_id")
    type: Literal["admin", "doctor", "patient"]
    name: str
    user_id: str
    password: str

    class Config:
        schema_extra = {
            "example": {
                "type": "admin",
                "name": "admin 1",
                "user_id": "admin001",
                "password": "Password@123"
            }
        }

class Doctor(BaseModel):
    id: str = Field(..., alias="_id")
    type: Literal["admin", "doctor", "patient"]
    name: str
    user_id: str
    password: str
    patients: list  

    class Config:
        schema_extra = {
            "example": {
                "type": "doctor",
                "name": "doctor 1",
                "user_id": "doctor001",
                "password": "Password@123",
                "patients": ["13234", "341324"]
            }
        }

class Patient(BaseModel):
    id: str = Field(..., alias="_id")
    type: Literal["admin", "doctor", "patient"]
    name: str
    user_id: str
    password: str
    data: list
    videos: list
    doctor: str



    class Config:
        schema_extra = {
            "example": {
                "type": "patient",
                "name": "patien 1",
                "user_id": "patient001",
                "password": "Password@123",
                "data": ["data1", "data2"],
                "videos": [],
                "doctor": "doctor001",
            }
        }

class HealthCheckupDetails(BaseModel):
    selectedDate: str

class PatientDetails(BaseModel):
    Accident: str
    Gender: str

class PersonalDetails(BaseModel):
    categories: List[str]
    healthcheckup: HealthCheckupDetails
    PatientDetails: PatientDetails
    Reports: List[str]
    Height: float
    Weight: float
    BMI: float
    Age: int

class Exercise(BaseModel):
    name: str
    values: List[float]
    pain: List[str]
    rom: Optional[int]

# Define your Exercises model
class Exercises(BaseModel):
    data: List[Exercise]

class ExercisesGiven(BaseModel):
    data: List[dict]

class HealthTracker(BaseModel):
    exercise_tracker: bool
    meeting_link: Optional[str]
    schedule_start_date: str
    schedule_end_date: str

class PatientInformation(BaseModel):
    _id: str
    user_id: str
    patient_id: str
    doctor_id: str
    profession: str
    PersonalDetails: PersonalDetails
    Exercises: Exercises
    exercises_given: ExercisesGiven
    health_tracker: HealthTracker
    PDF: str
    doctor_assigned: str
    flag: int

    class Config:
        schema_extra = {
            "example": {
                "user_id": "",
                "patient_id": "",
                "doctor_id": "",
                "profession": "",
                "PersonalDetails": {
                    "categories": ["Category1", "Category2"],
                    "healthcheckup": {
                        "selectedDate": "2024-02-03",
                    },
                    "PatientDetails": {
                        "Accident": "No",
                        "Gender": "Male",
                    },
                    "Reports": ["Report1", "Report2"],
                    "Height": 175,
                    "Weight": 70,
                    "BMI": 23,
                    "Age": 22,
                },
                "Exercises": {
                    "running": {"values": [5.0, 6.0, 7.0], "pain": ["None", "Minimal", "Moderate"], "rom": 90},
                    "pushups": {"values": [], "pain": [], "rom": None},
                    "squats": {"values": [], "pain": [], "rom": None},
                    "pullups": {"values": [], "pain": [], "rom": None},
                    "LegHipRotation": {"values": [], "pain": [], "rom": None},
                },
                "exercises_given": {
                    "running": {"rep": 10, "set": 3},
                    "pushups": {"rep": 12, "set": 3},
                    "squats": {"rep": 15, "set": 3},
                    "pullups": {"rep": 8, "set": 3},
                },
                "health_tracker": {
                    "exercise_tracker": True,
                    "meeting_link": "https://example.com/meeting",
                    "schedule_start_date": "2024-02-10",
                    "schedule_end_date": "2024-03-10",
                },
                "PDF": "path/to/patient_file.pdf",
                "doctor_assigned": "DoctorName",
                "flag": 0,
            }
        }

class GoogleOAuthCallback(BaseModel):
    type: Literal["admin", "doctor", "patient"]
    name: str
    email: EmailStr
    user_id: str
    password: str
    data: list
    videos: list
    doctor: str

    class Config:
        schema_extra = {
            "example": {
                "type": "patient",
                "name": "patien 1",
                "email": "user@example.com",
                "user_id": "patient001",
                "password": "Password@123",
                "data": ["data1", "data2"],
                "videos": [],
                "doctor": "doctor001"
            }
        }


class DeleteRequest(BaseModel):
    device_id: str
    start_date: str
    start_time: str
    end_date: str
    end_time: str

    class Config:
        schema_extra = {
            "example": {
                "device_id": "asdsadf",
                "start_date": "2023-11-01",
                "start_time": "08:00:00",
                "end_date": "2023-11-02",
                "end_time": "18:00:00",
            }
        }
    
class Data(BaseModel):
    data_id: str
    device_id: str
    series: list
    created_date: str = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d')
    created_time: str = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S')

    class Config:
        schema_extra = {
            "example": {
                "data_id": "adsfjh", 
                "device_id": "device1",
                "series": [],
                "created_date": "2023-11-04",
                "created_time": "14:30:00"
            }
        }

class WebSocketManager:
    def __init__(self):
        self.connections = {}
    
    def subscribe(self, websocket, user_type, user_id):
        # Add the WebSocket connection to the relevant subscription list
        key = (user_type, user_id)
        if key not in self.connections:
            self.connections[key] = []
        self.connections[key].append(websocket)

    def unsubscribe(self, websocket, user_type, user_id):
        # Remove the WebSocket connection from the subscription list
        key = (user_type, user_id)
        if key in self.connections:
            self.connections[key].remove(websocket)
            if not self.connections[key]:
                del self.connections[key]

    async def notify_subscribers(self, user_type, user_id, message):
        # Send a message to all WebSocket clients subscribed to the user_type and user_id
        key = (user_type, user_id)
        if key in self.connections:
            for websocket in self.connections[key]:
                await websocket.send_json(message)


class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)


