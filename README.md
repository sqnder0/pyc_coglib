# PyC CogLib

A comprehensive, modular Discord bot framework built with discord.py, featuring hot-swappable cogs, persistent settings, and an optional web management panel.

## 🚀 Features

### Core Framework

- **Modular Cog System**: Hot-swappable cogs that can be loaded/unloaded without restarting
- **Persistent Settings**: JSON-based configuration with dot-notation access and automatic namespacing
- **Database Integration**: SQLite wrapper for persistent data storage
- **Comprehensive Logging**: Structured logging with file rotation and console output
- **Graceful Shutdown**: Proper cleanup of resources and database connections

### Optional Web Panel

- **Browser-Based Management**: Control your bot from anywhere with a web interface
- **Real-Time Monitoring**: View bot status, latency, and cog information
- **Remote Control**: Start/stop bots, toggle cogs, and view logs
- **Secure Authentication**: Password-protected access with session management
- **Cross-Platform**: Supports Windows, macOS, and Linux terminal launching

### Built-in Cogs

#### 🎛️ Customization Cog

Manage your bot's appearance and presence:

- **Status Management**: Set online/idle/dnd/invisible status
- **Activity Types**: Playing, listening, watching, streaming, competing
- **Custom Messages**: Personalized activity messages
- **Embed Colors**: Configure default embed colors with validation
- **Persistent Settings**: All changes saved and restored on restart

#### 🎫 Ticket System Cog

Professional support ticket system:

- **Interactive Buttons**: Users click to create tickets
- **Auto-Channel Creation**: Generates private channels with proper permissions
- **Staff Management**: Claim and close tickets with role-based access
- **Configurable Categories**: Set where tickets are created
- **User Notifications**: DM users when tickets are closed
- **Persistent Views**: Buttons work even after bot restarts

#### 🛡️ Moderation Cog

Comprehensive moderation tools:

- **Warning System**: Automatic timeouts based on warning thresholds
- **Message Filtering**: Excessive ping and caps detection
- **Audit Log Integration**: Tracks bans, kicks, and timeouts automatically
- **Interactive Configuration**: Easy setup through Discord commands
- **Smart Permissions**: Respects Discord permission hierarchies
- **Detailed Logging**: All actions logged to designated channels

#### 🔧 Development Cog

Development and debugging utilities:

- **Hot Reload**: Reload all cogs without restarting the bot
- **Module Refresh**: Automatically imports updated Python code
- **Error Handling**: Graceful error reporting during reloads
- **Permission Protection**: Requires moderation permissions

#### 🌐 Web Panel Cog

Web interface integration:

- **Flask Blueprint**: Seamless integration with the web panel
- **Bot Status Display**: Real-time bot information on the dashboard
- **Cross-Platform Launcher**: Start bots in new terminal windows
- **API Proxy**: Secure communication between web and bot

## 📦 Installation

### Prerequisites

- Python 3.8+
- Discord.py 2.0+
- A Discord bot token

### Quick Start

