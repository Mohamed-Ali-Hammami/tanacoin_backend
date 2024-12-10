import random
import string
import re 
from dotenv import load_dotenv
import os
import hashlib
from faker import Faker
from datetime import datetime, timedelta
import jwt


load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_nonce')
fake = Faker()

def create_new_password(length=8) -> str:
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def hash_password(password):
    salted_password = password + SECRET_KEY
    hashed_password = hashlib.sha256(salted_password.encode()).hexdigest()
    return hashed_password

def check_password(entered_password, stored_hash):
    entered_hash = hash_password(entered_password)

    return entered_hash == stored_hash

def generate_token(user_id, is_superuser):
    """Generate a JWT token for a user."""
    payload = {
        'user_id': user_id,
        'is_superuser': is_superuser,
        'exp': datetime.utcnow() + timedelta(hours=1)  # Consider using a shorter expiry
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
