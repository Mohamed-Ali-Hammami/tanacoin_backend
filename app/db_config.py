from db_setup import get_db_connection
import logging
from werkzeug.security import check_password_hash
import base64
import pymysql
from self_utils import check_password

def check_wallet_link(wallet_address):
    connection = get_db_connection()
    
    try:
        with connection.cursor() as cursor:
            query = '''
            SELECT user_id
            FROM users
            WHERE wallet_id = %s
            '''
            cursor.execute(query, (wallet_address,))
            result = cursor.fetchone()
            if result:
                return {
                    'user_id': result['user_id'],
                }
            return None
    except Exception as e:
        logging.error(f"Error checking wallet link: {e}")
        return None
    finally:
        connection.close()

def get_superuser_details(identifier):
    logging.info(f"Fetching superuser details for identifier: {identifier}")
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            query = '''
            SELECT superuser_id, username, email, password_hash
            FROM superusers 
            WHERE superuser_id = %s OR username = %s OR email = %s
            '''
            cursor.execute(query, (identifier, identifier, identifier))
            superuser = cursor.fetchone()
            if superuser:
                logging.info(f"Superuser found: {superuser}")
            return superuser
    except Exception as e:
        logging.error(f"Error fetching superuser details: {e}")
        return None
    finally:
        connection.close()
import base64

def get_user_data(user_id):
    """Fetch user data from the database."""
    # Establish database connection
    connection = None
    try:
        connection = get_db_connection()
        print(f"[DEBUG] Database connection established for user_id: {user_id}")

        with connection.cursor() as cursor:
            # Call the stored procedure 'get_user_data' with the provided user_id
            cursor.callproc('get_user_data', [user_id])
            user_data = []
            wallet_data = []
            transactions = []
            payments = []
            # Fetch all the results from the stored procedure
            for result in cursor.fetchall():
                # Convert bytes data (profile_picture, transaction_hash) to base64 string
                profile_picture = result['profile_picture']
                if isinstance(profile_picture, bytes):
                    profile_picture = base64.b64encode(profile_picture).decode('utf-8')
                
                transaction_hash = result['transaction_hash']
                if isinstance(transaction_hash, bytes):
                    transaction_hash = base64.b64encode(transaction_hash).decode('utf-8')

                # Collect user data
                user_data.append({
                    'user_id': result['user_id'],
                    'first_name': result['first_name'],
                    'last_name': result['last_name'],
                    'username': result['username'],
                    'email': result['email'],
                    'profile_picture': profile_picture,
                    'tnc_wallet_id': result['user_tnc_wallet_id'],
                    'created_at': result['created_at']
                })

                # Collect wallet data
                wallet_data.append({
                    'wallet_id': result['wallet_id'],
                    'tnc_wallet_unique_id': result['tnc_wallet_unique_id'],
                    'balance': result['balance'],
                    'wallet_created_at': result['wallet_created_at']
                })

                # Collect transaction data
                if result['transaction_id']:
                    transactions.append({
                        'transaction_id': result['transaction_id'],
                        'sender_id': result['sender_id'],
                        'recipient_id': result['recipient_id'],
                        'amount': result['amount'],
                        'transaction_date': result['transaction_date'],
                        'status': result['status'],
                        'transaction_hash': transaction_hash
                    })

                # Collect payment data
                if result['payment_id']:
                    payments.append({
                        'payment_id': result['payment_id'],
                        'payment_amount': result['payment_amount'],
                        'crypto_type': result['crypto_type'],
                        'crypto_precision': result['crypto_precision'],
                        'payment_transaction_hash': result['payment_transaction_hash'],
                        'payment_date': result['payment_date'],
                        'payment_status': result['payment_status']
                    })

            # Return the formatted data in a dictionary
            return {
                'user_data': user_data,
                'wallet_data': wallet_data,
                'transactions': transactions,
                'payments': payments
            }

    except pymysql.MySQLError as e:
        print(f"[ERROR] MySQL error: {e}")
    
    finally:
        if connection:
            connection.close()
            print("[DEBUG] Database connection closed.")
        
    return None


def get_all_users():
    connection = get_db_connection()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            query = '''
            SELECT 
                user_id, 
                first_name, 
                last_name, 
                username, 
                email, 
                created_at, 
                updated_at
            FROM users
            '''
            cursor.execute(query)
            result = cursor.fetchall()
            
            users = []
            for user in result:
                profile_picture_base64 = None
                if user['profile_picture']:
                    profile_picture_base64 = base64.b64encode(user['profile_picture']).decode('utf-8')
                
                user_data = {
                    'user_id': user['user_id'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'username': user['username'],
                    'email': user['email'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                    'updated_at': user['updated_at'].isoformat() if user['updated_at'] else None,
                }
                users.append(user_data)
            
            return users
    except Exception as e:
        logging.error(f"Error fetching all users: {e}")
        return []
    finally:
        connection.close()
