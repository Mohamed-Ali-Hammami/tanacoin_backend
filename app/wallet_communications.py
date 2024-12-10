from db_setup import get_db_connection


def store_transaction_in_db(user_id, payment_amount, crypto_type, tx_hash, crypto_precision=8, status='pending'):
    try:
        # Assuming a MySQL database connection
        connection = get_db_connection()  # Replace with your actual DB connection logic
        cursor = connection.cursor()

        # Insert the transaction into the crypto_payments table
        cursor.execute('''
            INSERT INTO crypto_payments (user_id, payment_amount, crypto_type, crypto_precision, transaction_hash, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (user_id, payment_amount, crypto_type, crypto_precision, tx_hash, status))

        # Commit the transaction
        connection.commit()

        cursor.close()
        connection.close()

        return True, "Transaction stored successfully"
    except Exception as e:
        return False, str(e)