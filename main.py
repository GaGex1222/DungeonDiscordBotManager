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
class_max_length = {
    "Dps": 10,
    "Healers": 3,
    "Tank": 4,
}
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
    if len(query[class_type_to_add]) >= class_max_length[class_type_to_add]:
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


class UnmuteView(discord.ui.View):
    def __init__(self, dungeon_instance, message_object, username_for_approval):
        self.dungeon_instance = dungeon_instance
        self.message_object = message_object
        self.username_for_approval = username_for_approval
        super().__init__()

        unmute_player_button = discord.ui.Button(label="Unmute Player", style=discord.ButtonStyle.green)
        unmute_player_button.callback = self.unmute_player_button_callback
        self.add_item(unmute_player_button)
    

    async def unmute_player_button_callback(self):
        if check_if_player_muted_or_in_queue(_id=self.dungeon_instance.doc_id, username=self.username_for_approval, queue_or_mute="mute"):
            remove_player_from_queue_or_mute_lists(_id=self.dungeon_instance.doc_id, username=self.username_for_approval, queue_or_mute="mute")
            unmuted_embed = discord.Embed(title=f"You have unmuted {self.username_for_approval} in your dungeon at `{self.dungeon_instance.dungeon_start_time}`")
            await self.message_object.edit(embed=unmuted_embed, view=None)
            