1. **Download a Release or Clone the Repository**:

   - **Download a Release**: Visit the [Releases Page](https://github.com/sqnder0/pyc_coglib/releases) to download the latest version. Note: Releases are available without the web panel for a lightweight setup.
   - **Clone the Repository**:
     ```bash
     git clone https://github.com/sqnder0/pyc_coglib.git
     cd pyc_coglib
     ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   Create a `.env` file in the project root:

   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

4. **Run the bot**:
   ```bash
   python bot.py
   ```

### Web Panel Setup (Optional)

The web panel is automatically enabled if the `webpanels/` directory exists:

1. **Auto-Configuration**: The system automatically generates secure passwords and secret keys
2. **Access**: Open `http://localhost:5566` in your browser
3. **Login**: Use the auto-generated password from your `.env` file (`WEBPANEL_PASSWORD`)

## 🏗️ Architecture

### Project Structure

```
pyc_coglib/
├── bot.py              # Main bot entry point
├── api.py              # FastAPI backend for web panel
├── settings.py         # Configuration management system
├── database.py         # SQLite database wrapper
├── cogs/               # Modular bot functionality
│   ├── customization.py    # Bot appearance and presence
│   ├── tickets.py          # Support ticket system
│   ├── moderation.py       # Moderation tools and filters
│   ├── development.py      # Developer utilities
│   └── webpanel.py         # Web interface integration
├── webpanels/          # Optional web interface
│   ├── app.py              # Flask application
│   ├── templates/          # HTML templates
│   └── static/             # CSS, JS, and assets
└── logs/               # Log files (auto-created)
```

### Core Components

#### Settings System (`settings.py`)

- **Dot Notation**: Access nested settings like `"module.feature.setting"`
- **Auto-Namespacing**: Cogs automatically get their own setting namespace
- **Type Safety**: Default values with type checking
- **Auto-Persistence**: All changes automatically saved to JSON

#### Database System (`database.py`)

- **Singleton Pattern**: Single database instance across the application
- **Auto-Creation**: Database file created if it doesn't exist
- **Safe Operations**: Proper connection management and cleanup
- **Error Handling**: Comprehensive error logging

#### Cog System

- **Hot-Swappable**: Load/unload cogs without restarting
- **Auto-Discovery**: Automatically loads all `.py` files in `cogs/`
- **Persistent Views**: Discord UI components survive bot restarts
- **Error Isolation**: Cog errors don't crash the entire bot

## 🎮 Usage

### Basic Commands

#### Built-in Commands

- `/ping` - Check bot latency
- `/set_presence` - Configure bot status and activity (Admin only)
- `/set_embed_color` - Set default embed color (Admin only)
- `/reload` - Hot reload all cogs (Moderator only)

#### Ticket System

- `/ticket` - Create ticket creation embed with buttons (Admin only)
- `/ticketconfig` - Configure ticket system settings (Admin only)

#### Moderation System

- `/modmenu` - Interactive moderation configuration panel (Admin only)
- Automatic filtering for excessive pings and caps
- Automatic timeout tracking and logging

### Configuration Examples

#### Setting Bot Presence

```
/set_presence status:online activity:playing message:with Discord.py!
```

#### Configuring Ticket System

1. Run `/ticketconfig choice:set category`
2. Right-click a category → "Copy Category ID"
3. Paste the ID in chat

#### Setting Up Moderation

1. Run `/modmenu`
2. Use the interactive buttons to configure settings
3. Set mod log channel, warning thresholds, and filters

## 🔧 Development

### Creating Custom Cogs

Create a new file in the `cogs/` directory:

```python
from discord.ext import commands
from discord import app_commands
import discord

class YourCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="example", description="An example command")
    async def example_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello from your custom cog!")

async def setup(bot):
    await bot.add_cog(YourCog(bot))
```

### Using Settings in Cogs

```python
from settings import get_settings, get_path

SETTINGS = get_settings()

# Automatically namespaced to your cog
value = SETTINGS.get_or_create(get_path("my_setting"), "default_value")
SETTINGS.put(get_path("my_setting"), "new_value")
```

### Database Operations

```python
from database import get_database

DATABASE = get_database()

# Execute SQL
result = DATABASE.execute("SELECT * FROM users WHERE id = ?", user_id)

# Don't forget to commit changes
DATABASE.commit()
```

## 🌐 Web Panel Features

### Dashboard

- Real-time bot status monitoring
- Cog management (enable/disable)
- Quick access to bot information

### Remote Control

- Start bot in new terminal windows
- View recent log entries
- Graceful shutdown capabilities

### Security

- Password-protected access
- Auto-generated secure credentials
- Session-based authentication
- Request validation and sanitization

## 📝 Configuration

### Environment Variables

- `DISCORD_TOKEN` - Your Discord bot token (required)
- `WEBPANEL_PASSWORD` - Web panel password (auto-generated)
- `FLASK_SECRET_KEY` - Flask session secret (auto-generated)

### Settings File (`settings.json`)

The settings file is automatically created and managed. Example structure:

```json
{
  "embed": {
    "color": "#5865F2"
  },
  "customization": {
    "presence": {
      "activity": "playing",
      "status": "online",
      "message": "with Discord.py!"
    }
  },
  "moderation": {
    "warn_threshold": 5,
    "max_ping_count": 2,
    "max_caps_percent": 30
  }
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [discord.py](https://github.com/Rapptz/discord.py) - The Discord API wrapper
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [Flask](https://flask.palletsprojects.com/) - Lightweight web framework
- [Bootstrap](https://getbootstrap.com/) - Frontend component library

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/sqnder0/pyc_coglib/issues)
- **Documentation**: This README and inline code documentation

---

Made with ❤️ by [sqnder0](https://github.com/sqnder0)
