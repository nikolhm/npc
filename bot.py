import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

characters = {}
BACKUP_CHANNEL = 'npc-character-backup'

@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync the commands with Discord
    print(f'We have logged in as {bot.user}')

### CHARACTER COMMANDS ###
@bot.tree.command(name='create_character', description="Create a character and store it in a JSON file specific to this guild.")
async def create_character(interaction: discord.Interaction, name: str, image_url: str, *, background: str):
    guild_id = str(interaction.guild_id)

    if guild_id in characters and name in characters[guild_id]:
        await interaction.response.send_message(f"A character with the name '{name}' already exists in this guild!", ephemeral=True)
        return

    user = interaction.user
    user_id = str(user.id) 

    if guild_id not in characters:
        characters[guild_id] = {}

    characters[guild_id][name] = {
        'owner_id': user_id,
        'image_url': image_url,
        'background': background,
        'allowed_users': [user_id]  # Start with the creator having access
    }
    
    await interaction.response.send_message(f"Character '{name}' created and saved for this guild.", ephemeral=True)
    await export_characters(interaction, send_messages=False)

@bot.tree.command(name='delete_character', description="Delete a character from this guild.")
async def delete_character(interaction: discord.Interaction, name: str):
    guild_id = str(interaction.guild_id)
    if guild_id not in characters or name not in characters[guild_id]:
        await interaction.response.send_message(f"Character '{name}' does not exist in this guild.", ephemeral=True)
        return

    char_data = characters[guild_id].pop(name)
    await interaction.response.send_message(f"Character '{name}' has been deleted.", ephemeral=True)
    await export_characters(interaction, send_messages=False)

@bot.tree.command(name='edit_character', description="Edit a character's information.")
@app_commands.describe(
    name="The name of the character to edit",
    new_name="New name for the character (optional)",
    image_url="Image URL for the character (optional)",
    background="New description for the character (optional)"
)
async def edit_character(interaction: discord.Interaction, name: str, new_name: str = None, image_url: str = None, background: str = None):
    guild_id = str(interaction.guild_id)
    if guild_id not in characters or name not in characters[guild_id]:
        await interaction.response.send_message(f"Character '{name}' does not exist in this guild.", ephemeral=True)
        return

    char_data = characters[guild_id][name]
    user_id = str(interaction.user.id)
    if user_id != char_data['owner_id']:
        await interaction.response.send_message("You are not the owner of this character.", ephemeral=True)
        return

    if image_url:
        char_data['image_url'] = image_url
    if background:
        char_data['background'] = background
    if new_name:
        characters[guild_id][new_name] = char_data
        characters[guild_id].pop(name)
        name = new_name

    await interaction.response.send_message(f"Character '{name}' has been updated.", ephemeral=True)
    await export_characters(interaction, send_messages=False)

@bot.tree.command(name='allow_character', description="Allow another user to use a character in this guild.")
async def allow_character(interaction: discord.Interaction, character_name: str, user: discord.User):
    """Allow another user to use a character in this guild."""
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.author.id)
    
    if guild_id not in characters or character_name not in characters[guild_id]:
        await interaction.response.send_message(f"Character '{character_name}' does not exist in this guild.", ephemeral=True)
        return
    
    char_data = characters[guild_id][character_name]
    
    if char_data['owner_id'] != user_id:
        await interaction.response.send_message("You are not the owner of this character.", ephemeral=True)
        return
    
    char_data['allowed_users'].append(str(user.id))
    
    await interaction.response.send_message(f"User {user.name} can now use the character '{character_name}' in this guild.", ephemeral=True)
    await export_characters(interaction, send_messages=False)

@bot.tree.command(name='view_character', description="View a character's information.")
async def view_character(interaction: discord.Interaction, character_name: str):
    guild_id = str(interaction.guild_id)
    
    if guild_id not in characters or character_name not in characters[guild_id]:
        await interaction.response.send_message(f"Character '{character_name}' does not exist in this guild.", ephemeral=True)
        return
    
    char_data = characters[guild_id][character_name]
    channel = interaction.channel
    await export_json_to_channel(channel, {character_name: char_data})
    await interaction.response.send_message('Success!', ephemeral=True, delete_after=1)

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
    guild_id = str(interaction.guild_id)
    if guild_id not in characters or character_name not in characters[guild_id]:
        await interaction.response.send_message(f"Character `{character_name}` does not exist.", ephemeral=True)
        return

    character = characters[guild_id][character_name]
    user_id = str(interaction.user.id)
    if user_id not in character["allowed_users"]:
        await interaction.response.send_message(f"You do not have permission to use the character `{character_name}`.", ephemeral=True)
        return

    channel = interaction.channel
    webhook = await get_or_create_webhook(channel, "CharacterWebhook")
    await send_webhook_message(webhook, character_name, character["image_url"], message)
    await interaction.response.send_message('Success!', ephemeral=True, delete_after=1)

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
    if guild_id not in characters:
        characters[guild_id] = {}

    characters[guild_id].update(characters_data)

    await interaction.response.send_message(f"Characters loaded successfully from message.", ephemeral=True)
 
@bot.tree.command(name="export_characters", description="Export the list of characters as JSON to the back up channel")
async def export_characters_manual(interaction: discord.Interaction, send_messages: bool = True):
    await export_characters(interaction, send_messages)

async def export_characters(interaction, send_messages):
    guild_id = str(interaction.guild_id)
    if not characters or guild_id not in characters:
        await interaction.response.send_message("No characters to export.", ephemeral=True)
        return

    private_channel = discord.utils.get(interaction.guild.text_channels, name=BACKUP_CHANNEL)
    if private_channel:
        await export_json_to_channel(private_channel, characters[guild_id])
        if send_messages:
            await interaction.response.send_message("Characters exported successfully.", ephemeral=True)
    else:
        await interaction.response.send_message("Backup channel not found. Please run init", ephemeral=True)

async def export_json_to_channel(channel, data):
    with open("characters.json", "w") as f:
        json.dump(data, f, indent=4)

    await channel.send(file=discord.File("characters.json"))
    os.remove("characters.json")

bot.run(os.getenv('DISCORD_TOKEN'))