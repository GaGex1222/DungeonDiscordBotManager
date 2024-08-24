
import dotenv
from dotenv import load_dotenv
import os
from bson.objectid import ObjectId
import pymongo
from pymongo import MongoClient
load_dotenv()


cluster = MongoClient()
TOKEN = os.getenv('TOKEN')
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD')
MONGODB_URL = f'mongodb+srv://GaGex:{MONGODB_PASSWORD}@cluster0.6uemb.mongodb.net/'
mongodb_client = MongoClient(MONGODB_URL)
primary_database = mongodb_client['Discord']
maplestory_collection = primary_database.Maplestory
import datetime
obj = ObjectId('66ca54793b8018381b3a9514')
#pymongo function


query = maplestory_collection.find_one({"_id": obj})
dps_players_count = len(query["Dps"])
tank_players_count = len(query["Tank"])
healer_players_count = len(query["Healers"])
class_types = ("Dps", "Healers", "Tank")



print(query["Healers"])

playesr = []



for key, value in query["Healers"].items():
    playesr.append(key)

print(playesr)