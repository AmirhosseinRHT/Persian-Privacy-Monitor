from pymongo import MongoClient


class MongoDriver:
    """Handles MongoDB connection and operations."""

    def __init__(self, mongo_uri: str = "mongodb://localhost:27017", db_name: str = "privacy_monitor", collection: str = "scraped_pages"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection]

    def already_scraped(self, url: str) -> bool:
        """Check if a URL is already in MongoDB."""
        return self.collection.find_one({"url": url}) is not None

    def insert_doc(self, doc: dict):
        """Insert a document into MongoDB."""
        self.collection.insert_one(doc)
