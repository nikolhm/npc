import discord
from discord import app_commands
import aiohttp
from . import character

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

@app_commands.command(name="speak_as", description="Send a message as a character")
async def speak_as_character(interaction: discord.Interaction, character_name: str, message: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    ch = character.get_character(guild_id, character_name)
    if not ch:
        await interaction.followup.send(f"Character `{character_name}` does not exist.", ephemeral=True)
        return

    if not await character.allowed_users_check(interaction, ch):
        return

    channel = interaction.channel
    webhook = await get_or_create_webhook(channel, "NpcCharacterWebhook")
    try:
        await send_webhook_message(webhook, character_name, ch["image_url"], message)
    except Exception as e:
        print(e)
        await interaction.followup.send("Failed to send message due to an error. Please check your character settings or try again later.", ephemeral=True)
        return
    
    msg = await interaction.followup.send('Success!', ephemeral=True)
    await msg.delete(delay=2)