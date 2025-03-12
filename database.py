import mysql.connector
from config import db_config

def setup_db():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Create petitions table with the solution column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS petitions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255),
                phone_number VARCHAR(50),
                address TEXT,
                grievance TEXT,
                category VARCHAR(255),
                priority VARCHAR(50),
                solution TEXT,
                status VARCHAR(50) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                petition_id INT,
                message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (petition_id) REFERENCES petitions(id)
            )
        """)

        # Update users table to include designation
        cursor.execute("""
            DROP TABLE IF EXISTS users
        """)
        
        cursor.execute("""
            CREATE TABLE users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                designation VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("Database setup completed.")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        conn.close()
if __name__ == "__main__":
    setup_db()