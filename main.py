import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import view, Button
import dotenv
from dotenv import load_dotenv
import os
import pymongo
from class_infos import buttons_info
from pymongo import MongoClient
import asyncio
load_dotenv()


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
cluster = MongoClient()
TOKEN = os.getenv('TOKEN')
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD')
MONGODB_URL = f'mongodb+srv://GaGex:{MONGODB_PASSWORD}@cluster0.6uemb.mongodb.net/'
mongodb_client = MongoClient(MONGODB_URL)
primary_database = mongodb_client.Discord
maplestory_collection = primary_database.Maplestory

#pymongo functions
def create_document(creator_name):
    if maplestory_collection.find_one({"creator_name": creator_name}):
        return False
    else:
        new_doc = {
            "creator_name": creator_name,
            "Dps": {},
            "Healers": {},
            "Tank": {},
        }
        inserted_id = maplestory_collection.insert_one(new_doc).inserted_id
        return inserted_id

def add_player_to_document(class_name, username, _id, class_type_to_add):
    class_types = ("Dps", "Healers", "Tank")
    for class_type in class_types:
        if maplestory_collection.find_one({"_id": _id, f"{class_type}.{username}": {"$exists": True}}):
            return False
        else:
            maplestory_collection.update_one({"_id": _id}, {"$set": {class_type_to_add: {username: class_name}}})
            return True
        
def delete_player_from_document(username, _id):
    class_types = ("Dps", "Healers", "Tank")
    for class_type in class_types:
        if maplestory_collection.find_one({"_id": _id, f"{class_type}.{username}": {"$exists": True}}):
            maplestory_collection.update_one({"_id": _id}, {"$unset": {f"{class_type}.{username}": ""}})
            return True
    return False
    



@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user.name}')


@bot.command()
async def treesync(ctx):
    print("Tree sync trying to sync")
    if ctx.author.id == 301854099769655306:
        await bot.tree.sync()
        await ctx.send("Tree of commands has been synced")
    else:
        await ctx.send("You are not allowed to use this command.")


class MyView(discord.ui.View):
    def __init__(self, doc_id, creator_id):
        super().__init__()
        self.doc_id = doc_id
        self.timeout = None
        self.creator_id = creator_id




    def create_button_callback(self, class_type, label):
        async def button_callback(interaction: discord.Interaction):
            if label == "Unregister":
                player_removed = delete_player_from_document(str(interaction.user), self.doc_id)
                if player_removed:
                    await interaction.response.send_message(f"{interaction.user.mention} you have successfully unregistered from this dungeon!", ephemeral=True, delete_after=5)
                else:
                    await interaction.response.send_message(f"{interaction.user.mention} error occured while unregistering, probably because you are not registered.", ephemeral=True, delete_after=5)

            else:      
                player_added = add_player_to_document(label, str(interaction.user), self.doc_id, class_type)
                if player_added:
                    await interaction.response.send_message(content=f"{interaction.user.mention} You have entered this dungeon successfully!", ephemeral=True, delete_after=5)
                else:
                    await interaction.response.send_message(content=f"{interaction.user.mention} There was a problem joining the dungeon, probably because you are already in it or it's full!", ephemeral=True, delete_after=5)

        return button_callback
    
    def create_buttons(self, buttons_info):
        for label, style, class_type in buttons_info:
            button = discord.ui.Button(label=label, style=style, emoji='<:1000pogchamp:739592283439104001>')
            button.callback = self.create_button_callback(class_type=class_type, label=label)
            self.add_item(button)
        unregister_button = discord.ui.Button(label="Unregister", style=discord.ButtonStyle.gray, emoji='<:1000pogchamp:739592283439104001>', custom_id="unregister")
        unregister_button.callback = self.create_button_callback("doesnt matter", label=unregister_button.label)
        self.add_item(unregister_button)
        
        
    


    



async def update_embed(message, doc_id, username, user_id):
    while True:
        print("Updated it")
        created_doc_query = maplestory_collection.find_one({"_id": doc_id})
        dps_players_count = len(created_doc_query["Dps"])
        tank_players_count = len(created_doc_query["Tank"])
        healer_players_count = len(created_doc_query["Healers"])
        class_types_max_players_and_counts = [
            ("Dps", dps_players_count, 10),
            ("Healers", healer_players_count, 3),
            ("Tank", tank_players_count, 4)
        ]
        query = maplestory_collection.find_one({"_id": doc_id})
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
        player_map = {
        "Dps": Dps_players,
        "Healers": Healers_players,
        "Tank": Tank_players
        }

        embed = discord.Embed(title="Dungeon", description=f'Leader : {username} - ID {user_id}')
        for class_type, count, max_players in class_types_max_players_and_counts:
            value = player_map.get(class_type, "No players registered.")
            embed.add_field(name=f"{class_type} {max_players}/{count}", value=value)
        embed.add_field(name="Total players", value=dps_players_count + tank_players_count + healer_players_count)
        await message.edit(embed=embed)
        await asyncio.sleep(10)

                    


@bot.tree.command(name='create_dungeon')
async def create_dungeon(interaction: discord.Interaction):
    # Create an instance of the custom view
    new_doc_id = create_document(str(interaction.user))
    if new_doc_id == False:
        await interaction.response.send_message("Cant create more than one dungeon per user!")
    else:
        created_doc_query = maplestory_collection.find_one({"_id": new_doc_id})
        dps_players_count = len(created_doc_query["Dps"])
        tank_players_count = len(created_doc_query["Tank"])
        healer_players_count = len(created_doc_query["Healers"])
        class_types_max_players_and_counts = [
            ("Dps", dps_players_count, 10),
            ("Healer", healer_players_count, 3),
            ("Tank", tank_players_count, 4)
        ]

        embed = discord.Embed(title="Dungeon", description=f'Leader : {interaction.user} - ID {interaction.user.id}')
        for class_type, count, max_players in class_types_max_players_and_counts:
            embed.add_field(name=f"{class_type}", value=f"{max_players}/{count}")
        embed.add_field(name="Total players", value=dps_players_count + tank_players_count + healer_players_count)
        view = MyView(doc_id=new_doc_id, creator_id=interaction.user.id)
        view.create_buttons(buttons_info=buttons_info)

        await interaction.response.send_message(view=view, embed=embed)
        response_message = await interaction.original_response()
        bot.loop.create_task(update_embed(response_message, doc_id=new_doc_id, user_id=interaction.user.id, username=str(interaction.user)))









bot.run(token=TOKEN)