# NPC Discord Bot

## Overview

This Discord bot allows you to manage and interact with characters in your server. It supports creating, editing, and deleting characters, as well as sending messages as those characters using webhooks. It also provides functionality for exporting and importing character data to and from a backup channel.

![Demo](https://github.com/f1nn3g4n/npc/blob/main/demo/demo.gif)

## Features

- **Create Characters**: Store character data including name, image URL, and background.
- **Edit Characters**: Modify existing character details.
- **Delete Characters**: Remove characters from the guild.
- **Allow Access**: Grant other users permission to use specific characters.
- **View Characters**: Retrieve and view character information.
- **Speak as Character**: Send messages as a character using webhooks.
- **Backup and Restore**: Export character data to a backup channel and load it from a JSON message.
- **Configure Asynchronous Marketplaces**: Allow your players to buy items from characters and use their loot! Avoid setting aside playtime to barter and sell.

## Prerequisites

- Python 3.8 or higher
- `discord.py`, `pyyaml` and `aiohttp` libraries

## Installation

1. **Clone the Repository**

2. **Install Python3 and Pip3**

3. **Install Dependencies**:

   ```bash
   pip3 install discord.py
   ```

4. **Set up your bot token in the os environment, or paste in file**

## Usage

1. **Run the Bot**:

   ```bash
   python3 bot.py
   ```

2. **Bot Commands**:

   - `/create_character <name> <image_url> <background>`: Create a new character.
   - `/delete_character <name>`: Delete a character.
   - `/delete_all_characters`: Delete all characters for the server.
   - `/edit_character <name> [new_name] [image_url] [background]`: Edit a character's details.
   - `/allow_character <character_name> <user>`: Allow another user to use a character.
   - `/view_character <character_name>`: View a character's information.
   - `/speak_as <character_name> <message>`: Send a message as a character.
   - `/init`: Initialize or refresh character data from the backup channel.
   - `/load_characters_from_message <message_id>`: Load characters from a JSON message.
   - `/export_characters_manual`: Export character data to the backup channel.
   - `/add_inventory`: Give your character inventory for your party to buy!
   - `/edit_inventory`: Edit the existing inventory for a character.
   - `/remove_inventory`: Remove an inventory item for a character.
   - `/add_stock`: Add inventory stock for a character.
   - `/see_inventory`: See inventory for a character. Allowed users see all details about the items, while everyone else only sees the name, price, and description.
   - `/buy_item`: Purchase an item from a character.

## Configuration

### Backup Channel

The bot uses a specific text channel named `npc-character-backup` for backing up and restoring character data. If this channel doesn't exist, the bot will create it.

### Environment Variables

- **DISCORD_TOKEN**: Your Discord bot token. Make sure this is set in your environment.
- **Oracle DB information**: This bot is designed to use an Oracle Cloud DB in Light mode. Copy `example-config.yml` and rename to `config.yml` with your DB information.

## Troubleshooting

- **Bot not responding**: Ensure your bot token is correct and that the bot has the necessary permissions in your server.
- **Commands not working**: Make sure your bot is properly synced with Discord's API and has the necessary permissions to execute commands.
- **Export/Import Issues**: Verify that the backup channel exists and that you have the correct permissions to send messages there.

## Contributing

Feel free to open issues or submit pull requests if you have suggestions for improvements or bug fixes.

## Development Process

I've created a brief [Google Slides presentation](https://docs.google.com/presentation/d/1XILFKQcqIjoWt-Wn_A2jL20M7BzjStOAW8Q_cokHhB4/edit?usp=sharing) for anyone who is interested!

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
