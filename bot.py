import discord
from discord.ext import commands
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
characters = load_character_data()

# Command to create a character and save to JSON
@bot.command()
async def create_character(ctx, name: str, image_url: str, *, background: str):
    """Create a character and store it in a JSON file specific to this guild."""
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if guild_id not in characters:
        characters[guild_id] = {}

    if name in characters[guild_id]:
        await ctx.send(f"A character with the name '{name}' already exists in this guild!")
        return

    characters[guild_id][name] = {
        'owner_id': user_id,
        'image_url': image_url,
        'background': background,
        'allowed_users': [user_id]  # Start with the creator having access
    }
    
    # Save updated characters to JSON
    save_character_data(characters)
    
    await ctx.send(f"Character '{name}' created and saved for this guild.")

# Command to use a character
@bot.command()
async def use_character(ctx, name: str):
    """Switch to a character in this guild."""
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if guild_id not in characters or name not in characters[guild_id]:
        await ctx.send(f"Character '{name}' does not exist in this guild.")
        return
    
    char_data = characters[guild_id][name]
    if user_id not in char_data['allowed_users']:
        await ctx.send("You don't have permission to use this character.")
        return

    bot.current_character = name
    await ctx.send(f"You are now using the character '{name}'.")

# Command to send a message as a character
@bot.event
async def on_message(message):
    """Send a message as a character if a character is in use."""
    if message.author == bot.user:
        return

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)
    character_name = getattr(bot, "current_character", None)

    if character_name and guild_id in characters:
        char_data = characters[guild_id].get(character_name)
        if char_data and user_id in char_data['allowed_users']:
            embed = discord.Embed(description=message.content)
            embed.set_author(name=character_name)
            embed.set_thumbnail(url=char_data['image_url'])
            await message.channel.send(embed=embed)
            await message.delete()  # Delete original message
        else:
            await message.channel.send("You don't have permission to use this character.")
            return
    await bot.process_commands(message)

# Command to allow another user to use the character
@bot.command()
async def allow_character(ctx, character_name: str, user: discord.User):
    """Allow another user to use a character in this guild."""
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if guild_id not in characters or character_name not in characters[guild_id]:
        await ctx.send(f"Character '{character_name}' does not exist in this guild.")
        return
    
    char_data = characters[guild_id][character_name]
    
    if char_data['owner_id'] != user_id:
        await ctx.send("You are not the owner of this character.")
        return
    
    char_data['allowed_users'].append(str(user.id))
    
    # Save updated characters to JSON
    save_character_data(characters)
    
    await ctx.send(f"User {user.name} can now use the character '{character_name}' in this guild.")

# Command to get character info
@bot.command()
async def character_info(ctx, name: str):
    """Get character info, including background, for this guild."""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in characters or name not in characters[guild_id]:
        await ctx.send(f"Character '{name}' not found in this guild.")
        return
    
    char_data = characters[guild_id][name]
    owner = await bot.fetch_user(int(char_data['owner_id']))
    
    embed = discord.Embed(title=f"Character Info: {name}")
    embed.set_thumbnail(url=char_data['image_url'])
    embed.add_field(name="Owner", value=owner.name)
    embed.add_field(name="Background", value=char_data['background'])
    
    await ctx.send(embed=embed)

# Command to load character data from a message in a channel
@bot.command()
async def init_from_message(ctx, channel: discord.TextChannel, message_id: int):
    """Initialize character data from a JSON message in a specified channel for this guild."""
    guild_id = str(ctx.guild.id)
    
    try:
        message = await channel.fetch_message(message_id)
        json_data = json.loads(message.content)  # Assuming the message content is JSON
        
        if guild_id not in characters:
            characters[guild_id] = {}
        
        # Load the JSON data into the bot's character data and save it
        characters[guild_id].update(json_data)
        save_character_data(characters)
        
        await ctx.send("Character data successfully initialized from the message for this guild.")
    except discord.NotFound:
        await ctx.send(f"Message with ID {message_id} not found in {channel.name}.")
    except json.JSONDecodeError:
        await ctx.send("Failed to parse JSON data from the message.")

# Run the bot
bot.run('token')
