"""
(c) 2024 Zachariah Michael Lagden (All Rights Reserved)
You may not use, copy, distribute, modify, or sell this code without the express permission of the author.

This is the database file for the AR15 website. It contains the database connection logic.
"""

# Import the required modules

# Third Party Modules
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Config
from config import CONFIG

client = MongoClient(CONFIG["mongodb"]["uri"], server_api=ServerApi("1"))

web_app_db = client["web-app"]

users_cl = web_app_db["users"]


def get_mongo_client():
    return client
