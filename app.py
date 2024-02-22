from fastapi import FastAPI, WebSocket, HTTPException, Request, Depends, WebSocketDisconnect
from typing import Literal, Optional, List
from fastapi.middleware.cors import CORSMiddleware
from models import Admin, Doctor, Patient, Data
import db
from models import ConnectionManager, WebSocketManager, GoogleOAuthCallback,DeleteRequest,PatientInformation, ExercisesGiven, Exercises
from db import get_user_from_db,metrics,deleteData,patients, users, rooms_collection, signaling_collection
import json
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from authlib.integrations.starlette_client import OAuth
from datetime import datetime, timezone
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util,ObjectId


app = FastAPI()
manager = ConnectionManager()

storedData = []
websocket_list=[]
websocket_connections = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jinja2 templates configuration
templates = Jinja2Templates(directory="templates")

# Initialize OAuth instance
oauth = OAuth()

# OAuth configuration for Google
oauth.register(
    name='google',
    client_id='94330389608-e14ildo3ntq6l76np77dv6l98akv1kkp.apps.googleusercontent.com',
    client_secret='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',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    authorize_prompt_params=None,
    authorize_prompt_template=None,
    token_url='https://accounts.google.com/o/oauth2/token',
    redirect_uri='https://localhost:3000/diagnostics'
)

# OAuth configuration for LinkedIn
oauth.register(
    name='linkedin',
    client_id='YOUR_LINKEDIN_CLIENT_ID',
    client_secret='YOUR_LINKEDIN_CLIENT_SECRET',
    authorize_url='https://www.linkedin.com/oauth/v2/authorization',
    authorize_params=None,
    authorize_prompt_params=None,
    authorize_prompt_template=None,
    token_url='https://www.linkedin.com/oauth/v2/accessToken',
    redirect_uri='YOUR_LINKEDIN_REDIRECT_URI'
)

