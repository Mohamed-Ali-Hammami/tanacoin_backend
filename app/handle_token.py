from db_setup import get_db_connection
import datetime
import uuid
from pymysql import MySQLError


# Function to call the 'ManageTanacoinSupply' procedure
def manage_tanacoin_supply(action, amount):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Calling the procedure with parameters 'action' and 'amount'
            cursor.callproc('ManageTanacoinSupply', (action, amount))
            
            # Fetch and print the updated balance after the operation
            cursor.execute('SELECT @total_balance')
            result = cursor.fetchone()
            print(f"Updated Balance: {result[0]}")
            connection.commit()
    except MySQLError as e:
        print(f"Error occurred: {e}")
    finally:
        connection.close()

def get_tanacoin_main_balance():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.callproc('GetTanacoinBalance')
            result = cursor.fetchone()
            if result and 'total_balance' in result:
                return result['total_balance']  # Assuming the key is 'total_balance'
            else:
                print("Procedure returned unexpected result:", result)
                return 0
    except MySQLError as e:
        print(f"Error occurred: {e}")
        return 0
    finally:
        connection.close()

def transfer_tanacoin(sender_id, recipient_tnc_wallet_id, amount):
    print(f"Initiating transfer: Sender ID = {sender_id}, recipient_tnc_wallet_id = {recipient_tnc_wallet_id}, Amount = {amount}")  # Print the function's inputs
    connection = get_db_connection()
    
    try:
        print("Connecting to the database...")  # Indicating the database connection attempt
        with connection.cursor() as cursor:
            print(f"Calling stored procedure 'transfer_tanacoin' with sender_id={sender_id}, recipient_tnc_wallet_id={recipient_tnc_wallet_id}, amount={amount}")  # Print the stored procedure parameters
            cursor.callproc('transfer_tanacoin', (sender_id, recipient_tnc_wallet_id, amount))
            result = cursor.fetchone()
            connection.commit()
            print(f"Transaction successful. Transaction hash: {result}")  # Print the transaction hash returned by the procedure
            return {"message": "Transaction completed successfully.", "transaction_hash": result[0]}, 200

    except MySQLError as e:
        print(f"MySQL error occurred: {e}")  # Print MySQL-specific error message
        connection.rollback()
        return {"message": f"MySQL error occurred: {e}."}, 500

    finally:
        print("Closing database connection...")  # Indicating database connection closure
        connection.close()


def call_purchase_tanacoin(user_id, payment_amount, crypto_type, exchange_rate, crypto_precision, transaction_hash):
    try:
        # Connect to the database
        connection =get_db_connection()
        
        with connection.cursor() as cursor:
            # Call the stored procedure
            cursor.callproc('purchase_tanacoin', [
                user_id,
                payment_amount,
                crypto_type,
                exchange_rate,
                crypto_precision,
                transaction_hash
            ])
            
            # Fetch the result (output from SELECT in the procedure)
            result = cursor.fetchall()
            
            # Commit the transaction
            connection.commit()
        
        # Return the success message
        return {"status": "success", "message": result[0]['message'] if result else "No message returned."}

    except MySQLError as e:
        # Handle MySQL errors
        return {"status": "error", "message": f"MySQL error occurred: {str(e)}"}
    except Exception as e:
        # Handle other errors
        return {"status": "error", "message": f"Unexpected error occurred: {str(e)}"}
    finally:
        # Ensure the connection is closed
        if connection:
            connection.close()
     