import discord
from discord import app_commands, SelectOption
from discord.ext import commands
from discord.ui import view, Button, Select
import dotenv
from dotenv import load_dotenv
import os
import pymongo
from class_infos import all_classes, class_types_list
from pymongo import MongoClient
from datetime import datetime
load_dotenv()

for classing in class_types_list:
    print(classing)
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
class_types = ("Dps", "Healers", "Tank")
def create_document(creator_name, date):
    if maplestory_collection.find_one({"creator_name": creator_name}):
        return False
    else:
        new_doc = {
            "date": date,
            "creator_name": creator_name,
            "Dps": {},
            "Healers": {},
            "Tank": {},
        }
        inserted_id = maplestory_collection.insert_one(new_doc).inserted_id
        return inserted_id

    

def add_player_to_document(class_name, username, _id, class_type_to_add):
    query = maplestory_collection.find_one({"_id": _id})
    if len(query["Healers"]) >= 3 or  len(query["Dps"]) >= 10 or len(query["Tank"]) >= 4:
        return False
    for class_type in class_types:
        if query[class_type].get(username):
            return False 

    maplestory_collection.update_one(
        {"_id": _id},
        {"$set": {f"{class_type_to_add}.{username}": class_name}}
    )
    return True
    
        
def delete_player_from_document(username, _id):
    query = maplestory_collection.find_one({"_id": _id})
    for class_type in class_types:
        if query[class_type].get(username):
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


class DmOwnerForApproval(discord.ui.View):
    def __init__(self ,username_for_approval, doc_id, owner_id, user_class_name, user_class_category, message_object, dungeon_instance, interacted_user_id):
        self.username_for_approval = username_for_approval
        self.doc_id = doc_id
        self.owner_id = owner_id
        self.message_object = message_object
        self.user_class_name = user_class_name
        self.user_class_category = user_class_category
        self.user_approved = None
        self.dungeon_instace = dungeon_instance
        self.interacted_user_id = interacted_user_id
        super().__init__()

        
        reject_button = discord.ui.Button(label="Reject", style=discord.ButtonStyle.red)
        reject_button.callback = self.reject_button_callback
        self.add_item(reject_button)
        
        
        accept_button = discord.ui.Button(label="Approve", style=discord.ButtonStyle.green)
        accept_button.callback = self.approve_button_callback
        self.add_item(accept_button)

    async def approve_button_callback(self, interaction: discord.Interaction):
        player_added = add_player_to_document(class_name=self.user_class_name, username=self.username_for_approval, class_type_to_add=self.user_class_category, _id=self.doc_id)
        if player_added:
                self.dungeon_instace.approved_queue.remove(self.username_for_approval)
                self.dungeon_instace.dungeon_players.append(self.username_for_approval)
                approved_embed = discord.Embed(title=f"You have approved {self.username_for_approval} to join your dungeon as a {self.user_class_name} in category {self.user_class_category}")
                await self.message_object.edit(embed=approved_embed, view=None)
                await self.dungeon_instace.update_embed()
        else:
            self.dungeon_instace.approved_queue.remove(self.username_for_approval)
            await interaction.response.send_message("Your request was denied, possibly because the dungeon is full or the user is already in the dungeon")
                



    async def reject_button_callback(self, interaction: discord.Interaction):
        rejected_embed = discord.Embed(title=f"You have rejected {self.username_for_approval} to join your dungeon as a {self.user_class_name} in category {self.user_class_category}")
        await self.message_object.edit(embed=rejected_embed, view=None)
        await interaction.response.send_message(f"{self.username_for_approval} Have Been rejected from joining the dungeon", delete_after=5)
        self.dungeon_instace.approved_queue.remove(self.username_for_approval)

        

    

    

