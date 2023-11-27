from fastapi import FastAPI, WebSocket, HTTPException, Request, Depends
from typing import Literal, Optional
from fastapi.middleware.cors import CORSMiddleware
from models import Admin, Doctor, Patient, Data
import db
from models import ConnectionManager, WebSocketManager, GoogleOAuthCallback,DeleteRequest
from db import get_user_from_db,metrics,deleteData
import json
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from authlib.integrations.starlette_client import OAuth
from datetime import datetime, timezone



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
        print(res["data"])
        # Redirect the user to the social media login endpoint
        return res["data"]

    # Traditional username/password login logic
    res = await db.loginUser(user_id, password)
    if res["loginStatus"]:
        return res["data"]
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
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


