from fastapi import FastAPI, WebSocket
from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator, conint, confloat
from typing import Literal, Optional, List, Dict, Any
from datetime import datetime
import pytz
from bson import ObjectId

class Admin(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    type: Literal["admin"]
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
    id: Optional[str] = Field(None, alias="_id")
    type: Literal["doctor"]
    email: str 
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
                "email": "patient1@example.com", 
                "patients": ["13234", "341324"]
            }
        }

class Nurse(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    type: Literal["nurse"]
    email: str 
    name: str
    user_id: str
    password: str
    patients: list  

    class Config:
        schema_extra = {
            "example": {
                "type": "nurse",
                "name": "nurse 1",
                "user_id": "nurse001",
                "password": "Password@123",
                "email": "patient1@example.com", 
                "patients": ["13234", "341324"]
            }
        }

class Patient(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    type: Literal["patient"]
    name: str
    user_id: str
    password: str
    email: str 
    data: List[str]
    videos: List[str]
    therapist_assigned: str
    therapist_id:str
    doctor_id: str
    doctor: str

    class Config:
        schema_extra = {
            "example": {
                "type": "patient",
                "name": "patient 1",
                "user_id": "patient001",
                "password": "Password@123",
                "email": "patient1@example.com", 
                "data": ["data1", "data2"],
                "videos": [],
                "therapist_assigned" : "No therapist assigned",
                "therapist_id": "",
                "doctor_id": "",
                "doctor": "No doctor assigned",
            }
        }

class ModelExercise(BaseModel):
    values: List[float]
    pain: List[str]
    rom: int
    rep: int
    set: int
    assigned_rep: int
    assigned_set: int
    velocity: int
    progress: str

class AssessmentModel(BaseModel):
    exercises: Dict[str, Dict[str, List[List[float]]]]


class RecoveryModel(BaseModel):
    Title: str
    Exercise: Dict[str, ModelExercise]
    pain_scale: int

class ExerciseAssigned(BaseModel):
    sets: int
    reps: int

class PersonalDetails(BaseModel):
    DORegn: str
    Accident: str
    Gender: str
    pain_indication: List[str]
    Blood_Group: str
    Height: float
    Weight: float
    BMI: float
    Age: int
    DOB: str

class PatientInformation(BaseModel):
    _id: str
    user_id: str
    patient_name: Optional[str] = None
    unique_id: str
    patient_id: str
    doctor_id: Optional[str] = None
    therapist_id: Optional[str] = None
    profession: Optional[str] = None
    PersonalDetails: Optional[PersonalDetails] = None  # type: ignore
    Assessment: Optional[List[AssessmentModel]] = None
    Model_Recovery: Optional[List[RecoveryModel]] = None
    Exercise_Assigned: Optional[Dict[str, ExerciseAssigned]] = None
    exercise_tracker: Optional[int] = None
    events_date: Optional[List[str]] = None
    PDF: Optional[List[str]] = None
    doctor_assigned: Optional[str] = None
    therapist_assigned: Optional[str] = None
    flag: int

    class Config:
        schema_extra = {
            "example": {
                "user_id": "",
                "unique_id": "WAD123",
                "patient_name" : "",
                "patient_id": "",
                "doctor_id": "",
                "therapist_id": "",
                "profession": "",
                "PersonalDetails": {
                    "DORegn": "2024-02-03",
                    "Accident": "No",
                    "Gender": "Male",
                    "pain_indication": ["Knee Pain", "Ankle Pain"],
                    "Blood_Group": "A+",
                    "Height": 175,
                    "Weight": 70,
                    "BMI": 23,
                    "Age": 22,
                    "DOB": "07/12/2001"
                },
                "Assessment": [
                    {
                        "exercises": {
                            "running": {"values": [5.0, 6.0, 7.0], "pain": ["None", "Minimal", "Moderate"], "rom": 90, "velocity": 50},
                            "pushups": {"values": [], "pain": [], "rom": 50, "velocity": 50},
                            "squats": {"values": [], "pain": [], "rom": 50, "velocity": 50},
                            "pullups": {"values": [], "pain": [], "rom": 50, "velocity": 50},
                            "LegHipRotation": {"values": [], "pain": [], "rom": 50, "velocity": 50}
                        }
                    },
                    {
                        "exercises": {
                            "running": {"values": [5.0, 6.0, 7.0], "pain": ["None", "Minimal", "Moderate"], "rom": 90, "velocity": 50},
                            "pushups": {"values": [], "pain": [], "rom": 50, "velocity": 50},
                            "squats": {"values": [], "pain": [], "rom": 50, "velocity": 50},
                            "pullups": {"values": [], "pain": [], "rom": 50, "velocity": 50},
                            "LegHipRotation": {"values": [], "pain": [], "rom": 50, "velocity": 50}
                        }
                    }
                ],
                "Model_Recovery": [
                    {
                        "Title": "Title",
                        "Exercise": {
                            "running": {"values": [5.0, 6.0, 7.0], "pain": ["None", "Minimal", "Moderate"], "rom": 90, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"},
                            "pushups": {"values": [], "pain": [], "rom": 50, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"},
                            "squats": {"values": [], "pain": [], "rom": 50, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"},
                            "pullups": {"values": [], "pain": [], "rom": 50, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"},
                            "LegHipRotation": {"values": [], "pain": [], "rom": 50, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"}
                        },
                        "pain_scale": 5
                    },
                    {
                        "Title": "Title",
                        "Exercise": {
                            "running": {"values": [5.0, 6.0, 7.0], "pain": ["None", "Minimal", "Moderate"], "rom": 90, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"},
                            "pushups": {"values": [], "pain": [], "rom": 50, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"},
                            "squats": {"values": [], "pain": [], "rom": 50, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"},
                            "pullups": {"values": [], "pain": [], "rom": 50, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"},
                            "LegHipRotation": {"values": [], "pain": [], "rom": 50, "rep": 3, "set": 3, "velocity": 50, "progress": "20%"}
                        },
                        "pain_scale": 5
                    }
                ],
                "Exercise_Assigned": {
                    "running": {"sets": 3, "reps": 12},
                    "pushups": {"sets": 4, "reps": 10},
                    "squats": {"sets": 4, "reps": 15},
                    "pullups": {"sets": 3, "reps": 8},
                    "LegHipRotation": {"sets": 3, "reps": 10}
                },
                "exercise_tracker": 1,
                "events_date": ["2024-02-10", "2024-03-10"],
                "PDF": ["path/to/patient_file.pdf", "path/to/patient_file.pdf"],
                "doctor_assigned": "Not Assigned",
                "therapist_assigned": "Not Assigned",
                "flag": 0
            }
        }


class GoogleOAuthCallback(BaseModel):
    type: Literal["admin", "doctor", "patient","nurse"]
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


