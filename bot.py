import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# Set up intents and bot prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Define the path to the JSON file where character data will be stored
CHARACTERS_FILE = 'characters.json'

# Load character data from JSON file
def load_character_data():
    if os.path.exists(CHARACTERS_FILE):
        with open(CHARACTERS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save character data to JSON file
def save_character_data(data):
    with open(CHARACTERS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize character data on startup
characters = {}

# Register slash commands
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync the commands with Discord
    print(f'We have logged in as {bot.user}')

# Command to create a character and save to JSON
@bot.tree.command(name='create_character', description="Create a character and store it in a JSON file specific to this guild.")
async def create_character(interaction: discord.Interaction, name: str, image_url: str, *, background: str):
    guild_id = str(interaction.guild_id)

    if guild_id in characters and name in characters[guild_id]:
        await interaction.response.send_message(f"A character with the name '{name}' already exists in this guild!")
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
    
    await interaction.response.send_message(f"Character '{name}' created and saved for this guild.")

# Slash command to speak as a character
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

    # Send the message as the specified character
    embed = discord.Embed(description=message, color=discord.Color.blue())
    embed.set_author(name=character_name)
    
    await channel.send(embed=embed)
    await interaction.response.send_message(f"Message sent as `{character_name}`.", ephemeral=True)

# Command to allow another user to use the character
@bot.tree.command(name='allow_character', description="Allow another user to use a character in this guild.")
async def allow_character(interaction: discord.Interaction, character_name: str, user: discord.User):
    """Allow another user to use a character in this guild."""
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.author.id)
    
    if guild_id not in characters or character_name not in characters[guild_id]:
        await interaction.response.send_message(f"Character '{character_name}' does not exist in this guild.")
        return
    
    char_data = characters[guild_id][character_name]
    
    if char_data['owner_id'] != user_id:
        await interaction.response.send_message("You are not the owner of this character.")
        return
    
    char_data['allowed_users'].append(str(user.id))
    
    # Save updated characters to JSON
    save_character_data(characters)
    
    await interaction.response.send_message(f"User {user.name} can now use the character '{character_name}' in this guild.")

# Slash command to load characters from JSON message
@bot.tree.command(name="load_characters", description="Load characters from a JSON message")
@app_commands.describe(message_id="The ID of the message containing the JSON data")
async def load_characters(interaction: discord.Interaction, message_id: str):
    channel = interaction.channel

    try:
        message = await channel.fetch_message(int(message_id))

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

        await interaction.response.send_message(f"Characters loaded successfully from message {message_id}.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to load characters: {str(e)}", ephemeral=True)

# Command to export character data to a message in a channel
@bot.tree.command(name="export_characters", description="Export the list of characters as JSON")
async def export_characters(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    if not characters or guild_id not in characters:
        await interaction.response.send_message("No characters to export.", ephemeral=True)
        return

    with open("characters.json", "w") as f:
        json.dump(characters[guild_id], f, indent=4)

    # Send the JSON file to the channel
    await interaction.response.send_message(file=discord.File("characters.json"))
    # Delete the JSON file after sending
    os.remove("characters.json")

# Run the bot
# bot.run(os.getenv('DISCORD_TOKEN'))
bot.run('MTI4MTAzMzkzOTY2NTk0ODcyNQ.Gj36yY.D9j5aDj5zUUVlLvLFoOD9Dzy_Z4zMfgvrZyGDI')
