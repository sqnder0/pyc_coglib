"""
PyC CogLib Web Panel Flask Application

Flask web application providing a browser-based interface for Discord bot management.
Features secure authentication, bot monitoring, and API proxy functionality.

Features:
- Password-protected access with session management
- Automatic password and secret key generation
- Bot heartbeat monitoring
- API proxy for secure bot communication
- Cross-platform compatibility
- Template auto-reload for development

Security:
- Session-based authentication with Flask-Login
- Auto-generated secure passwords and secret keys
- Constant-time password comparison
- Protected API endpoints

Author: sqnder0
Repository: pyc_coglib
License: See LICENSE file
"""

from flask import Flask, render_template, request, session, redirect, jsonify, url_for
from flask_login import login_user, UserMixin, LoginManager, login_required
from typing import Callable, TypeVar
from dotenv import load_dotenv
from secrets import token_urlsafe, compare_digest
import sys
import os
import logging
import requests

# Load the project directory
project_folder = os.path.dirname(os.path.dirname(__file__))
sys.path.append(project_folder)

from bot import HOST, PORT

logger = logging.getLogger("main")

# Initialize a flask app
app = Flask(__name__)

# Get the directory from the file, and go up 1 directory
dotenv_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(dotenv_dir, ".env")

# Initialize login manager
login_manager = LoginManager()

login_manager.login_view = "login" #type: ignore

login_manager.init_app(app)


# Load the environment
load_dotenv(dotenv_path=dotenv_path)

# Get the password for the webpanel
password_key = "WEBPANEL_PASSWORD"
webpanel_password = os.environ.get(password_key)

#Generate a flask secret key
secret_key_key = "FLASK_SECRET_KEY"
secret_key = os.environ.get(secret_key_key)

# Define the root user
# Please note there is only ONE user
class RootUser(UserMixin):
    """
    Single root user for web panel authentication.
    
    This application uses a simple single-user authentication model
    where there is only one user account ('root') for accessing
    the web panel interface.
    """
    
    def __init__(self):
        """Initialize the root user with ID 'root'."""
        self.id = "root"

root_user = RootUser()

generation_count = 0
while not webpanel_password and generation_count < 5:
    try:
        password_str = token_urlsafe(24)
        
        with open(dotenv_path, "a") as file:
            file.write(f"\n{password_key}={password_str}")
        
        # Reload the environment
        load_dotenv(dotenv_path=dotenv_path)
        
        webpanel_password = os.environ.get(password_key)
    except Exception as e:
        print(e)
        
    generation_count += 1
        
if not webpanel_password:
    print(f"Couldn't generate a new password, tried {generation_count} time(s)")
    exit()
    

generation_count = 0
while not secret_key and generation_count < 5:
    try:
        secret_key_str = token_urlsafe(24)
        
        with open(dotenv_path, "a") as file:
            file.write(f"\n{secret_key_key}={secret_key_str}")
        
        # Reload the environment
        load_dotenv(dotenv_path=dotenv_path)
        
        secret_key = os.environ.get(secret_key_key)
    except Exception as e:
        print(e)
        
    generation_count += 1
        
if not secret_key:
    print(f"Couldn't generate a new secret key, tried {generation_count} time(s)")
    exit()
    
app.secret_key = secret_key

# Load the webpanel routes if the webpanel cog is present
if os.path.exists(os.path.join(project_folder, "cogs/webpanel.py")):
    # Import the webpanel blueprint after the bot is loaded
    try:
        from cogs.webpanel import webpanel
        app.register_blueprint(webpanel)
        logger.info("Webpanel routes registered")
    except ImportError as e:
        logger.warning(f"Could not import webpanel routes: {e}")
        logger.info("Webpanel routes will be registered when bot loads the cog")
    

F = TypeVar("F", bound=Callable)
logger = logging.getLogger("main")

@app.route("/heartbeat", methods=["GET"])
def heartbeat():
    """
    Check if the Discord bot API is alive and responsive.
    
    Returns:
        dict: JSON response indicating bot status
        
    This endpoint proxies a heartbeat request to the bot's API
    to determine if the bot is running and responsive. Used
    for status monitoring in the web interface.
    """
    try:
        response = requests.get(f"http://{HOST}:{PORT}/heartbeat")
        
        if response.status_code == 200:
            return jsonify({"alive": True})
        
        else:
            return jsonify({"alive": False, "code": response.status_code, "error": response.reason})
    except requests.RequestException as e:
        return jsonify({"alive": False})
    except Exception as e:
        return jsonify({"alive": False, "error": str(e)})

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handle user authentication for the web panel.
    
    Returns:
        str: Login form for GET requests, redirect or error for POST
        
    GET: Displays the login form
    POST: Processes login credentials and creates user session
    
    Uses constant-time comparison for password security and supports
    the "remember me" functionality for persistent sessions.
    """
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        data = request.form.to_dict()
        password = data.get("password")
        
        remember = True if data.get("remember") else False
        
        if compare_digest(str(password), str(webpanel_password)):
            login_user(user=root_user, remember=remember)
            return redirect("/")
        else:
            return render_template("login.html", error="Password incorrect")
    
    return "Invalid method"

@app.route("/api", methods=["POST"])
@login_required
def api():
    """
    Proxy API requests to the Discord bot's internal API.
    
    Returns:
        tuple: JSON response and HTTP status code
        
    This endpoint acts as a secure proxy between the web interface
    and the bot's internal API, handling authentication and error
    cases while forwarding requests and responses.
    
    Expected JSON payload:
    - internal_api_url: The bot API endpoint to call
    - params: Optional query parameters for the request
    """
    data = request.get_json()

    internal_api_url = data.get("internal_api_url")
    params = data.get("params")

    if not internal_api_url:
        return jsonify({"error": "Bad request", "description": "Please provide internal_api_url"}), 400

    # Forward the request
    try:
        if params:
            response = requests.get(f"http://{HOST}:{PORT}{internal_api_url}", params=params)
        else:
            response = requests.get(f"http://{HOST}:{PORT}{internal_api_url}")
    except:
        return jsonify({"error": "Bot offline: request timed out"}), 400

    # Try to parse as JSON, fallback to plain text
    try:
        response_data = response.json()
    except ValueError:
        return jsonify({
            "error": "Invalid JSON response from bot",
            "status": response.status_code,
            "body": response.text[:500]
        }), response.status_code

    return jsonify(response_data), response.status_code

@login_manager.user_loader
def load_user(user_id):
    """
    Load user for Flask-Login session management.
    
    Args:
        user_id (str): The user ID to load
        
    Returns:
        RootUser or None: The user object if valid, None otherwise
    """
    if user_id == "root":
        return root_user
    return None

@login_manager.unauthorized_handler
def unauthorized():
    """
    Handle unauthorized access attempts.
    
    Returns:
        Response: JSON error for API requests, redirect for web requests
        
    Provides appropriate responses based on request type:
    - API requests get JSON error responses
    - Web requests are redirected to the login page
    """
    if request.path.startswith("/api"):
        return jsonify({"error": "Unauthorized"}), 401
    
    return redirect(url_for("login"))
    
if __name__ == '__main__':
    # When run as a separate process, use the run_flask function
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True)