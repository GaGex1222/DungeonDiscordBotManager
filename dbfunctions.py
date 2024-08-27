from pymongo import MongoClient
import os
import pymongo
import discord


class_types = ("Dps", "Healers", "Tank")
role_max_length = {
    "Dps": 10,
    "Healers": 3,
    "Tank": 4,
}
cluster = MongoClient()
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD')
MONGODB_URL = f'mongodb+srv://GaGex:{MONGODB_PASSWORD}@cluster0.6uemb.mongodb.net/'
mongodb_client = MongoClient(MONGODB_URL)
primary_database = mongodb_client.Discord
maplestory_collection = primary_database.Maplestory


def create_document(creator_name, date, creator_id):
    new_doc = {
        "date": date,
        "creator_name": creator_name,
        "creator_id": creator_id,
        "Dps": {},
        "Healers": {},
        "Tank": {},
        "muted_players": [],
        "in_queue_players": [],
    }
    inserted_id = maplestory_collection.insert_one(new_doc).inserted_id
    return inserted_id

def add_player_to_queue_or_mute_lists(_id, username, queue_or_mute):
    if queue_or_mute == "mute":
        query_keyword = "muted_players"
    elif queue_or_mute == "queue":
        query_keyword = "in_queue_players"
    maplestory_collection.update_one({"_id": _id}, {"$push": {query_keyword: username}})

def remove_player_from_queue_or_mute_lists(_id, username, queue_or_mute):
    if queue_or_mute == "mute":
        query_keyword = "muted_players"
    elif queue_or_mute == "queue":
        query_keyword = "in_queue_players"
    maplestory_collection.update_one({"_id": _id}, {"$pull": {query_keyword: username}})

def check_if_player_muted_or_in_queue(_id, username, queue_or_mute):
    if queue_or_mute == "mute":
        query_keyword = "muted_players"
    elif queue_or_mute == "queue":
        query_keyword = "in_queue_players"
    if maplestory_collection.find_one({"_id": _id, query_keyword: username}):
        return True
    else:
        return False


def get_all_dungeon_documents():
    all_docs = maplestory_collection.find({})
    if len(list(all_docs)) == 0:
        return all_docs
    else:
        return False

def check_if_player_in_dungeon(_id, username):
    query = maplestory_collection.find_one({"_id": _id})
    for class_type in class_types:
        if query[class_type].get(username):
            return True
    return False

def check_length_of_players_in_queue(_id):
    query = maplestory_collection.find_one({"_id": _id})
    return len(query["in_queue_players"])

def add_player_to_document(class_name, username, _id, class_type_to_add):
    query = maplestory_collection.find_one({"_id": _id})
    if len(query[class_type_to_add]) >= role_max_length[class_type_to_add]:
        return False
    for class_type in class_types:
        if query[class_type].get(username):
            return False 

    maplestory_collection.update_one(
        {"_id": _id},
        {"$set": {f"{class_type_to_add}.{username}": class_name}}
    )
    return True

def all_dungeon_players(_id):
    doc = maplestory_collection.find_one({"_id": _id})
    players = []
    for class_type in class_types:
        for key, value in doc[class_type].items():
            players.append(key)
    return players
        

def get_all_document_data(_id):
    query = maplestory_collection.find_one({"_id": _id})
    print(query)
    return query

def total_players(_id):
    query = maplestory_collection.find_one({"_id": _id})
    dps_players_count = len(query["Dps"])
    tank_players_count = len(query["Tank"])
    healer_players_count = len(query["Healers"])
    return (healer_players_count + tank_players_count + dps_players_count)


def delete_player_from_document(username, _id):
    query = maplestory_collection.find_one({"_id": _id})
    for class_type in class_types:
        if query[class_type].get(username):
            maplestory_collection.update_one({"_id": _id}, {"$unset": {f"{class_type}.{username}": ""}})
            return True
    return False


# async def update_or_send_embed(doc_id, username, dungeon_start_time, creator_id, send_or_edit, message, interaction=None):
#     created_doc_query = maplestory_collection.find_one({"_id": doc_id})
#     dps_players_count = len(created_doc_query["Dps"])
#     tank_players_count = len(created_doc_query["Tank"])
#     healer_players_count = len(created_doc_query["Healers"])
#     class_types_max_players_and_counts = [
#         ("Dps", dps_players_count, 10),
#         ("Healers", healer_players_count, 3),
#         ("Tank", tank_players_count, 4)
#     ]
#     query = maplestory_collection.find_one({"_id": doc_id})
#     Dps_players = ''
#     Healers_players = ''
#     Tank_players = ''
#     for class_type in class_types:
#         for player, class_name in query[class_type].items():
#             if class_type == "Dps":
#                 Dps_players += f"{player} {class_name}\n"
#             elif class_type == "Healers":
#                 Healers_players += f"{player} {class_name}\n"
#             else:   
#                 Tank_players += f"{player} {class_name}\n"
#     player_map = {
#     "Dps": Dps_players,
#     "Healers": Healers_players,
#     "Tank": Tank_players
#     }

#     embed = discord.Embed(title="Dungeon", description=f'Leader : {username} - ID {creator_id}')
#     for class_type, count, max_players in class_types_max_players_and_counts:
#         value = player_map.get(class_type, "No players registered.")
#         embed.add_field(name=f"{class_type} {max_players}/{count}", value=value)
#     embed.add_field(name="Total players 📊", value=dps_players_count + tank_players_count + healer_players_count)
#     embed.add_field(name="Start Time :calendar_spiral: ", value=f"`{dungeon_start_time}`")
#     embed.add_field(name="Players in queue 🚦", value=check_length_of_players_in_queue(doc_id))
#     if send_or_edit == "edit":
#         await message.edit(embed=embed)
#     elif send_or_edit == "send":
#         await interaction.response.send_message(embed=embed)



if get_all_dungeon_documents():
    print("Yes")
else:
    print("No")