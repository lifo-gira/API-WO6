from fastapi import FastAPI, WebSocket
from typing import Literal
from fastapi.middleware.cors import CORSMiddleware
from models import Admin, Doctor, Patient, Data
import db
from models import ConnectionManager, WebSocketManager
from db import get_user_from_db,metrics
import json


app = FastAPI()
manager = ConnectionManager()

storedData = []
websocket_list=[]

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"Message": "use '/docs' endpoint to find all the api related docs "}

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     if websocket not in websocket_list:
#         websocket_list.append(websocket)
#     while True:
#         data = await websocket.receive_text()
#         await websocket.send_text(f"You sent: {data}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_list.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"You sent: {data}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if websocket in websocket_list:
            websocket_list.remove(websocket)


@app.post("/post-data/{data}")
def postData(data):
    try:
        storedData.append(data)
        return {"inserted": "true"}
    except:
        return {"inserted": "false"}

@app.get("/get-all-data")
def getData():
    return storedData

    
@app.post("/create-adminuser")
async def createAdminUser(data: Admin):
    res = await db.createAdminUser(data=data)
    return{"userCreated": res} 

@app.post("/create-doctor")
async def createDoctor(data: Doctor):
    res = await db.createDoctor(data=data)
    return{"userCreated": res}

@app.post("/create-patient")
async def createPatient(data: Patient):
    res = await db.createPatient(data=data)
    return{"userCreated": res}

@app.post("/login")
async def initiateLogin(user_id: str, password: str):
    res = await db.loginUser(user_id, password) 
    if res["loginStatus"] == True:
        return res["data"]

@app.get("/get-all-user/{type}")
async def getUsers(type: Literal["admin", "doctor", "patient", "all"]):
    res = await db.getAllUser(type)
    return res

@app.get("/get-user/{type}/{id}")
async def getUsers(type: Literal["admin", "doctor", "patient"], id: str):
    res = await db.getUser(type, id)
    return res

@app.post("/post-data")
async def addData(user_id: str,data: Data):
    res = await db.postData(user_id=user_id, data=data)
    for web in websocket_list:
        data_json = json.dumps(data.dict())
        await web.send_text(data_json)
        return{"dataCreated": res}

@app.put("/put-data")
async def addData( data: Data):
    res = await db.putData(data=data)
    return{"dataCreated": res}

@app.post("/metrics")
async def getData(data_id: list):
    res = await db.getData(data_id)
    return res