class DmOwnerForApproval(discord.ui.View):
    def __init__(self ,username_for_approval, user_class_name, user_class_role, message_object, dungeon_instance, interacted_user_id):
        self.dungeon_instace = dungeon_instance
        self.dungeon_start_time = dungeon_instance.dungeon_start_time
        self.doc_id = dungeon_instance.doc_id
        self.username_for_approval = username_for_approval
        self.message_object = message_object
        self.user_class_name = user_class_name
        self.user_class_role = user_class_role
        self.interacted_user_id = interacted_user_id
        self.interacted_user_object = bot.get_user(self.interacted_user_id)
        super().__init__()

        
        reject_button = discord.ui.Button(label="Reject", style=discord.ButtonStyle.red)
        reject_button.callback = self.reject_button_callback
        self.add_item(reject_button)
        
        
        accept_button = discord.ui.Button(label="Approve", style=discord.ButtonStyle.green)
        accept_button.callback = self.approve_button_callback
        self.add_item(accept_button)

        reject_and_mute = discord.ui.Button(label="Reject And Mute", style=discord.ButtonStyle.gray)
        reject_and_mute.callback = self.reject_and_mute_button_callback
        self.add_item(reject_and_mute)


    async def approve_button_callback(self, interaction: discord.Interaction):
        player_added = add_player_to_document(class_name=self.user_class_name, username=self.username_for_approval, class_type_to_add=self.user_class_role, _id=self.doc_id)
        if player_added:
                approved_message_dm = discord.Embed(title=f"{self.dungeon_instace.username} have approved your request on joining the dungeon\n\nthe dungeon starts at `{self.dungeon_instace.dungeon_start_time}`\n\nYou have registered as {self.user_class_name} in role {self.user_class_role}")
                await self.interacted_user_object.send(embed=approved_message_dm)
                remove_player_from_queue_or_mute_lists(_id=self.doc_id, username=self.username_for_approval, queue_or_mute="queue")
                approved_embed = discord.Embed(title=f"You have been approved {self.username_for_approval} to join your dungeon at `{self.dungeon_start_time}`\n\nas a {self.user_class_name} in role {self.user_class_role}")
                await self.message_object.edit(embed=approved_embed, view=None)
                await self.dungeon_instace.update_embed()
                await self.dungeon_instace.update_kicked_players_options()
        else:
            remove_player_from_queue_or_mute_lists(_id=self.doc_id, username=self.username_for_approval, queue_or_mute="queue")
            await interaction.response.send_message("Your request was denied, possibly because the dungeon is full or the user is already in the dungeon")
            await self.dungeon_instace.update_embed()
                



    async def reject_button_callback(self, interaction: discord.Interaction):
        rejected_embed = discord.Embed(title=f"You have rejected {self.username_for_approval} to join your dungeon at `{self.dungeon_start_time}`\n\nas {self.user_class_name} in role {self.user_class_role}")
        reject_embed_for_user = discord.Embed(title=f"You have been rejected from {self.dungeon_instace.username} dungeon at `{self.dungeon_instace.dungeon_start_time}`")
        await self.message_object.edit(embed=rejected_embed, view=None)
        await self.interacted_user_object.send(embed=reject_embed_for_user)
        await interaction.response.send_message(f"{self.username_for_approval} Have Been rejected from joining the dungeon", delete_after=5)
        remove_player_from_queue_or_mute_lists(_id=self.doc_id, username=self.username_for_approval, queue_or_mute="queue")
        await self.dungeon_instace.update_embed()

    async def reject_and_mute_button_callback(self, interaction: discord.Interaction):
        if not check_if_player_muted_or_in_queue(_id=self.doc_id, username=self.username_for_approval, queue_or_mute="mute"):
            add_player_to_queue_or_mute_lists(_id=self.doc_id, username=self.username_for_approval, queue_or_mute="mute")
            remove_player_from_queue_or_mute_lists(_id=self.doc_id, username=self.username_for_approval, queue_or_mute="queue")
            rejected_and_muted_embed = discord.Embed(title=f"You have rejected and muted {self.username_for_approval} to join your dungeon at `{self.dungeon_start_time}`\n\nas {self.user_class_name} in role {self.user_class_role}")
            rejected_and_muted_embed_for_user = discord.Embed(title=f"You have been rejected and muted from {self.dungeon_instace.username} dungeon at `{self.dungeon_start_time}`")
            unmute_button = UnmuteView(dungeon_instance=self.dungeon_instace, message_object=self.message_object, username_for_approval=self.username_for_approval)
            await self.interacted_user_object.send(embed=rejected_and_muted_embed_for_user)
            await self.message_object.edit(embed=rejected_and_muted_embed, view=unmute_button)
            await interaction.response.send_message(f"{self.username_for_approval} Have Been rejected and muted from joining the dungeon", delete_after=5)
            await self.dungeon_instace.update_embed()


        

    

    

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
        self.user_selected_class_role = {}
        self.owner_user_object = bot.get_user(int(creator_id))
        self.selected_kicked_users = None
        self.all_dungeon_players = None

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


        select_class_role_menu = Select(
            min_values=1,
            max_values=1,
            placeholder="Choose a class role...",
            options=[SelectOption(label=class_role) for class_role in class_types_list],
            custom_id="select_class_role_menu"

        )
        select_class_role_menu.callback = self.select_callback_class_role
        self.add_item(select_class_role_menu)

        self.select_kicked_players = Select(
            min_values=1,
            max_values=1,
            placeholder="Choose player/s to kick...",
            options=[SelectOption(label="No players available", value="none")],
            custom_id="select_kicked_players"
        )
        self.select_kicked_players.callback = self.select_kicked_players_callback
        self.add_item(self.select_kicked_players)
        
        unregister_button = discord.ui.Button(label="Unregsiter", style=discord.ButtonStyle.danger)
        unregister_button.callback = self.unregister_button_callback
        self.add_item(unregister_button)

        register_button = discord.ui.Button(label="Register", style=discord.ButtonStyle.green)
        register_button.callback = self.register_button_callback
        self.add_item(register_button)

        kick_players_button = discord.ui.Button(label="Kick Players", style=discord.ButtonStyle.grey)
        kick_players_button.callback = self.kick_button_callback
        self.add_item(kick_players_button)


    async def update_kicked_players_options(self):
        self.all_dungeon_players = all_dungeon_players(self.doc_id)
        if len(self.all_dungeon_players) > 0:
            self.select_kicked_players.options = [SelectOption(label=player) for player in self.all_dungeon_players]
            self.select_kicked_players.max_values = len(self.all_dungeon_players)
        else:
            self.select_kicked_players.max_values = 1
            self.select_kicked_players.options = [SelectOption(label="No players in dungeon!")]
        await self.message.edit(view=self)







    async def update_embed(self):
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
                    Dps_players += f"{player} {class_name}\n"
                elif class_type == "Healers":
                    Healers_players += f"{player} {class_name}\n"
                else:   
                    Tank_players += f"{player} {class_name}\n"
        player_map = {
        "Dps": Dps_players,
        "Healers": Healers_players,
        "Tank": Tank_players
        }

        embed = discord.Embed(title="Dungeon", description=f'Leader : {self.username} - ID {self.creator_id}')
        for class_type, count, max_players in class_types_max_players_and_counts:
            value = player_map.get(class_type, "No players registered.")
            embed.add_field(name=f"{class_type} {max_players}/{count}", value=value)
        embed.add_field(name="Total players 📊", value=dps_players_count + tank_players_count + healer_players_count)
        embed.add_field(name="Start Time :calendar_spiral: ", value=f"`{self.dungeon_start_time}`")
        embed.add_field(name="Players in queue 🚦", value=check_length_of_players_in_queue(self.doc_id))
        await self.message.edit(embed=embed)


    async def kick_button_callback(self, interaction: discord.Interaction):
        if self.selected_kicked_users:
            print(self.selected_kicked_users)
            for player in self.selected_kicked_users:
                delete_player_from_document(username=player, _id=self.doc_id)
                self.selected_kicked_users.remove(player)
            await interaction.response.send_message("Kicked all players selected from the dungeon", ephemeral=True, delete_after=5)
            await self.update_embed()
            await self.update_kicked_players_options()
        else:
            await interaction.response.send_message("No players selected to kick", ephemeral=True, delete_after=5)

    async def register_button_callback(self, interaction: discord.Interaction):
        interacting_user_id = interaction.user.id
        requsting_username = str(interaction.user)
        #cases which the player cant send a request
        if check_if_player_muted_or_in_queue(_id=self.doc_id, username=requsting_username, queue_or_mute="queue"):
            await interaction.response.send_message("Your request has already been sent to the owner. Please wait for a response before sending another one.", ephemeral=True, delete_after=5)
            return
        if check_if_player_in_dungeon(_id=self.doc_id, username=requsting_username):
            await interaction.response.send_message("You are already registered in this dungeon", ephemeral=True, delete_after=5)
            return
        if check_if_player_muted_or_in_queue(_id=self.doc_id, username=requsting_username, queue_or_mute="mute"):
            await interaction.response.send_message("You are muted by the owner, so you cant send a request to join the dungeon!")
            return
        try:
            user_class_name = self.user_selected_class[interacting_user_id]
            user_class_role = self.user_selected_class_role[interacting_user_id]
        except Exception:
            await interaction.response.send_message("You have to fill in class and class role!", ephemeral=True, delete_after=5)
        else:
            if interacting_user_id == self.creator_id:
                player_added = add_player_to_document(class_name=user_class_name, class_type_to_add=user_class_role, _id=self.doc_id, username=requsting_username)
                if player_added:
                    await interaction.response.send_message("Because you are the owner you have been registered without needing to queue!")
                    await self.update_embed()
                    await self.update_kicked_players_options()
                else:
                    await interaction.response.send_message("There was a problem registering you, may be because the dungeon is full or the role is full!")
            else:
                await interaction.response.send_message(f"{requsting_username}, Your request has been sent to {self.username}, who will decide whether to accept you", ephemeral=True, delete_after=5)
                embed = discord.Embed(title=f"{requsting_username} requested to join your dugeon party that starts at `{self.dungeon_start_time}`\n\nas {user_class_name} in role {user_class_role}\n\nApprove or reject?")
                message_dmed_to_user = await self.owner_user_object.send(embed=embed)
                
                dm_for_owner_view = DmOwnerForApproval(message_object=message_dmed_to_user ,username_for_approval=requsting_username, interacted_user_id=interacting_user_id, user_class_name=user_class_name, user_class_role=user_class_role, dungeon_instance=self)
                await message_dmed_to_user.edit(view=dm_for_owner_view)
                add_player_to_queue_or_mute_lists(_id=self.doc_id, username=requsting_username, queue_or_mute="queue")
                await self.update_embed()



    async def unregister_button_callback(self, interaction: discord.Interaction):
        player_deleted = delete_player_from_document(username=str(interaction.user), _id=self.doc_id)
        if player_deleted:
            await interaction.response.send_message("You have been successfully unregistered from the dungeon", ephemeral=True, delete_after=5)
            await self.update_embed()
        else:
            await interaction.response.send_message("There was a problem unregistering you from the dungeon, Probably becuase you are not registered!", ephemeral=True, delete_after=5)

    async def select_callback_class_name(self, interaction: discord.Interaction):
        self.user_selected_class[interaction.user.id] = interaction.data["values"][0]
        print(self.user_selected_class)
        await interaction.response.send_message(f"You have selected the class {interaction.data["values"][0]}", ephemeral=True, delete_after=5)


    async def select_callback_class_role(self, interaction: discord.Interaction):
        self.user_selected_class_role[interaction.user.id] = interaction.data["values"][0]
        print(self.user_selected_class_role)
        await interaction.response.send_message(f"You have selected the role {interaction.data["values"][0]}", ephemeral=True, delete_after=5)

    async def select_kicked_players_callback(self, interaction: discord.Interaction):
        self.all_dungeon_players = all_dungeon_players(self.doc_id)
        if self.all_dungeon_players:
            print(f"All dungeon Players : {self.all_dungeon_players}")
            if len(self.all_dungeon_players) > 0:
                self.select_kicked_players.options = [SelectOption(label=player) for player in self.all_dungeon_players]
                self.select_kicked_players.max_values = len(self.all_dungeon_players)
            else:
                self.select_kicked_players.max_values = 1
                self.select_kicked_players.options = [SelectOption(label="No players in dungeon!")]
            self.selected_kicked_users = interaction.data["values"]
            await interaction.response.send_message("Selected player/s successfully!", ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message("There are no players in the current dungeon!", ephemeral=True, delete_after=5)

        
#Discord bot functions
@bot.tree.command(name='create_dungeon', description="This command creates a dungeon!")
@app_commands.describe(date="Specify the dungeon date (YYYY-MM-DD Format)")
@app_commands.describe(hour="Specify the dungeon start time (H:M Format)")
async def create_dungeon(interaction: discord.Interaction, date: str, hour: str):
    try:
        concatenated_date = f"{date} {hour}"
        date_object = datetime.strptime(concatenated_date, "%Y-%m-%d %H:%M")
    except Exception:
        await interaction.response.send_message("Invalid format for date or hour, please use the specified format")
    new_doc_id = create_document(str(interaction.user), date=date_object)
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
        embed.add_field(name="Start Time :calendar_spiral: ", value=f"`{date_object}`")
        embed.add_field(name="Players in queue 🚦", value=check_length_of_players_in_queue(new_doc_id))


        await interaction.response.send_message(embed=embed)
        response_message = await interaction.original_response()
        view = ClassSelectorsView(doc_id=new_doc_id, message=response_message, creator_id=interaction.user.id, username=str(interaction.user), dungeon_start_time=date_object)
        await response_message.edit(view=view)









bot.run(token=TOKEN)