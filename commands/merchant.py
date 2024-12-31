import discord
from discord import app_commands
import random
import math
from . import db
from . import character as char_commands

TRANSACTION_CHANNEL = 'npc-transactions'

async def create_transaction_channel(guild: discord.Guild):
    if discord.utils.get(guild.text_channels, name=TRANSACTION_CHANNEL):
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    channel = await guild.create_text_channel(TRANSACTION_CHANNEL, overwrites=overwrites)
    await channel.edit(topic="NPC-generated channel for posting transaction data.")

def get_inventory_item(character_id, item_name):
    connection = db.create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM inventory WHERE character_id = :character_id AND name = :name", {'character_id': character_id, 'name': item_name})
    result = cursor.fetchone()
    cursor.close()
    if result:
        result = {
            'id': result[0],
            'character_id': result[1],
            'name': result[2],
            'quantity': result[3],
            'info': result[4],
            'price': result[5],
            'discount': result[6],
            'discount_threshold': result[7]
        }
    return result

def get_all_inventory(character_id):
    connection = db.create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM inventory WHERE character_id = :character_id ORDER BY id", {'character_id': character_id})
    result = cursor.fetchall()
    cursor.close()
    return result

# publish transaction to a transaction channel, for gameplay recordkeeping
async def publish_transaction(interaction: discord.Interaction, character, item, quantity, price, got_discount):
    transaction_channel = discord.utils.get(interaction.guild.text_channels, name=TRANSACTION_CHANNEL)
    if not transaction_channel:
        await create_transaction_channel(interaction.guild)
        transaction_channel = discord.utils.get(interaction.guild.text_channels, name=TRANSACTION_CHANNEL)

    if not transaction_channel:
        await interaction.followup.send("Transaction channel couldn't be created, please try again.", ephemeral=True)
        return
    
    receipt = f"Player `{interaction.user.name}` bought {quantity} of item `{item}` for {price} gold from {character}"
    if got_discount:
        receipt += " with a discount"
    
    await transaction_channel.send(receipt)

@app_commands.command(name="add_inventory", description="Add an item to a character's inventory")
@app_commands.describe(
    character="The character to add the item to",
    item_name="The name of the item",
    quantity="The number of items to add",
    info="Additional information about the item",
    price="The price of the item (default 1)",
    discount="The discount percentage for the item (default 0)",
    discount_threshold="The value players can roll to get a discount (default 0)"
)
async def add_inventory(interaction: discord.Interaction, character: str, item_name: str, quantity: int, info: str = None, price: int = 1, discount: int = 0, discount_threshold: int = 0):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    ch = char_commands.get_character(guild_id, character)
    if not ch:
        await interaction.followup.send(f"Character `{character}` does not exist.", ephemeral=True)
        return

    if not await char_commands.allowed_users_check(interaction, ch):
        return
    
    if get_inventory_item(ch["id"], item_name):
        await interaction.followup.send(f"Item `{item_name}` already exists in character `{character}`'s inventory.", ephemeral=True)
        return

    connection = db.create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO inventory (id, character_id, name, quantity, info, price, discount, discount_threshold) VALUES (inventory_seq.nextval, :character_id, :name, :quantity, :info, :price, :discount, :discount_threshold)", {'character_id': ch["id"], 'name': item_name, 'quantity': quantity, 'info': info, 'price': price, 'discount': discount, 'discount_threshold': discount_threshold})
    connection.commit()
    cursor.close()

    await interaction.followup.send(f"Item `{item_name}` added to character `{character}`'s inventory.", ephemeral=True)

@app_commands.command(name="edit_inventory", description="Edit an item from a character's inventory")
@app_commands.describe(
    character="The character to add the item to",
    item_name="The name of the item",
    new_item_name="The new name of the item",
    quantity="The number of items",
    info="Additional information about the item",
    price="The price of the item",
    discount="The discount percentage for the item",
    discount_threshold="The value players can roll to get a discount"
)
async def edit_inventory(interaction: discord.Interaction, character: str, item_name: str, new_item_name: str = None, quantity: int = 0, info: str = None, price: int = 0, discount: int = 0, discount_threshold: int = 0):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    ch = char_commands.get_character(guild_id, character)
    if not ch:
        await interaction.followup.send(f"Character `{character}` does not exist.", ephemeral=True)
        return

    if not await char_commands.allowed_users_check(interaction, ch):
        return
    
    item = get_inventory_item(ch["id"], item_name)
    if not item:
        await interaction.followup.send(f"Item `{item_name}` does not exist in character `{character}`'s inventory.", ephemeral=True)
        return
    
    item['name'] = new_item_name if new_item_name else item['name']
    item['quantity'] = quantity if quantity else item['quantity']
    item['info'] = info if info else item['info']
    item['price'] = price if price else item['price']
    item['discount'] = discount if discount else item['discount']
    item['discount_threshold'] = discount_threshold if discount_threshold else item['discount_threshold']

    connection = db.create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE inventory SET name = :name, quantity = :quantity, info = :info, price = :price, discount = :discount, discount_threshold = :discount_threshold WHERE character_id = :character_id AND name = :old_name", {'name': item['name'], 'quantity': item['quantity'], 'info': item['info'], 'price': item['price'], 'discount': item['discount'], 'discount_threshold': item['discount_threshold'], 'character_id': ch["id"], 'old_name': item_name})
    connection.commit()
    cursor.close()

    await interaction.followup.send(f"Item `{item_name}` edited in character `{character}`'s inventory.", ephemeral=True)

