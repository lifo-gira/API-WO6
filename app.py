from fastapi import Body, FastAPI, WebSocket, HTTPException, Request, Depends, WebSocketDisconnect
from typing import Literal, Optional, List, Union
from fastapi.middleware.cors import CORSMiddleware
from models import Admin, AssessmentModel, Dicom, Doctor, ExerciseAssigned, Nurse, Patient, Data, RecoveryModel
import db
from models import ConnectionManager, WebSocketManager, GoogleOAuthCallback,DeleteRequest,PatientInformation,DicomData 
from db import get_user_from_db,metrics,deleteData,patients, users, rooms_collection, signaling_collection, dicom
import json
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from authlib.integrations.starlette_client import OAuth
from datetime import datetime, timezone
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util,ObjectId
import asyncio
from typing import Dict, List

app = FastAPI()
manager = ConnectionManager()

storedData = {}
websocket_list: Dict[str, WebSocket] = {}
websocket_connections = []
message_queues: Dict[str, asyncio.Queue] = {}
pending_messages: Dict[str, List[str]] = {}
lock = asyncio.Lock()

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
    async with lock:
        websocket_list[user_id] = websocket
        if user_id in pending_messages:
            for message in pending_messages[user_id]:
                await send_message(websocket, message)
            pending_messages.pop(user_id, None)

    print(f"User {user_id} connected")

    message_queue = asyncio.Queue()
    async with lock:
        message_queues[user_id] = message_queue

    try:
        while True:
            data = await websocket.receive_text()
            await message_queue.put(data)
            await process_message_queue(user_id, message_queue)
    except WebSocketDisconnect:
        print(f"User {user_id} disconnected")
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
    finally:
        await remove_websocket(user_id)

async def process_message_queue(user_id: str, queue: asyncio.Queue):
    while not queue.empty():
        message = await queue.get()
        await broadcast_message(user_id, f"You sent: {message}")

async def broadcast_message(sender_user_id: str, message: str):
    async with lock:
        send_tasks = []
        for user_id, ws in websocket_list.items():
            if user_id != sender_user_id:
                send_tasks.append(send_message_with_ack(user_id, ws, message))
        await asyncio.gather(*send_tasks, return_exceptions=True)

async def send_message_with_ack(user_id: str, websocket: WebSocket, message: str):
    try:
        await websocket.send_text(message)
        # Simulate an acknowledgment mechanism using message_id
        # For example, the client sends back "ACK:message_id" which could be parsed and validated here
        # However, here we assume messages are acknowledged in the next receive cycle
    except Exception as e:
        print(f"Error sending message to user {user_id}: {e}")
        async with lock:
            if user_id not in pending_messages:
                pending_messages[user_id] = []
            pending_messages[user_id].append(message)

async def send_message(websocket: WebSocket, message: str):
    try:
        await websocket.send_text(message)
    except Exception as e:
        print(f"Error sending message to websocket: {e}")

async def remove_websocket(user_id: str):
    async with lock:
        if user_id in websocket_list:
            websocket_list.pop(user_id, None)
        if user_id in message_queues:
            message_queues.pop(user_id, None)
        print(f"User {user_id} removed")

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

@app.post("/create-nurse")
async def createNurse(data: Nurse):
    res = await db.createNurse(data=data)
    return{"userCreated": res}

@app.get("/patients/{email}", response_model=Patient)
async def get_patient(email: str):
    # Retrieve patient data from the users collection
    patient_data = await users.find_one({"email": email})
    if patient_data is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Convert ObjectId to string for _id
    patient_data["_id"] = str(patient_data["_id"])  # Convert ObjectId to string

    # Convert MongoDB document to Patient model
    patient = Patient(**patient_data)
    return patient

@app.post("/create-patient")
async def create_patient(data: Patient):
    try:
        # Convert Pydantic model to a JSON-compatible dictionary
        patient_dict = jsonable_encoder(data)
        
        # MongoDB automatically generates _id, so remove it from the request
        patient_dict.pop("_id", None)

        # Insert the patient into the users collection
        result = await users.insert_one(patient_dict)

        if result.inserted_id:
            patient_id = str(result.inserted_id)  # Get the MongoDB-generated _id as a string
            # Create a minimal PatientInformation entry
            patient_info = {
                "user_id": patient_dict["user_id"],
                "patient_id": patient_id,
                "therapist_id": patient_dict["therapist_id"],
                "therapist_assigned": patient_dict["therapist_assigned"],
                "flag": -3
            }

            # Insert the minimal PatientInformation entry into the patients collection
            patient_info_result = await patients.insert_one(patient_info)

            if patient_info_result.inserted_id:
                return {"message": "Patient and PatientInformation created successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to create PatientInformation")

    except Exception as e:
        # Log and handle the exception
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    # If insertion fails
    raise HTTPException(status_code=500, detail="Failed to create patient")


    
User = Union[Doctor, Patient]

