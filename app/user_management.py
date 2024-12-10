from werkzeug.security import generate_password_hash, check_password_hash
from db_setup import get_db_connection
from self_utils import generate_token
import pymysql
import logging
import os
from faker import Faker
import uuid
from dotenv import load_dotenv

fake = Faker()
load_dotenv()
DEFAULT_PICTURE_PATH = os.path.join(os.path.dirname(__file__), 'static', 'images', 'default_profile_picture.jpg')

def generate_fake_user():
    """Generate a fake user with random data."""
    username = fake.user_name()
    email = fake.email()
    first_name = fake.first_name()
    last_name = fake.last_name()
    password = fake.password()
    print(f"Generated fake user: {username}, {email}, {first_name}, {last_name}")
    return {
        "username": username,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "password": password
    }

def register_user(data):
    print("Function called with data: ", data)
    try:
        # Load default profile picture
        with open(DEFAULT_PICTURE_PATH, 'rb') as f:
            default_picture = f.read()
        if data.get("wallet_connect", False):
            print("WalletConnect is being used.")
            wallet_id = data.get("wallet_address")
            if not wallet_id:
                return {"message": "Wallet address is required for WalletConnect."}, 400
            # Check if wallet already exists
            if check_wallet_exists(wallet_id):
                return {"message": "This wallet is already linked to an account."}, 400
            # Handle case where no user data is provided with wallet connect
            username = data.get("username", None) or f"TNC_{uuid.uuid4().hex[:8]}"
            email = data.get("email", None) or f"{username}@example.com"
            password_hash = generate_password_hash(uuid.uuid4().hex[:12])  # Random password hash
            tnc_wallet_id = str(uuid.uuid4())  # Generate unique tnc_wallet_id

            # Ensure first_name and last_name are generated or provided
            first_name = data.get("first_name", fake.first_name()) if data.get("first_name") else fake.first_name()
            last_name = data.get("last_name", fake.last_name()) if data.get("last_name") else fake.last_name()
            print(f"Generated or used provided first_name: {first_name}, last_name: {last_name}")
        else:
            # Regular registration (without WalletConnect)
            required_fields = ["first_name", "last_name", "username", "email", "password"]
            if not all(data.get(field) for field in required_fields):
                print("Missing required fields")
                return {"message": "Missing required fields."}, 400
            first_name = data["first_name"]
            last_name = data["last_name"]
            username = data["username"]
            email = data["email"]
            password_hash = generate_password_hash(data["password"])

            tnc_wallet_id = str(uuid.uuid4())  # Generate a unique tnc_wallet_id

        # Insert data into the database using stored procedure
        print(f"Inserting user data into the database: {first_name}, {last_name}, {username}, {email}")
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.callproc('RegisterUser', (
                    first_name,
                    last_name,
                    username,
                    email,
                    password_hash,
                    default_picture,
                    wallet_id if data.get("wallet_connect", False) else None,  # If WalletConnect is used, provide wallet_id
                    tnc_wallet_id  # Always provide a tnc_wallet_id
                ))
                connection.commit()

        print(f"User {username} registered successfully.")
        return {"message": f"User {username} registered successfully."}, 201

    except pymysql.MySQLError as e:
        error_message = str(e)
        logging.error(f"MySQL Error: {error_message}")
        print(f"MySQL Error: {error_message}")

        if e.args[0] == 1062:  # Duplicate entry error code
            if "username" in error_message:
                return {"message": "Username is already taken."}, 1062
            elif "email" in error_message:
                return {"message": "Email is already registered."}, 1062
            else:
                return {"message": "Duplicate entry error."}, 1062

        return {"message": "Database error occurred."}, 500
    except Exception as e:
        logging.error(f"Unexpected Error: {e}")
        print(f"Unexpected Error: {e}")
        return {"message": "An unexpected error occurred."}, 500

def check_wallet_exists(wallet_id):
    """Check if a wallet is already linked to an account."""
    try:
        print(f"Checking if wallet {wallet_id} already exists...")
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE wallet_id = %s", (wallet_id,))
                result = cursor.fetchone()
                print(result)
                
                # Ensure that we safely retrieve the count value
                count = result.get("count", 0) if result else 0
                print(f"Wallet check result: {count}")
                return count > 0
    except Exception as e:
        logging.error(f"Error checking wallet existence: {e}")
        print(f"Error checking wallet existence: {e}")
        return False

    
def check_wallet_link(wallet_address):
    """Check if the wallet is linked to any user account."""
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Check if the wallet address matches the 'wallet_id' in the 'users' table
                cursor.execute("SELECT id, username, wallet_id FROM users WHERE wallet_id = %s", (wallet_address,))
                user = cursor.fetchone()
                if user:
                    # Return relevant user details if the wallet address is found
                    return {
                        "user_id": user['id'],
                        "username": user['username'],
                        "is_superuser": False  # By default, users are not superusers
                    }
                else:
                    # If no user is linked with the given wallet address
                    return None
    except Exception as e:
        logging.error(f"Error checking wallet link: {e}")
        return None

def check_credentials(identifier, password):
    """Check if the provided credentials (username/email and password) are valid."""
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:  # Use dictionary cursor for easier access
                # Call the stored procedure with the input identifier
                cursor.callproc('check_credentials', [identifier])
                
                # Fetch the result of the SELECT statement inside the procedure
                result = cursor.fetchone()  # Fetch the single result row
                print(result)  # Debugging output to verify the result
                
                if result and result['user_id'] is not None:  # Check if a user was found
                    # Validate the password
                    if check_password_hash(result['password_hash'], password):
                        return {
                            "user_id": result['user_id'],
                            "username": result['username'],
                            "email": result['email'],
                            "user_type": result['user_type'],
                            "is_superuser": bool(result['is_superuser'])
                        }
                        
                return None  # Return None if credentials are invalid
    except Exception as e:
        logging.error(f"Error checking credentials: {e}")
        return None


def login_user(wallet_connect=False, **kwargs):
    """Handle login logic for both WalletConnect and normal login."""
    if wallet_connect:
        wallet_address = kwargs.get('wallet_address')
        chain_id = kwargs.get('chain_id')
        network_id = kwargs.get('network_id')
        if not (wallet_address and chain_id and network_id):
            return {"message": "Wallet address, chain ID, and network ID are required."}, 400

        user = check_wallet_link(wallet_address)
        if not user:
            return {"message": "Wallet is not linked to any user account."}, 401

        user_id = user['user_id']
        is_superuser = user.get('is_superuser', False)
    else:
        identifier = kwargs.get('identifier')
        password = kwargs.get('password')
        if not (identifier and password):
            return {"message": "Username/Email and password are required."}, 400

        credentials_result = check_credentials(identifier, password)
        if not credentials_result:
            return {"message": "Invalid credentials."}, 401

        user_id = credentials_result['user_id']
        is_superuser = credentials_result['is_superuser']

    token = generate_token(user_id, is_superuser)

    return {
        "message": "Login successful!",
        "token": token,
        "user_id": user_id,
        "is_superuser": is_superuser,
    }, 200

def update_wallet_id(user_id, wallet_id):
    """Update wallet ID based on user ID after checking if the wallet already exists."""
    try:
        # If the wallet does not exist, proceed with updating the wallet ID
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE users SET wallet_id = %s WHERE id = %s", (wallet_id, user_id))
                connection.commit()

    except Exception as e:
        logging.error(f"Error updating wallet ID: {e}")
        return {"message": "Error updating wallet ID."}, 500
