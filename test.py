
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

obj = ObjectId('66c4fceed5ebc9c051601489')
#pymongo function


query = maplestory_collection.find_one({"_id": obj})
dps_players_count = len(query["Dps"])
tank_players_count = len(query["Tank"])
healer_players_count = len(query["Healers"])
class_types = ("Dps", "Healers", "Tank")



Dps_players = ''
Healers_players = ''
Tank_players = ''
for class_type in class_types:
    for player, class_name in query[class_type].items():
        if class_type == "Dps":
            Dps_players += f"{player} {class_name}"
        elif class_type == "Healers":
            Healers_players += f"{player} {class_name}\n"
        else:   
            Tank_players += f"{player} {class_name}"




print(Healers_players)