class ClassSelectorsView(discord.ui.View):
    def __init__(self, doc_id, creator_id, message, username, dungeon_start_time):
        super().__init__()
        self.doc_id = doc_id
        self.timeout = None
        self.creator_id = creator_id
        self.message = message
        self.username = username
        self.dungeon_start_time = dungeon_start_time
        self.user_selected_class = {}
        self.user_selected_class_category = {}
        self.owner_user_object = bot.get_user(int(creator_id))
        self.approved_queue = []
        self.dungeon_players = []

        #Components
        select_class_menu = Select(
                min_values=1,
                max_values=1,
                placeholder="Choose a class...",
                options=[SelectOption(label=option) for option in all_classes],
                custom_id="class_menu"

            )
        select_class_menu.callback = self.select_callback_class_name
        self.add_item(select_class_menu)



        select_class_category_menu = Select(
            min_values=1,
            max_values=1,
            placeholder="Choose a class category...",
            options=[SelectOption(label=class_category) for class_category in class_types_list],
            custom_id="select_class_category_menu"

        )
        select_class_category_menu.callback = self.select_callback_class_category
        self.add_item(select_class_category_menu)

        unregister_button = discord.ui.Button(label="Unregsiter", style=discord.ButtonStyle.danger)
        unregister_button.callback = self.unregister_button_callback
        self.add_item(unregister_button)

        register_button = discord.ui.Button(label="Register", style=discord.ButtonStyle.green)
        register_button.callback = self.register_button_callback
        self.add_item(register_button)

    async def update_embed(self):
        print("Updated it")
        created_doc_query = maplestory_collection.find_one({"_id": self.doc_id})
        dps_players_count = len(created_doc_query["Dps"])
        tank_players_count = len(created_doc_query["Tank"])
        healer_players_count = len(created_doc_query["Healers"])
        class_types_max_players_and_counts = [
            ("Dps", dps_players_count, 10),
            ("Healers", healer_players_count, 3),
            ("Tank", tank_players_count, 4)
        ]
        query = maplestory_collection.find_one({"_id": self.doc_id})
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

        embed = discord.Embed(title="Dungeon", description=f'Leader : {self.username} - ID {self.creator_id}')
        for class_type, count, max_players in class_types_max_players_and_counts:
            value = player_map.get(class_type, "No players registered.")
            if count >= max_players:
                embed.add_field(name=f"{class_type} {max_players}/{count}", value=value)
            else:
                embed.add_field(name=f"{class_type} {max_players}/{count}", value=value)
        embed.add_field(name="Total players 📊", value=dps_players_count + tank_players_count + healer_players_count)
        embed.add_field(name="Start Time :calendar_spiral: ", value=f"`{self.dungeon_start_time}`")
        await self.message.edit(embed=embed)


    async def register_button_callback(self, interaction: discord.Interaction):
        interacting_user_id = interaction.user.id
        requsting_username = str(interaction.user)
        requsting_user_id = interaction.user.id
        if requsting_username in self.approved_queue:
            await interaction.response.send_message("Your request has already been sent to the owner. Please wait for a response before sending another one.", ephemeral=True, delete_after=5)
            return
        if requsting_username in self.dungeon_players:
            await interaction.response.send_message("You are already registered in this dungeon", ephemeral=True, delete_after=5)
            return
        try:
            user_class_name = self.user_selected_class[interacting_user_id]
            user_class_category = self.user_selected_class_category[interacting_user_id]
        except Exception:
            await interaction.response.send_message("You have to fill in class and class category!", ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message(f"{requsting_username}, Your request has been sent to {self.username}, who will decide whether to accept you", ephemeral=True, delete_after=5)
            embed = discord.Embed(title=f"Approval request for dungeon from {requsting_username}", description=f"{requsting_username} requested to join your dugeon party as {user_class_name} in category {user_class_category}\nApprove or reject?")
            message_dmed_to_user = await self.owner_user_object.send(embed=embed)
            
            dm_for_owner_view = DmOwnerForApproval(message_object=message_dmed_to_user ,username_for_approval=requsting_username, doc_id=self.doc_id, owner_id=self.creator_id, interacted_user_id=requsting_user_id, user_class_name=user_class_name, user_class_category=user_class_category, dungeon_instance=self)
            await message_dmed_to_user.edit(view=dm_for_owner_view)
            self.approved_queue.append(requsting_username)



    async def unregister_button_callback(self, interaction: discord.Interaction):
        player_deleted = delete_player_from_document(username=str(interaction.user), _id=self.doc_id)
        if player_deleted:
            await interaction.response.send_message("You have been successfully unregistered from the dungeon", ephemeral=True, delete_after=5)
            self.dungeon_players.remove(str(interaction.user))
            await self.update_embed()
        else:
            await interaction.response.send_message("There was a problem unregistering you from the dungeon, Probably becuase you are not registered!", ephemeral=True, delete_after=5)

    async def select_callback_class_name(self, interaction: discord.Interaction):
        self.user_selected_class[interaction.user.id] = interaction.data["values"][0]
        print(self.user_selected_class)
        await interaction.response.send_message(f"You have selected the class {interaction.data["values"][0]}", ephemeral=True, delete_after=5)


    async def select_callback_class_category(self, interaction: discord.Interaction):
        self.user_selected_class_category[interaction.user.id] = interaction.data["values"][0]
        print(self.user_selected_class_category)
        await interaction.response.send_message(f"You have selected the category {interaction.data["values"][0]}", ephemeral=True, delete_after=5)

        
#Discord bot functions
@bot.tree.command(name='create_dungeon', description="This command creates a dungeon!")
@app_commands.describe(date="Specify the dungeon date (YYYY-MM-DD Format)")
@app_commands.describe(hour="Specify the dungeon start time (H:M Format)")
async def create_dungeon(interaction: discord.Interaction, date: str, hour: str):
    try:
        concatenated_date = f"{date} {hour}"
        date_object = datetime.strptime(concatenated_date, "%Y-%m-%d %H:%M")
        date_formatted = datetime.strftime(date_object, '%Y %d %B, %A %H:%M')
    except Exception:
        await interaction.response.send_message("Invalid format for date or hour, please use the specified format")
    new_doc_id = create_document(str(interaction.user), date=date_formatted)
    if new_doc_id == False:
        await interaction.response.send_message("Cant create more than one dungeon per user!")
        return
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
        embed.add_field(name="Total players 📊", value=dps_players_count + tank_players_count + healer_players_count)
        embed.add_field(name="Start Time :calendar_spiral: ", value=f"`{date_formatted}`")

        await interaction.response.send_message(embed=embed)
        response_message = await interaction.original_response()
        view = ClassSelectorsView(doc_id=new_doc_id, message=response_message, creator_id=interaction.user.id, username=str(interaction.user), dungeon_start_time=date_formatted)
        await response_message.edit(view=view)









bot.run(token=TOKEN)