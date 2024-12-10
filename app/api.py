from flask import request, jsonify, session
from functools import wraps
import os
import requests
from db_config import get_user_data
from user_management import register_user, login_user,update_wallet_id
from dotenv import load_dotenv
import jwt
from db_setup import create_app
from handle_token import transfer_tanacoin, call_purchase_tanacoin,get_tanacoin_main_balance
from _superuser_dashboard import superuser_dashboard_bp

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
RECEIVER_ADDRESS = os.getenv("RECEIVER_ADDRESS")
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
app = create_app()

# Function to validate the JWT token
def token_required(f):
    @wraps(f)
    def decorated():
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({"message": "Token is missing"}), 401
        try:
            token = token.split(" ")[1] if " " in token else token
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = {
                "user_id": payload.get('user_id'),
                "is_superuser": payload.get('is_superuser', False)
            }
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 403
        return f(current_user)
    return decorated
@app.route('/dashboard', methods=['GET', 'POST'])
@token_required
def dashboard(current_user):
    user_id = current_user['user_id']  # Get user ID from the decoded token
    user_details = get_user_data(user_id)

    if not user_details or not user_details['user_data']:
        return jsonify({"error": "User data could not be retrieved."}), 404

    if request.method == 'POST':
        action = request.json.get('action')  # Get action from JSON body

        if action == 'add_wallet':
            try:
                wallet_address = request.json.get('wallet_address')  # Extract wallet address
                if not wallet_address:
                    return jsonify({'error': 'Wallet address is required.'}), 400  # Validation check

                # Update wallet in the database
                result = update_wallet_id(user_id, wallet_address)
            except Exception as e:
                return jsonify({'error': f'An error occurred while adding wallet: {str(e)}'}), 500


        elif action == 'transfer':
            try:
                recipient_tnc_wallet_id = request.json.get('recipient_tnc_wallet_id')
                amount = float(request.json.get('amount'))
                result = transfer_tanacoin(user_id, recipient_tnc_wallet_id, amount)
                return jsonify({'message': result['message']}), result[1]
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid input for transfer.'}), 400
            except Exception as e:
                return jsonify({'error': f'An error occurred during the transfer: {str(e)}'}), 500
        
        elif action == 'purchase':
            try:
                payment_amount = float(request.json.get('payment_amount'))
                crypto_type = request.json.get('crypto_type')
                exchange_rate = 0.09
                crypto_precision = int(18)
                transaction_hash = request.json.get('transaction_hash')
                result = call_purchase_tanacoin(user_id,payment_amount,crypto_type,exchange_rate,crypto_precision,transaction_hash)
                return jsonify({'message': result['message']}), result[1]
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid input for purchase.'}), 400
            except Exception as e:
                return jsonify({'error': f'An error occurred during the purchase: {str(e)}'}), 500

    return jsonify({
        "user_data": user_details['user_data'],
        "wallet_data": user_details['wallet_data'] if user_details['wallet_data'] else [],
        "transactions": user_details['transactions'] if user_details['transactions'] else [],
        "payments": user_details['payments'] if user_details['payments'] else []
    })


@app.route('/dashboard/data', methods=['GET'])
@token_required
def dashboard_data(current_user):
    user_id = current_user['user_id']  # Get user ID from the decoded token
    user_details = get_user_data(user_id)
    
    if not user_details or not user_details['user_data']:
        return jsonify({'error': 'User data not found'}), 404

    # Return the data with a proper structure
    return jsonify({
        "user_data": user_details['user_data'],
        "wallet_data": user_details['wallet_data'] if user_details['wallet_data'] else [],
        "transactions": user_details['transactions'] if user_details['transactions'] else [],
        "payments": user_details['payments'] if user_details['payments'] else []
    })

@app.route('/get_tanacoin_price', methods=['GET'])
def get_tanacoin_price():
    """Fetch Tanacoin price based on the payment method."""
    payment_method = request.args.get('payment_method')

    if payment_method not in ['ETH', 'USDT']:
        return jsonify({'success': False, 'message': 'Invalid payment method'}), 400

    if payment_method == 'ETH':
        coin_price = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd').json()
        tanacoin_price = coin_price['ethereum']['usd']
    elif payment_method == 'USDT':
        coin_price = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd').json()
        tanacoin_price = coin_price['tether']['usd']

    return jsonify({'success': True, 'price': tanacoin_price})

@app.route('/purchase_tanacoin', methods=['POST'])
def purchase_tanacoin():
    data = request.get_json()
    amount = data.get('amount')
    payment_method = data.get('payment_method')
    payment_amount = data.get('payment_amount')

    if not amount or not payment_method or not payment_amount:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    # Process payment and handle logic
    user_balance = 100  # Simulated user balance

    new_balance = user_balance - payment_amount
    if new_balance < 0:
        return jsonify({'success': False, 'message': 'Insufficient balance'}), 400

    return jsonify({'success': True, 'new_balance': new_balance})

@app.route('/signup', methods=['POST'])
def signup():
    """Handle user signup."""
    form_data = request.get_json()
    response = register_user(form_data)

    if response[1] == 1062:
        return jsonify({'message': response[0]['message']}), 400
    elif response[1] == 201:
        return jsonify({'message': f"User {form_data['username']} registered successfully."}), 201
    else:
        return jsonify({'message': 'An error occurred during registration.'}), 400

@app.route('/login', methods=['POST'])
def login():
    """Handle user login."""
    data = request.json
    identifier = data.get('identifier')
    password = data.get('password')
    # Validate user credentials (username/password login)
    result, status_code = login_user(wallet_connect=False, identifier=identifier, password=password)
    
    if status_code == 200:
        user_id = result.get('user_id')
        # Storing some user data in session (if needed)
        session['user_id'] = user_id
        session['username'] = result.get('username')
        session['is_superuser'] = result.get('is_superuser')

        return jsonify({
            'message': 'Login successful!',
            'user': {
                'user_id': user_id,
                'username': result.get('username'),
                'is_superuser': result.get('is_superuser')
            },
            'token': result.get('token')
        }), status_code
    else:
        return jsonify({'message': 'Authentication failed'}), status_code
    
@app.route('/connect_wallet', methods=['POST'])
def connect_wallet():
    data = request.json
    # Check if wallet address is provided
    wallet_address = data.get('wallet_address')
    if not wallet_address:
        return jsonify({"message": "Wallet address is required."}), 400
    wallet_address = data.get('wallet_address')
    chain_id = data.get('chain_id')
    network_id = data.get('network_id')
    # Attempt to log in the user using the wallet address
    login_response = login_user(wallet_connect=True, wallet_address=wallet_address, chain_id=chain_id, network_id=network_id)
    if login_response[1] == 200:  # If login is successful
        return jsonify(login_response[0]), 200
    # If login fails, we assume the user is not registered and attempt to register
    data['wallet_connect'] = True
    registration_response = register_user(data)
    # Return the registration response
    return jsonify(registration_response[0]), registration_response[1]

@app.route("/logout")
def logout():
    """Log out the user and clear the session."""
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route("/about_us")
def about():
    """Provide info about the site."""
    return jsonify({"message": "About us information goes here"})

@app.route('/token-supply')
def get_token_supply():
    """Return the total token supply."""
    try:
        total_supply = get_tanacoin_main_balance()
        return jsonify({'totalSupply': str(total_supply)})
    except Exception as e:
        print(f"Error occurred while fetching token supply: {e}")
        return jsonify({'error': 'Failed to retrieve token supply'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)