# OAuth configuration for Facebook
oauth.register(
    name='facebook',
    client_id='YOUR_FACEBOOK_APP_ID',
    client_secret='YOUR_FACEBOOK_APP_SECRET',
    authorize_url='https://www.facebook.com/v12.0/dialog/oauth',
    authorize_params=None,
    authorize_prompt_params=None,
    authorize_prompt_template=None,
    token_url='https://graph.facebook.com/v12.0/oauth/access_token',
    redirect_uri='YOUR_FACEBOOK_REDIRECT_URI'
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

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    websocket_list.append((user_id, websocket))

    try:
        while True:
            data = await websocket.receive_text()
            await broadcast_message(user_id, f"You sent: {data}")
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
    finally:
        remove_websocket(user_id, websocket)

async def broadcast_message(sender_user_id, message):
    for user_id, ws in websocket_list:
        if user_id != sender_user_id:
            await ws.send_text(message)

def remove_websocket(user_id, websocket):
    websocket_list.remove((user_id, websocket))



@app.post("/post-data/{data}")
def postData(data: str):
    try:
        # Get current date and time in IST
        current_datetime_ist = datetime.now().astimezone(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
        data_with_timestamp = f"{current_datetime_ist}: {data}"
        storedData.append(data_with_timestamp)
        return {"inserted": "true"}
    except Exception as e:
        return {"inserted": "false", "error": str(e)}


@app.delete("/delete-data")
async def delete_data(request: DeleteRequest):
    try:
        result = await deleteData(request)
        if result["deleted"]:
            return {"message": "Data deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to delete data: {result['error']}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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

@app.post("/google-login")
async def google_login(data: GoogleOAuthCallback):
    try:
        # Check if the user already exists in the database based on the email address
        existing_patient = await db.users.find_one({"email": data.email})
        if existing_patient:
            # If the user already exists, you can return an error or handle it as needed
            return {"message": "Login successful"}
        else:
            # If the user doesn't exist, return an error or handle it as needed
            raise HTTPException(status_code=401, detail="Unauthorized: User not found")
        # If the user doesn't exist, create a new patient record
        # res = await db.createPatient(data=data)
        # return {"userCreated": res}
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/login")
async def initiate_login(user_id: str, password: str, provider: Optional[str] = None):
    if provider:  # Social media login
        if provider not in ["google", "linkedin", "facebook"]:
            raise HTTPException(status_code=400, detail="Invalid social media provider")
        # Redirect the user to the social media login endpoint # Not sure where res is coming from, might need adjustment
        return res["data"]  # Not sure where res is coming from, might need adjustment

    # Traditional username/password login logic
    res = await db.loginUser(user_id, password)
    if res["loginStatus"] == True:
        return res["data"]
    
@app.route("/login/{provider}/callback")
async def social_media_callback(request: Request, provider: str):
    token = await oauth.create_client(provider).authorize_access_token(request)
    user_info = await oauth.create_client(provider).parse_id_token(request, token)
    # Handle user information obtained from the OAuth provider (e.g., store in database, generate JWT token)
    # ...

    # For demonstration purposes, render a template with user information
    return templates.TemplateResponse("social_media_callback.html", {"request": request, "user_info": user_info})

@app.get("/get-all-user/{type}")
async def getUsers(type: Literal["admin", "doctor", "patient", "all"]):
    res = await db.getAllUser(type)
    return res

@app.get("/get-user/{type}/{id}")
async def getUsers(type: Literal["admin", "doctor", "patient"], id: str):
    res = await db.getUser(type, id)
    return res

@app.post("/post-data")
async def addData(user_id: str, data: Data):
    res = await db.postData(user_id=user_id, data=data)
    
    # Convert the data to a JSON string
    data_json = json.dumps(data.dict())

    # Iterate over each WebSocket in websocket_list
    for uid, websocket in websocket_list:
        if uid == user_id:
            # Send the data only to the user who posted it
            await websocket.send_text(data_json)

    return {"dataCreated": res}

@app.put("/put-data")
async def addData( data: Data):
    res = await db.putData(data=data)
    return{"dataCreated": res}

@app.post("/metrics")
async def getData(data_id: list):
    res = await db.getData(data_id)
    return res

@app.post("/patient-info/")
async def create_patient_info(patient_info: PatientInformation):
    # Convert Pydantic model to JSON-compatible dict
    patient_info_dict = jsonable_encoder(patient_info)

    # Check if a document with the same user_id already exists
    existing_patient = await patients.find_one({"user_id": patient_info_dict["user_id"]})
    if existing_patient:
        raise HTTPException(status_code=400, detail="Patient with the same user_id already exists")

    # Insert the data into MongoDB
    result = await patients.insert_one(patient_info_dict)

    if result.inserted_id:
        # Convert ObjectId to string for JSON serialization
        patient_info_dict["_id"] = str(patient_info_dict["_id"])

        # Notify clients about the new patient with JSON object
        message = {"event": "new_patient", "data": patient_info_dict}
        await notify_clients(message)

        return {"message": "Patient information created successfully"}

    raise HTTPException(status_code=500, detail="Failed to create patient information")

@app.put("/update-exercise-info/{patient_id}/{new_flag}")
async def update_exercise_info(patient_id: str, exercise_data: Exercises, new_flag: int):
    # Check if a document with the specified user_id exists
    existing_patient = await patients.find_one({"patient_id": patient_id})
    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update the exercise information
    result = await patients.update_one(
        {"patient_id": patient_id},
        {"$set": {
            "Exercises": exercise_data.dict(),
            "flag": new_flag
        }}
    )

    if result.modified_count > 0:
        # Fetch the updated item from the database
        updated_todo = await patients.find_one({"patient_id": patient_id})

        # If the flag is in the range 1 to 5, send the entire updated_todo data through the WebSocket
        if new_flag in range(-2,6):
            await send_websocket_message(json_util.dumps(updated_todo, default=json_util.default))
        
        return {"message": "Exercise information updated successfully"}

    raise HTTPException(status_code=500, detail="Failed to update exercise information")

async def send_websocket_message(message: str):
    for websocket in websocket_connections:
        await websocket.send_text(message)

@app.put("/update_given_exercise_info/{patient_id}/{new_flag}")
async def update_given_exercise_info(patient_id: str, exercise_data: ExercisesGiven, new_flag: int):
    # Check if a document with the specified patient_id exists
    existing_patient = await patients.find_one({"patient_id": patient_id})
    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update the exercise information and flag
    result = await patients.update_one(
        {"patient_id": patient_id},
        {"$set": {
            "exercises_given": exercise_data.dict(),
            "flag": new_flag
        }}
    )

    if result.modified_count > 0:
        # Fetch the updated item from the database
        updated_todo = await patients.find_one({"patient_id": patient_id})

        # If the flag is in the range 1 to 5, send the entire updated_todo data through the WebSocket
        if new_flag in range(-2,6):
            await send_websocket_message(json_util.dumps(updated_todo, default=json_util.default))
        
        return {"message": "Exercise information updated successfully"}

    raise HTTPException(status_code=500, detail="Failed to update exercise information")

async def send_websocket_message(message: str):
    for websocket in websocket_connections:
        await websocket.send_text(message)

@app.put("/update_flag/{patient_id}/{new_flag}/{doctor_name}/{doctor_id}/{schedule_start_date}/{meeting_id}")
async def update_flag(patient_id: str, new_flag: int, doctor_name: str, doctor_id: str, schedule_start_date: str,meeting_id: str):
    # Fetch the item from the database using the provided item_id
    todo = await patients.find_one({"patient_id": patient_id})

    # Check if the item exists
    if not todo:
        raise HTTPException(status_code=404, detail="Item not found")

    # Update only the "schedule_start_date" within the "health_tracker" field
    await patients.update_one(
        {"patient_id": patient_id},
        {"$set": {"flag": new_flag, 
                  "doctor_assigned": doctor_name, 
                  "doctor_id": doctor_id, 
                  "health_tracker.schedule_start_date": schedule_start_date,
                  "health_tracker.meeting_link": meeting_id}}
    )

    # Fetch the updated item from the database
    updated_todo = await patients.find_one({"patient_id": patient_id})

    # If the flag is 1, send the entire updated_todo data through the WebSocket
    if new_flag in range(-2,6):
        await send_websocket_message(json_util.dumps(updated_todo, default=json_util.default))

    # You can return the updated item if needed
    return "successful"

@app.get("/patient-info/{patient_id}")
async def get_patient_info(patient_id: str):
    # Check if a document with the specified user_id exists
    existing_patient = await patients.find_one({"patient_id": patient_id})
    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Convert the retrieved data to a Pydantic model
    # patient_info = PatientInformation(**existing_patient)
    existing_patient["_id"] = str(existing_patient["_id"])

    return existing_patient

@app.get("/patient-details/all", response_model=List[dict])
async def get_all_patient_info():
    # Retrieve all patient information from the "patients" collection
    all_patients = await patients.find().to_list(1000)  # Adjust the batch size as needed

    # Check if there are any patients in the collection
    if not all_patients:
        raise HTTPException(status_code=404, detail="No patient information found")
    
    # Convert ObjectId to string for each document
    for patient in all_patients:
        patient['_id'] = str(patient['_id'])

    return all_patients

async def notify_clients(data: dict):
    for connection in websocket_connections:
        await connection.send_json(data)

# WebSocket endpoint
@app.websocket("/patients")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.append(websocket)
    try:
        print("HI")
        while True:
            data = await websocket.receive_text()
            
            # Process data or interact with the WebSocket connection
            await handle_websocket_data(websocket, data)
    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup on WebSocket disconnect
        websocket_connections.remove(websocket)

async def handle_websocket_data(websocket: WebSocket, data: str):
    # Process data or interact with the WebSocket connection

    # For example, check if data is related to flag update
    if data.startswith("update_flag"):
        _, item_id, new_flag, doctor_name = data.split("/")
        await update_flag(item_id, int(new_flag), doctor_name)

    # For bidirectional communication, you can send data back to the client
    bidirectional_data = {"message": "Hello from the server!"}
    await websocket.send_text(json.dumps(bidirectional_data))

async def update_flag(item_id: str, new_flag: int, doctor_name: str):
    # Implement your logic to update the flag in the database or perform other actions
    print(f"Updating flag for item {item_id} to {new_flag} by doctor {doctor_name}")

@app.get("/users", response_model=List[dict])
async def get_all_users():
    users_data = await users.find({}).to_list(length=None)
    # Convert ObjectId to string for each document
    for user in users_data:
        user['_id'] = str(user['_id'])
    return users_data

@app.get("/check_patient/{patient_id}")
async def check_patient(patient_id: str):
    # Check if the patient ID exists in the MongoDB collection
    patient = await patients.find_one({"patient_id": patient_id})
    if patient:
        return True
    else:
        return False
    
@app.get("/get_flags/{patient_id}")
async def get_flags(patient_id: str):
    # Check if the patient ID exists in the MongoDB collection
    patient = await patients.find_one({"patient_id": patient_id})
    if patient:
        flags = patient.get("flag", [])
        return {"flags": flags}
    else:
        raise HTTPException(status_code=404, detail=f"Patient with ID {patient_id} not found")

# @app.post("/doctor-patient-info/")
# async def create_doctor_patient_info(patient_info: DoctorPatientInformation):
#     patient_info_dict = jsonable_encoder(patient_info)

#     existing_patient = await doctor_patient.find_one({"patient.patient_id": patient_info.patient.patient_id})
#     if existing_patient:
#         raise HTTPException(status_code=400, detail="Patient with the same patient_id already exists")

#     result = await doctor_patient.insert_one(patient_info_dict)

#     if result.inserted_id:
#         patient_info_dict["_id"] = str(patient_info_dict["_id"])
#         return {"message": "Doctor-Patient information created successfully"}

#     raise HTTPException(status_code=500, detail="Failed to create doctor-patient information")

# @app.put("/update-assigned-exercises/{patient_id}")
# async def update_assigned_exercises(patient_id: str, assigned_exercises: AssignedExercises):
#     # Check if the patient exists
#     existing_patient = await doctor_patient.find_one({"patient.patient_id": patient_id})
#     if not existing_patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     # Update assigned exercises
#     result = await doctor_patient.update_one(
#         {"patient.patient_id": patient_id},
#         {"$set": {"assigned_exercises": assigned_exercises.dict()}}
#     )

#     if result.modified_count == 1:
#         return {"message": "Assigned exercises updated successfully"}

#     raise HTTPException(status_code=500, detail="Failed to update assigned exercises")

# @app.put("/update-exercises-given/{patient_id}")
# async def update_exercises_given(patient_id: str, exercises_given: ExercisesGiven):
#     # Check if the patient exists
#     existing_patient = await doctor_patient.find_one({"patient.patient_id": patient_id})
#     if not existing_patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     # Update exercises given
#     result = await doctor_patient.update_one(
#         {"patient.patient_id": patient_id},
#         {"$set": {"exercises_given": exercises_given.dict()}}
#     )

#     if result.modified_count == 1:
#         return {"message": "Exercises given updated successfully"}

#     raise HTTPException(status_code=500, detail="Failed to update exercises given")