from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

class Admin(BaseModel):
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
                "doctor": "doctor001"
                
            }
        }


class Data(BaseModel):
    data_id: str
    device_id: str
    series: list

    class Config:
        schema_extra = {
            "example": {
                "data_id": "adsfjh", 
                "device_id": "device1",
                "series": []
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

