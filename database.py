import os
import pymongo
import datetime
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DBNAME = os.getenv("MONGO_DBNAME")

if not MONGO_URI or not MONGO_DBNAME:
    raise RuntimeError("Missing MongoDB configuration")

connection = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS = 5000)
db = connection[MONGO_DBNAME]