@app_commands.command(name="remove_inventory", description="Remove an item from a character's inventory")
@app_commands.describe(
    character="The character to remove the item from",
    item_name="The name of the item",
)
async def remove_inventory(interaction: discord.Interaction, character: str, item_name: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    ch = char_commands.get_character(guild_id, character)
    if not ch:
        await interaction.followup.send(f"Character `{character}` does not exist.", ephemeral=True)
        return

    if not await char_commands.allowed_users_check(interaction, ch):
        return
    
    if not get_inventory_item(ch["id"], item_name):
        await interaction.followup.send(f"Item `{item_name}` does not exist in character `{character}`'s inventory.", ephemeral=True)
        return

    connection = db.create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM inventory WHERE character_id = :character_id AND name = :name", {'character_id': ch["id"], 'name': item_name})
    connection.commit()
    cursor.close()

    await interaction.followup.send(f"Item `{item_name}` removed from character `{character}`'s inventory.", ephemeral=True)

@app_commands.command(name="add_stock", description="Add stock to an item in a character's inventory")
@app_commands.describe(
    character="The character to add stock to",
    item_name="The name of the item",
    quantity="The number of items to add",
)
async def add_stock(interaction: discord.Interaction, character: str, item_name: str, quantity: int):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    ch = char_commands.get_character(guild_id, character)
    if not ch:
        await interaction.followup.send(f"Character `{character}` does not exist.", ephemeral=True)
        return

    if not await char_commands.allowed_users_check(interaction, ch):
        return
    
    item = get_inventory_item(ch["id"], item_name)
    if not item:
        await interaction.followup.send(f"Item `{item_name}` does not exist in character `{character}`'s inventory.", ephemeral=True)
        return

    connection = db.create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE inventory SET quantity = quantity + :quantity WHERE character_id = :character_id AND name = :name", {'quantity': quantity, 'character_id': ch["id"], 'name': item_name})
    connection.commit()
    cursor.close()

    await interaction.followup.send(f"Stock added to item `{item_name}` in character `{character}`'s inventory.", ephemeral=True)

@app_commands.command(name="see_inventory", description="See a character's inventory")
@app_commands.describe(
    character="The character to see the inventory of",
)
async def see_inventory(interaction: discord.Interaction, character: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    ch = char_commands.get_character(guild_id, character)
    if not ch:
        await interaction.followup.send(f"Character `{character}` does not exist.", ephemeral=True)
        return
    
    see_more = await char_commands.allowed_users_check(interaction, ch)

    items = get_all_inventory(ch["id"])
    if not items:
        await interaction.followup.send(f"Character `{character}`'s inventory is empty.", ephemeral=True)
        return

    items_str = ""
    for item in items:
        items_str += f"{item[2]}: {item[3]}"
        if item[4]:
            items_str += f"; {item[4]}"
        if see_more:
            items_str += f"; {item[5]} gold"
            if item[6] > 0:
                items_str += f"; {item[6]}% discount at roll {item[7]}"
        items_str += "\n"

    await interaction.followup.send(f"Character `{character}`'s inventory:\n{items_str}", ephemeral=True)

@app_commands.command(name="buy_item", description="Buy an item from a character's inventory")
@app_commands.describe(
    character="The character to buy the item from",
    item_name="The name of the item",
    quantity="The number of items to buy",
)
async def buy_item(interaction: discord.Interaction, character: str, item_name: str, quantity: int = 1):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    ch = char_commands.get_character(guild_id, character)
    if not ch:
        await interaction.followup.send(f"Character `{character}` does not exist.", ephemeral=True)
        return
    
    item = get_inventory_item(ch["id"], item_name)
    if not item:
        await interaction.followup.send(f"Item `{item_name}` does not exist in character `{character}`'s inventory.", ephemeral=True)
        return
    
    if item['quantity'] < quantity:
        await interaction.followup.send(f"Character `{character}` does not have enough stock of item `{item_name}`.", ephemeral=True)
        return
    
    price = item['price']
    got_discount = False

    if item['discount'] > 0:
        view = BarterView()
        await interaction.followup.send("Would you like to roll to barter?", view=view, ephemeral=True)
        await view.wait()
        if view.result == 'barter':
            # choose random number between 1 and 20
            roll = random.randint(1, 20)
            if roll >= item['discount_threshold'] or roll == 20:
                # round up to nearest integer, don't deal w decimals in rpgs
                price = price - math.ceil(price * item['discount'] / 100)
                got_discount = True
                await interaction.followup.send(f"Barter successful! Price reduced to {price}.", ephemeral=True)
            else:
                await interaction.followup.send(f"Barter failed! Price remains at {price}.", ephemeral=True)

    connection = db.create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE inventory SET quantity = quantity - :quantity WHERE character_id = :character_id AND name = :name", {'quantity': quantity, 'character_id': ch["id"], 'name': item_name})
    connection.commit()
    cursor.close()

    await publish_transaction(interaction, character, item_name, quantity, price * quantity, got_discount)
    await interaction.followup.send(f"Item `{item_name}` bought from character `{character}`.", ephemeral=True)

class BarterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.result = None

    @discord.ui.button(label="Roll to barter", style=discord.ButtonStyle.primary)
    async def roll_to_barter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Rolling to barter...", ephemeral=True)
        self.result = 'barter'
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Barter cancelled. Paying full price.", ephemeral=True)
        self.stop()
