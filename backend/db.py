import os
import json
import re
from pymongo import MongoClient

# Use MongoDB by default, fallback to simple JSON file if not available
# Accept both MONGO_URI and MONGODB_URI for convenience (docker-compose uses the latter).
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")

def _value_matches(actual, condition):
    """Match a single field value against a Mongo-style condition (subset)."""
    if isinstance(condition, dict):
        for op, expected in condition.items():
            if op == "$regex":
                flags = 0
                opts = condition.get("$options", "")
                if "i" in opts:
                    flags |= re.IGNORECASE
                if actual is None or not re.search(expected, str(actual), flags):
                    return False
            elif op == "$in":
                if actual not in expected:
                    return False
            elif op == "$ne":
                if actual == expected:
                    return False
            elif op == "$options":
                continue
            else:
                # Unsupported operator -> no match (fail safe).
                return False
        return True
    return actual == condition


def _doc_matches(item, query):
    if not query:
        return True
    for k, v in query.items():
        if not _value_matches(item.get(k), v):
            return False
    return True


class MockCollection:
    def __init__(self, filename):
        self.filename = filename
        self.data = []
        self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = []

    def _save(self):
        with open(self.filename, 'w') as f:
            json.dump(self.data, f)

    def find(self, query=None):
        class Cursor:
            def __init__(self, data):
                self.data = data
            def sort(self, key, direction):
                # Extremely naive sort
                return self.data
            def __iter__(self):
                return iter(self.data)
                
        if not query:
            return Cursor(self.data)

        results = [item for item in self.data if _doc_matches(item, query)]
        return Cursor(results)

    def find_one(self, query=None):
        cursor = self.find(query)
        for item in cursor:
            return item
        return None

    def count_documents(self, query=None):
        cursor = self.find(query)
        count = 0
        for _ in cursor:
            count += 1
        return count

    def update_one(self, query, update, upsert=False):
        for idx, item in enumerate(self.data):
            if _doc_matches(item, query):
                if "$set" in update:
                    self.data[idx].update(update["$set"])
                self._save()
                return
                
        if upsert:
            new_item = {}
            new_item.update(query)
            if "$set" in update:
                new_item.update(update["$set"])
            self.data.append(new_item)
            self._save()

    def insert_one(self, doc):
        # Convert datetime to string for JSON serialization
        import datetime
        doc_copy = doc.copy()
        for k, v in doc_copy.items():
            if isinstance(v, datetime.datetime):
                doc_copy[k] = v.isoformat()
        self.data.append(doc_copy)
        self._save()
        
    def delete_many(self, query):
        new_data = []
        deleted_count = 0
        for item in self.data:
            if _doc_matches(item, query):
                deleted_count += 1
            else:
                new_data.append(item)
        self.data = new_data
        self._save()
        class DeleteResult:
            def __init__(self, count):
                self.deleted_count = count
        return DeleteResult(deleted_count)

try:
    if not MONGO_URI:
        raise Exception("MONGO_URI is not set")
    # Set a slightly longer timeout for remote MongoDB connection
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Force a server call to verify connection
    client.server_info()
    
    print("Successfully connected to MongoDB!")
    db = client.highwatch
    files_collection = db.files
    chats_collection = db.chats
    USING_MONGO = True

except Exception as e:
    print(f"Warning: Could not connect to MongoDB ({e}). Falling back to local JSON files.")
    if not os.path.exists("local_db"):
        os.makedirs("local_db")

    db = None
    files_collection = MockCollection("local_db/files.json")
    chats_collection = MockCollection("local_db/chats.json")
    USING_MONGO = False

# Registry so feature modules (e.g. analytics) can request arbitrary collections
# without each having to re-implement the Mongo/JSON fallback logic.
_collection_cache = {
    "files": files_collection,
    "chats": chats_collection,
}


def db_get_collection(name):
    """Return a collection by name, backed by Mongo or the JSON fallback."""
    if name in _collection_cache:
        return _collection_cache[name]
    if USING_MONGO and db is not None:
        coll = db[name]
    else:
        if not os.path.exists("local_db"):
            os.makedirs("local_db")
        coll = MockCollection(f"local_db/{name}.json")
    _collection_cache[name] = coll
    return coll
