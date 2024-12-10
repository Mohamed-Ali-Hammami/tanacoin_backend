from flask import Blueprint, session, redirect, url_for, flash, request, render_template, jsonify
from functools import wraps
from datetime import datetime, timedelta
import jwt
import os
from db_setup import get_db_connection
from handle_token import transfer_tanacoin ,purchase_tanacoin
import logging

# Blueprint definition
superuser_dashboard_bp = Blueprint('superuser_dashboard', __name__)
SECRET_KEY = os.getenv('SECRET_KEY')

def generate_token(user_id, is_superuser):
    payload = {
        'user_id': user_id,
        'is_superuser': is_superuser,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
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

            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM superusers WHERE user_id = %s', (current_user['user_id'],))
                user = cursor.fetchone()

            if not user:
                return jsonify({"message": "User not found"}), 404

            current_user.update(user)
            connection.close()

        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401
        except Exception as e:
            logging.error(f"Token validation error: {e}")
            return jsonify({"message": "Internal server error"}), 500

        return f(current_user, *args, **kwargs)
    return decorated

@superuser_dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@token_required
def dashboard(current_user):
    user_id = current_user['user_id']

    try:
        # Fetch wallet and transaction details from the database
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM wallets WHERE user_id = %s', (user_id,))
            wallet = cursor.fetchone()

            if not wallet:
                flash("Wallet not found.", "danger")
                return redirect(url_for('home'))

            # Handle actions for purchase and transfer
            if request.method == 'POST':
                action = request.form.get('action')
                amount = float(request.form.get('amount', 0))
                recipient_id = request.form.get('recipient_id')

                if action == 'purchase':
                    # Handle the purchase action
                    transaction = purchase_tanacoin(user_id, amount)
                    if transaction:
                        flash('Tokens purchased successfully!', 'success')
                        return jsonify({'success': True})  
                    else:
                        flash('Error purchasing tokens.', 'danger')
                        return jsonify({'success': False})  

                elif action == 'transfer' and recipient_id:
                    recipient_id = int(recipient_id)
                    if recipient_id != user_id and amount > 0:
                        transaction = transfer_tanacoin(user_id, recipient_id, amount)
                        if transaction:
                            flash('Tokens transferred successfully!', 'success')
                            return jsonify({'success': True})  
                        else:
                            flash('Error transferring tokens.', 'danger')
                            return jsonify({'success': False})  
                    else:
                        flash('Invalid recipient or amount.', 'danger')
                        return jsonify({'success': False})  

            # Retrieve transaction history
            cursor.execute("""SELECT * FROM transactions WHERE sender_id = %s OR recipient_id = %s ORDER BY transaction_date DESC LIMIT 10""", (user_id, user_id))
            transactions = cursor.fetchall()

            # Retrieve leaderboard (Top 5 users by balance)
            cursor.execute("""SELECT u.username, w.balance FROM users u JOIN wallets w ON u.user_id = w.user_id ORDER BY w.balance DESC LIMIT 5""")
            leaderboard = cursor.fetchall()

            # User statistics (total tokens purchased and transferred)
            cursor.execute("""SELECT SUM(amount) FROM transactions WHERE sender_id = %s AND transaction_type = 'buy'""", (user_id,))
            total_purchased = cursor.fetchone()[0] or 0

            cursor.execute("""SELECT SUM(amount) FROM transactions WHERE sender_id = %s AND transaction_type = 'transfer'""", (user_id,))
            total_transferred = cursor.fetchone()[0] or 0

            wallet_value_eur = float(wallet['balance']) * 0.09

            connection.close()

            # Render superuser dashboard
            return render_template('superuser_dashboard.html', 
                                   wallet=wallet, 
                                   transactions=transactions, 
                                   leaderboard=leaderboard, 
                                   total_purchased=total_purchased, 
                                   total_transferred=total_transferred, 
                                   wallet_value_eur=wallet_value_eur)

    except Exception as e:
        logging.error(f"Database error: {e}")
        flash('A database error occurred. Please try again later.', 'danger')
        return redirect(url_for('home'))
def get_all_users_data():
    """Retrieve all user data for the superuser."""
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, first_name, last_name, username, email, profile_picture, wallet_id, tnc_wallet_id, created_at
                    FROM users
                """)
                users_data = cursor.fetchall()

                if users_data:
                    return users_data
                else:
                    return None
    except Exception as e:
        logging.error(f"Error retrieving all users data: {e}")
        return None
