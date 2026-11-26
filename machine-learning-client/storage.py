import os
from datetime import datetime, timezone
from functools import lru_cache
from pymongo import MongoClient

@lru_cache(maxsize=1)
def get_client():
    return MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"), timeoutMS=500)

def save_tracking_result(result):
    database = get_client()[os.getenv("MONGO_DB", "fruit_ninja")]
    database["tracking_results"].insert_one({**result, "created_at": datetime.now(timezone.utc)})