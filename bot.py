import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import os
import oracledb
import yaml
import platform

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

BACKUP_CHANNEL = 'npc-character-backup'

def load_config():
    with open("./db-info/config.yml", "r") as file:
        return yaml.safe_load(file)

config = load_config()

def create_oracle_connection():
    connection = oracledb.connect(
        user=config['oracle_db']['user'],
        password=config['oracle_db']['password'],
        dsn=config['oracle_db']['dsn'],
    )
    return connection

### START UP ###
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync the / commands with Discord
    create_character_table()

def create_character_table():
    connection = create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute('''
        SELECT table_name 
        FROM user_tables 
        WHERE table_name = 'CHARACTERS'
    ''')
    table_exists = cursor.fetchone()
    
    if not table_exists:
        cursor.execute('''
            CREATE TABLE characters (
                guild_id VARCHAR2(50),
                character_name VARCHAR2(50),
                owner_id VARCHAR2(50),
                image_url VARCHAR2(255),
                background VARCHAR2(1000),
                allowed_users CLOB
            )
        ''')
        connection.commit()
    cursor.close()
    connection.close()

### CHARACTER COMMANDS ###
async def owner_check(interaction, character):
    user_id = str(interaction.user.id)
    if user_id != character['owner_id']:
        await interaction.followup.send("You are not the owner of this character.", ephemeral=True)
        return False
    return True

async def allowed_users_check(interaction, character):
    user_id = str(interaction.user.id)
    if user_id not in character['allowed_users']:
        await interaction.followup.send("You do not have permission to use this character.", ephemeral=True)
        return False
    return True

def get_character(guild_id, name):
    connection = create_oracle_connection()
    cursor = connection.cursor()

    cursor.execute('''
        SELECT character_name, owner_id, image_url, background, allowed_users
        FROM characters
        WHERE guild_id = :guild_id AND character_name = :name
    ''', {"guild_id": guild_id, "name": name})

    character = cursor.fetchone()
    if character:
        character = {
            "name": character[0],
            "owner_id": character[1],
            "image_url": character[2],
            "background": character[3],
            "allowed_users": json.loads(character[4].read())
        }

    cursor.close()
    connection.close()
    return character

