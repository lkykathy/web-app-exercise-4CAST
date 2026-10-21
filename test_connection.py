from database import connection, db

try:
    connection.admin.command("ping")
    print("Successfullly connected to MongoDB")
    print("Database: ", db.name)

except Exception as error:
    print("Connection failed: ", error)