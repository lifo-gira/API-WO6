from motor import motor_asyncio

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
    
async def createPatient(data: Patient):
    try:
        await users.insert_one(dict(data))
        return True
    except:
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
    
async def postData( user_id: str, data: Data):
    try:
        await metrics.insert_one(dict(data))
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