@bot.tree.command(name='create_character', description="Create a character specific to this guild.")
@app_commands.describe(
    name="The name of the character to edit (50 character limit)",
    image_url="Image URL for the character",
    background="New description for the character (1000 character limit)"
)
async def create_character(interaction: discord.Interaction, name: str, image_url: str, *, background: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)

    if get_character(guild_id, name):
        await interaction.followup.send(f"A character with the name '{name}' already exists in this guild!", ephemeral=True)
        return

    user = interaction.user
    user_id = str(user.id) 

    try:
        connection = create_oracle_connection()
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO characters (guild_id, character_name, owner_id, image_url, background, allowed_users)
            VALUES (:guild_id, :name, :owner_id, :image_url, :background, :allowed_users)
        ''', {
            "guild_id": guild_id, 
            "name": name, 
            "owner_id": user_id, 
            "image_url": image_url, 
            "background": background, 
            "allowed_users": json.dumps([user_id])
        })
        connection.commit()
        await interaction.followup.send(f"Character '{name}' created and saved for this guild.", ephemeral=True)
        await export_characters(interaction, send_messages=False)
    except Exception as e:
        await interaction.followup.send(f"Failed to create character due to an error: {str(e)}", ephemeral=True)
    finally:
        cursor.close()
        connection.close()

@bot.tree.command(name='delete_character', description="Delete a character from this guild.")
async def delete_character(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    character = get_character(guild_id, name)
    if not character:
        await interaction.followup.send(f"Character '{name}' does not exist in this guild.", ephemeral=True)
        return

    if not await owner_check(interaction, character):
        return

    try: 
        connection = create_oracle_connection()
        cursor = connection.cursor()
        cursor.execute('''
            DELETE FROM characters
            WHERE guild_id = :guild_id AND character_name = :name
        ''', {"guild_id": guild_id, "name": name})
        connection.commit()
        await interaction.followup.send(f"Character '{name}' has been deleted.", ephemeral=True)
        await export_characters(interaction, send_messages=False)
    except Exception as e:
        await interaction.followup.send(f"Failed to delete character due to an error: {str(e)}", ephemeral=True)
    finally:
        cursor.close()
        connection.close()

class ConfirmDeleteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger, custom_id="confirm_delete_all_characters")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild_id)
        connection = create_oracle_connection()
        cursor = connection.cursor()
        cursor.execute('''
            DELETE FROM characters
            WHERE guild_id = :guild_id
        ''', {"guild_id": guild_id})
        connection.commit()
        cursor.close()
        connection.close()
        # send empty json to backup channel, but leave older messages for recovery
        private_channel = discord.utils.get(interaction.guild.text_channels, name=BACKUP_CHANNEL)
        if private_channel:
            await export_json_to_channel(private_channel, {})
        await interaction.response.send_message("All characters have been deleted from this guild.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_delete_all_characters")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Deletion of all characters has been cancelled.", ephemeral=True)
        self.stop()

@bot.tree.command(name='delete_all_characters', description="Delete all characters from this guild.")
async def delete_all_characters(interaction: discord.Interaction):
    view = ConfirmDeleteView()
    await interaction.response.send_message("Are you sure you want to delete all characters in this guild?", ephemeral=True, view=view)

@bot.tree.command(name='edit_character', description="Edit a character's information.")
@app_commands.describe(
    name="The name of the character to edit",
    new_name="New name for the character (optional)",
    image_url="Image URL for the character (optional)",
    background="New description for the character (optional)"
)
async def edit_character(interaction: discord.Interaction, name: str, new_name: str = None, image_url: str = None, background: str = None):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    character = get_character(guild_id, name)
    if not character:
        await interaction.followup.send(f"Character '{name}' does not exist in this guild.", ephemeral=True)
        return

    if not await allowed_users_check(interaction, character):
        return

    if image_url:
        character['image_url'] = image_url
    if background:
        character['background'] = background
    if new_name:
        character['name'] = new_name
        name = new_name

    try:
        connection = create_oracle_connection()
        cursor = connection.cursor()
        cursor.execute('''
            UPDATE characters
            SET character_name = :new_name, image_url = :image_url, background = :background
            WHERE guild_id = :guild_id AND character_name = :name
        ''', {
            "new_name": character['name'], 
            "image_url": character['image_url'], 
            "background": character['background'], 
            "guild_id": guild_id, 
            "name": name
        })
        connection.commit()
        await interaction.followup.send(f"Character '{name}' has been updated.", ephemeral=True)
        await export_characters(interaction, send_messages=False)
    except Exception as e:
        await interaction.followup.send(f"Failed to update character due to an error: {str(e)}", ephemeral=True)
    finally:
        cursor.close()
        connection.close()

@bot.tree.command(name='allow_character', description="Allow another user to use a character in this guild.")
async def allow_character(interaction: discord.Interaction, character_name: str, user: discord.User):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    character = get_character(guild_id, character_name)
    
    if not character:
        await interaction.followup.send(f"Character '{character_name}' does not exist in this guild.", ephemeral=True)
        return
        
    if not await owner_check(interaction, character):
        return
    
    character['allowed_users'].append(str(user.id))
    try:
        connection = create_oracle_connection()
        cursor = connection.cursor()
        cursor.execute('''
            UPDATE characters
            SET allowed_users = :allowed_users
            WHERE guild_id = :guild_id AND character_name = :name
        ''', {
            "allowed_users": json.dumps(character['allowed_users']), 
            "guild_id": guild_id, 
            "name": character_name
        })
        connection.commit()
        await interaction.followup.send(f"User {user.name} can now use the character '{character_name}' in this guild.", ephemeral=True)
        await export_characters(interaction, send_messages=False)
    except Exception as e:
        await interaction.followup.send(f"Failed to allow user due to an error: {str(e)}", ephemeral=True)
        return
    finally:
        cursor.close()
        connection.close()

@bot.tree.command(name='view_character', description="View a character's information.")
async def view_character(interaction: discord.Interaction, character_name: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    character = get_character(guild_id, character_name)
    
    if not character:
        await interaction.followup.send(f"Character '{character_name}' does not exist in this guild.", ephemeral=True)
        return

    if not await allowed_users_check(interaction, character):
        return
    
    channel = interaction.channel
    await export_json_to_channel(channel, {[character_name]: character})
    msg = await interaction.followup.send('Success!', ephemeral=True)
    await msg.delete(delay=2)

### SENDING MESSAGES AS CHARACTERS ###
async def get_or_create_webhook(channel: discord.TextChannel, name: str):
    webhooks = await channel.webhooks()
    webhook = discord.utils.get(webhooks, name=name)
    
    if webhook is None:
        webhook = await channel.create_webhook(name=name)
    
    return webhook

async def send_webhook_message(webhook: discord.Webhook, username: str, avatar_url: str, content: str):
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(webhook.url, session=session)
        await webhook.send(content=content, username=username, avatar_url=avatar_url)

@bot.tree.command(name="speak_as", description="Send a message as a character")
async def speak_as_character(interaction: discord.Interaction, character_name: str, message: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    character = get_character(guild_id, character_name)
    if not character:
        await interaction.followup.send(f"Character `{character_name}` does not exist.", ephemeral=True)
        return

    if not await allowed_users_check(interaction, character):
        return

    channel = interaction.channel
    webhook = await get_or_create_webhook(channel, "NpcCharacterWebhook")
    try:
        await send_webhook_message(webhook, character_name, character["image_url"], message)
    except Exception as e:
        await interaction.followup.send("Failed to send message due to an error. Please check your character settings or try again later.", ephemeral=True)
        return
    
    msg = await interaction.followup.send('Success!', ephemeral=True)
    await msg.delete(delay=2)

### CHARACTER DATA MANAGEMENT ###
async def create_backup_channel(guild: discord.Guild):
    if discord.utils.get(guild.text_channels, name=BACKUP_CHANNEL):
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    channel = await guild.create_text_channel(BACKUP_CHANNEL, overwrites=overwrites)
    await channel.edit(topic="NPC-generated channel for storing character data backups.")


@bot.tree.command(name="init", description="Init or refresh the character data from the backup channel")
async def init(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    private_channel = discord.utils.get(interaction.guild.text_channels, name=BACKUP_CHANNEL)
    if private_channel:
        # Fetch the last message from the private channel
        messages = [message async for message in private_channel.history(limit=1)]
        if messages:
            last_message = messages[0]
            try:
                await load_character_data(interaction, last_message)
            except json.JSONDecodeError:
                await interaction.response.send_message("Failed to load character data. The data might be corrupted.", ephemeral=True)
        else:
            await interaction.response.send_message("No backup message found in the private channel.", ephemeral=True)
    else:
        await interaction.response.send_message("Backup channel not found, creating one.", ephemeral=True)
        await create_backup_channel(interaction.guild)
        await interaction.response.edit_message("Backup channel created. Add a character JSON to that channel and rerun command to upload.", ephemeral=True)

@bot.tree.command(name="load_characters_from_message", description="Load characters from a JSON message")
@app_commands.describe(message_id="The ID of the message containing the JSON data")
async def load_characters_from_message(interaction: discord.Interaction, message_id: str):
    channel = interaction.channel

    try:
        message = await channel.fetch_message(int(message_id))
        load_character_data(interaction, message)  
    except Exception as e:
        await interaction.response.send_message(f"Failed to load characters: {str(e)}", ephemeral=True)

async def load_character_data(interaction: discord.Interaction, message: discord.Message):
    if not message.attachments:
        await interaction.response.send_message("No file attachments found in the message.", ephemeral=True)
        return

    # Assuming there's only one attachment
    attachment = message.attachments[0]

    file = await attachment.read()
    try:
        characters_data = json.loads(file.decode('utf-8'))
    except json.JSONDecodeError:
        await interaction.response.send_message("The file content is not valid JSON.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    try:
        connection = create_oracle_connection()
        cursor = connection.cursor()
        for character_name, character_info in characters_data.items():        
            cursor.execute('''
                INSERT INTO characters (guild_id, character_name, owner_id, image_url, background, allowed_users)
                VALUES (:guild_id, :name, :owner_id, :image_url, :background, :allowed_users)
            ''', {
                'guild_id': guild_id,
                'name': character_name,
                'owner_id': character_info['owner_id'],
                'image_url': character_info.get('image_url', ''),
                'background': character_info.get('background', ''),
                'allowed_users': json.dumps(character_info.get('allowed_users', []))
            })
        connection.commit()
        await interaction.response.send_message(f"Characters loaded successfully from message.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to load characters: {str(e)}", ephemeral=True)
    finally:
        cursor.close()
        connection.close()
 
@bot.tree.command(name="export_characters_manual", description="Export the list of characters as JSON to the back up channel")
async def export_characters_manual(interaction: discord.Interaction, send_messages: bool = True):
    await export_characters(interaction, send_messages)

async def export_characters(interaction, send_messages):
    guild_id = str(interaction.guild_id)
    connection = create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute('''
        SELECT character_name, owner_id, image_url, background, allowed_users
        FROM characters
        WHERE guild_id = :guild_id
    ''', {"guild_id": guild_id})
    characters = cursor.fetchall()
    if not characters or len(characters) == 0:
        if send_messages:
            await interaction.response.send_message("No characters to export.", ephemeral=True)
        cursor.close()
        connection.close()
        return

    characters_data = {}
    for character in characters:
        characters_data[character[0]] = {
            "owner_id": character[1],
            "image_url": character[2],
            "background": character[3],
            "allowed_users": json.loads(character[4].read())
        }
    cursor.close()
    connection.close()

    private_channel = discord.utils.get(interaction.guild.text_channels, name=BACKUP_CHANNEL)
    if private_channel:
        await export_json_to_channel(private_channel, characters_data)
        if send_messages:
            await interaction.followup.send("Characters exported successfully.", ephemeral=True)
    else:
        await interaction.followup.send("Backup channel not found. Please run /init", ephemeral=True)

async def export_json_to_channel(channel, data):
    with open("characters.json", "w") as f:
        json.dump(data, f, indent=4)

    await channel.send(file=discord.File("characters.json"))
    os.remove("characters.json")

bot.run(os.getenv('DISCORD_TOKEN'))