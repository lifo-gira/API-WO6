from motor import motor_asyncio
from datetime import datetime
from bson import ObjectId
from models import *

client = motor_asyncio.AsyncIOMotorClient("mongodb+srv://wadfirm2023:wadfirm2023@wadco.o2m22gs.mongodb.net/?retryWrites=true&w=majority")
db = client.Main
users = db.users
metrics = db.metrics

async def getAllUser(type):
    try:
        allUsers = []
        if type == "all":
            cursor = users.find({}, {'_id': 0})
        else:
            cursor = users.find({"type": type}, {'_id': 0})
        
        async for document in cursor:
            allUsers.append(document)
    except Exception as e:
        print(e)
    return allUsers

async def getUser(type, id):
    try: 
        res = await users.find_one({"user_id": id, "type": type},{'_id': 0})
        return res
    except Exception as e:
        return None

async def createAdminUser(data: Admin):
    try:
        await users.insert_one(dict(data))
        return True
    except Exception as e:
        print(e)
        return False
    
async def createDoctor(data: Doctor):
    try:
        await users.insert_one(dict(data))
        return True
    except:
        return False
    
# async def createPatient(data: Patient):
#     try:
#         await users.insert_one(dict(data))
#         return True
#     except:
#         return False

async def createPatient(data: GoogleOAuthCallback):
    try:
        # Insert patient data and Google sign-in data into the database
        await users.insert_one(dict(data))
        return True
    except Exception as e:  
        print(f"Error inserting data: {e}")
        return False 
    
async def loginUser(user_id, password):
    user = {"data": {}, "loginStatus": False}
    res = await users.find_one({"user_id": user_id, "password": password},{'_id': 0})
    try: 
        user["data"] = res
        user["loginStatus"] = True
    except Exception as e:
        print(e)
        user["loginStatus"] = False
    finally:
        return user
    
async def postData(user_id: str, data: Data):
    try:
        # Set the created_date and created_time to IST
        ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
        data.created_date = ist_now.strftime('%Y-%m-%d')
        data.created_time = ist_now.strftime('%H:%M:%S')

        # Data object will have default values for created_date and created_time in IST
        await metrics.insert_one(data.dict())  # Convert data object to dictionary

        res = await users.find_one({"user_id": user_id, "type": "patient"})
        res = dict(res)
        res["data"].append(data.data_id)
        
        await users.update_one({"user_id": user_id, "type": "patient"}, {"$set": res})
        return True
    except Exception as e:
        print(e)
        return False

async def putData(data: Data):
    try:
        res = await metrics.find_one({"data_id": data.data_id},{'_id': 0})
        res["series"] = res["series"] + data.series
        await metrics.update_one({"data_id": data.data_id}, {"$set": res})
        return True
    except Exception as e:
        print(e)
        return False
    
async def getData(data_id: list):
    metricsColl = []
    cursor =  metrics.find( { "data_id": { "$in": data_id } }, { "_id": 0 } )
    async for document in cursor:
        metricsColl.append(document)
    return metricsColl


async def get_user_from_db(type: str, user_id: str) -> Patient:
    user_data = await users.find_one({"type": type, "user_id": user_id})
    if user_data:
        return Patient(**user_data)
    return None

async def deleteData(request: DeleteRequest):
    try:
        # Convert start_date and end_date to datetime objects for comparison
        start_datetime = datetime.strptime(f"{request.start_date} {request.start_time}", "%Y-%m-%d %H:%M:%S")
        end_datetime = datetime.strptime(f"{request.end_date} {request.end_time}", "%Y-%m-%d %H:%M:%S")

        # Define the query for documents with the same device_id, created_date, and created_time within the specified range
        query = {
            "device_id": request.device_id,
            "created_date": {
                "$gte": start_datetime.strftime("%Y-%m-%d"),
                "$lte": end_datetime.strftime("%Y-%m-%d")
            },
            "created_time": {
                "$gte": request.start_time,
                "$lte": request.end_time
            }
        }

        # Perform deletion
        result = await metrics.delete_many(query)

        if result.deleted_count > 0:
            await users.update_one(
                {"device_id": request.device_id, "type": "sensor"},
                {"$pull": {"data": {"$in": [str(doc["_id"]) for doc in result.deleted_ids]}}}
            )
            
            return {"deleted": True, "count": result.deleted_count}
        else:
            return {"deleted": False, "error": "No matching documents found to delete"}
    except Exception as e:
        return {"deleted": False, "error": str(e)}