@app.get("/users/{email}", response_model=User)
async def get_user(email: str):
    # Retrieve user data from the users collection
    user_data = await users.find_one({"email": email})
    if user_data is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert ObjectId to string for _id
    user_data["_id"] = str(user_data["_id"])  # Convert ObjectId to string

    # Check the type and return the appropriate model
    user_type = user_data.get("type")
    if user_type == "doctor":
        user = Doctor(**user_data)
    elif user_type == "patient":
        user = Patient(**user_data)
    else:
        raise HTTPException(status_code=400, detail="Invalid user type")
    
    return user

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
async def getUsers(type: Literal["admin", "doctor", "patient","nurse"]):
    res = await db.getAllUser(type)
    return res

@app.get("/get-user/{type}/{id}")
async def getUsers(type: Literal["admin", "doctor", "patient","nurse"], id: str):
    res = await db.getUser(type, id)
    return res

@app.post("/post-data")
async def addData(user_id: str, data: Data):
    # Simulate data storage operation
    try:
        res = await db.postData(user_id=user_id, data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing data: {e}")

    # Convert the data to a JSON string once
    data_json = json.dumps(data.dict())

    async with lock:
        websocket = websocket_list.get(user_id)
        if websocket:
            try:
                await send_message_with_ack(user_id, websocket, data_json)
            except Exception as e:
                print(f"Error sending data to user {user_id}: {e}")
        else:
            # Store the message if the user is not currently connected
            if user_id not in pending_messages:
                pending_messages[user_id] = []
            pending_messages[user_id].append(data_json)

    return {"dataCreated": res}

# @app.post("/post-data")
# async def addData(user_id: str,data: Data):
#     res = await db.postData(user_id=user_id, data=data)
#     for web in websocket_list:
#         data_json = json.dumps(data.dict())
#         await web.send_text(data_json)
#         return{"dataCreated": res}

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

@app.patch("/patient-info/{patient_id}")
async def update_patient_info(patient_id: str, update_data: dict = Body(...)):
    # Same logic for handling the patch
    existing_patient = await patients.find_one({"patient_id": patient_id})
    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_data = jsonable_encoder(update_data)

    update_result = await patients.replace_one(
        {"patient_id": patient_id},
        update_data
    )

    if update_result.modified_count > 0:
        updated_patient = await patients.find_one({"patient_id": patient_id})
        updated_patient["_id"] = str(updated_patient["_id"])

        message = {"event": "update_patient", "data": updated_patient}
        await notify_clients(message)

        return {"message": "Patient information updated successfully", "data": updated_patient}

    raise HTTPException(status_code=500, detail="Failed to update patient information")


@app.put("/update-assessment-info/{patient_id}/{new_flag}")
async def update_assessment_info(patient_id: str, assessment_data: List[AssessmentModel], new_flag: int):
    # Check if a document with the specified patient_id exists
    existing_patient = await patients.find_one({"patient_id": patient_id})
    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Retrieve existing assessments
    existing_assessments = existing_patient.get("Assessment", [])

    # Add new assessments to the existing ones
    updated_assessments = existing_assessments + [assessment.dict() for assessment in assessment_data]

    # Update the Assessment field and the flag
    result = await patients.update_one(
        {"patient_id": patient_id},
        {"$set": {
            "Assessment": updated_assessments,
            "flag": new_flag
        }}
    )

    if result.modified_count > 0:
        # Fetch the updated item from the database
        updated_patient = await patients.find_one({"patient_id": patient_id})

        # If the flag is in the range 1 to 5, send the entire updated_patient data through the WebSocket
        if new_flag in range(-2, 6):
            await send_websocket_message(json_util.dumps(updated_patient, default=json_util.default))
        
        return [
    {
        "message": "Assessment information updated successfully"
    }
]


    raise HTTPException(status_code=500, detail="Failed to update assessment information")

async def send_websocket_message(message: str):
    for websocket in websocket_connections:
        await websocket.send_text(message)

@app.put("/update-recovery-info/{patient_id}/{new_flag}")
async def update_recovery_info(patient_id: str, recovery_data: RecoveryModel, new_flag: int):
    # Check if a document with the specified patient_id exists
    existing_patient = await patients.find_one({"patient_id": patient_id})

    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Retrieve the existing exercises from the patient record
    existing_recovery = existing_patient.get("Model_Recovery", [])

    # Append the new recovery data
    existing_recovery.append(recovery_data.dict())

    # Update the Model_Recovery field and the flag
    result = await patients.update_one(
        {"patient_id": patient_id},
        {"$set": {
            "Model_Recovery": existing_recovery,
            "flag": new_flag
        }}
    )

    if result.modified_count > 0:
        updated_patient = await patients.find_one({"patient_id": patient_id})

        # If the flag is in the range 1 to 5, send the updated patient data through the WebSocket
        if new_flag in range(-2, 6):
            await send_websocket_message(json_util.dumps(updated_patient, default=json_util.default))
        
        return {
            "message": "Recovery information updated successfully"
        } 


    raise HTTPException(status_code=500, detail="Failed to update recovery information")


async def send_websocket_message(message: str):
    for websocket in websocket_connections:
        await websocket.send_text(message)

@app.put("/patients/{patient_id}/{new_flag}/add-exercise-assigned")
async def add_empty_exercise_assigned(patient_id: str, exercises: Dict[str, ExerciseAssigned], new_flag: int):
    # Find the patient document by patient_id
    patient = await patients.find_one({"patient_id": patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Prepare the new Exercise_Assigned dictionary
    new_exercise_assigned = {key: value.dict() for key, value in exercises.items()}  # Convert Pydantic models to dict
    
    # Update the document to add Exercise_Assigned and update the flag
    update_result = await patients.update_one(
        {"patient_id": patient_id},
        {
            "$set": {
                "Exercise_Assigned": new_exercise_assigned,
                "flag": new_flag
            }
        }
    )

    updated_todo = await patients.find_one({"patient_id": patient_id})

    if new_flag in range(-2, 6):
        await send_websocket_message(json_util.dumps(updated_todo))
    
    if update_result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update the patient document")

    return {"message": "New Exercises added and flag updated successfully"}

from bson import json_util
from fastapi import HTTPException

@app.put("/update_flag/{patient_id}/{new_flag}/{doctor_name}/{doctor_id}/{schedule_start_date}")
async def update_flag(patient_id: str, new_flag: int, doctor_name: str, doctor_id: str, schedule_start_date: str):
    # Fetch the item from the database using the provided patient_id
    todo = await patients.find_one({"patient_id": patient_id})

    # Check if the item exists
    if not todo:
        raise HTTPException(status_code=404, detail="Item not found")

    # Append the new schedule_start_date to the events_date array
    await patients.update_one(
        {"patient_id": patient_id},
        {
            "$set": {
                "flag": new_flag,
                "doctor_assigned": doctor_name,
                "doctor_id": doctor_id,
            },
            "$push": {"events_date": schedule_start_date},
        }
    )

    # Fetch the updated document
    updated_todo = await patients.find_one({"patient_id": patient_id})

    # Use WebSocket to send the updated document if the flag is in the valid range
    if new_flag in range(-2, 6):
        await send_websocket_message(json_util.dumps(updated_todo))

    # Return the updated document as JSON
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
    
# @app.post("/add_dicom/{unique_id}")
# async def add_dicom(unique_id: str, dicom_data: DicomData):
#     try:
#         # Convert the incoming data into dictionary
#         dicom_entry = dicom_data.dict()
#         dicom_entry["date_time"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

#         # Check if the document with the unique_id already exists
#         existing_document = await db.dicom.find_one({"unique_id": unique_id})

#         if existing_document:
#             # Append new entry to the data list, keeping only the last 5 entries
#             await db.dicom.update_one(
#                 {"unique_id": unique_id},
#                 {
#                     "$push": {
#                         "data": {"$each": [dicom_entry], "$slice": -5}
#                     }
#                 },
#             )
#             # Fetch the updated document
#             updated_document = await db.dicom.find_one({"unique_id": unique_id})
#             updated_document["_id"] = str(updated_document["_id"])  # Convert ObjectId to string
#             return updated_document
#         else:
#             # Create a new document if it doesn't exist
#             new_document = {
#                 "unique_id": unique_id,
#                 "data": [dicom_entry],
#             }
#             result = await db.dicom.insert_one(new_document)
#             new_document["_id"] = str(result.inserted_id)
#             return new_document

#     except Exception as e:
#         # Return a 500 error with the exception message
#         raise HTTPException(status_code=500, detail=f"Error inserting data: {e}")
    

@app.post("/add_dicom/")
async def add_dicom(dicom: Dicom):
    try:
        dicom_entry = dicom.dict()
        dicom_entry["date_time"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # Insert a new document for each entry in `data`
        for entry in dicom_entry["data"]:
            new_document = {
                "unique_id": dicom_entry["unique_id"],
                "values_stored": entry["values_stored"],
                "dicom_image": entry["dicom_image"],
                "date_time": dicom_entry["date_time"],
            }
            result = await db.dicom.insert_one(new_document)
            new_document["_id"] = str(result.inserted_id)  # Convert ObjectId to string
        
        return {"message": "DICOM data inserted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inserting data: {e}")
    
@app.get("/get_dicom/{unique_id}")
async def get_dicom(unique_id: str):
    try:
        # Find all documents matching the unique_id
        documents_cursor = db.dicom.find({"unique_id": unique_id})
        
        # Convert the cursor to a list using `await`
        documents = await documents_cursor.to_list(length=None)

        if not documents:
            raise HTTPException(status_code=404, detail="DICOM data not found")

        # Convert ObjectId to string
        for doc in documents:
            doc["_id"] = str(doc["_id"])

        return {"data": documents}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

    
@app.get("/unique_ids")
async def get_all_patient_unique_ids():
    try:
        # Find all patient documents (no filter on empty unique_id for now)
        patient_data = patients.find({}, {"unique_id": 1})

        # Use async for to iterate over the cursor
        unique_ids = []
        async for patient in patient_data:
            if "unique_id" in patient and patient["unique_id"]:  # Check if unique_id exists and is not empty
                unique_ids.append({"unique_id": patient["unique_id"]})

        return unique_ids
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving patient data: {e}")

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
