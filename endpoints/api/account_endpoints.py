"""
(c) 2024 Zachariah Michael Lagden (All Rights Reserved)
You may not use, copy, distribute, modify, or sell this code without the express permission of the author.
"""

import uuid
import string
import random
import datetime
from typing import Dict, Any
from nltk.corpus import words  # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Blueprint, request, session, jsonify
from db import users_cl

blueprint = Blueprint("api_account", __name__, url_prefix="/api/account")

word_list = words.words()


def format_account_age(account_age_mil: float) -> str:
    """Format account age into a human-readable string."""
    time_units = [
        (365 * 24 * 60 * 60 * 1000, "Year"),
        (30 * 24 * 60 * 60 * 1000, "Month"),
        (24 * 60 * 60 * 1000, "Day"),
        (60 * 60 * 1000, "Hour"),
        (60 * 1000, "Minute"),
        (1000, "Second"),
    ]

    for unit_ms, unit_name in time_units:
        if account_age_mil >= unit_ms:
            value = int(account_age_mil // unit_ms)
            return f"{value} {unit_name}{'s' if value != 1 else ''}"

    return (
        f"{int(account_age_mil)} Millisecond{'s' if int(account_age_mil) != 1 else ''}"
    )


@blueprint.route("/")
def get_account_info():
    """Get the user's information including API key."""
    if "uuid" not in session:
        return jsonify({"ok": False, "error": "User not logged in"})

    user = users_cl.find_one({"uuid": session["uuid"]})
    if not user:
        session.pop("uuid", None)
        return jsonify({"ok": False, "error": "Session expired"})

    # Remove sensitive information
    user.pop("_id", None)
    user.pop("password", None)

    # Generate API key if it doesn't exist
    if "api_key" not in user:
        api_key = str(uuid.uuid4())
        user["api_key"] = api_key
        users_cl.update_one({"uuid": user["uuid"]}, {"$set": {"api_key": api_key}})
    else:
        api_key = user["api_key"]

    # Calculate account age
    account_age_ms = (
        datetime.datetime.now() - user["created_at"]
    ).total_seconds() * 1000
    account_age = format_account_age(account_age_ms)

    # Ensure 'logs' and 'api' keys exist
    if "logs" not in user:
        user["logs"] = {"api": []}
        users_cl.update_one({"uuid": user["uuid"]}, {"$set": {"logs": {"api": []}}})
    elif "api" not in user["logs"]:
        user["logs"]["api"] = []
        users_cl.update_one({"uuid": user["uuid"]}, {"$set": {"logs.api": []}})

    api_requests = len(user["logs"]["api"])

    return jsonify(
        {
            "ok": True,
            "user": user,
            "api_key": api_key,
            "readables": {"account_age": account_age},
            "stats": {"api_requests": api_requests},
        }
    )


@blueprint.route("/login", methods=["POST"])
def _login():
    """Login a user to the website."""
    username = request.json.get("username")
    password = request.json.get("password")

    user = users_cl.find_one({"username": username})
    if not user:
        return jsonify({"ok": False, "error": "User does not exist"})

    if not check_password_hash(user["password"], password):
        return jsonify({"ok": False, "error": "Incorrect password"})

    session["uuid"] = user["uuid"]
    return jsonify({"ok": True})


@blueprint.route("/register", methods=["POST"])
def _register():
    """Register a new user with a generated username and password."""
    while True:
        username = "-".join(random.choice(word_list).lower() for _ in range(4))
        if not users_cl.find_one({"username": username}):
            break

    password = "".join(
        random.choice(string.ascii_letters + string.digits + string.punctuation)
        for _ in range(16)
    )

    user = {
        "uuid": str(uuid.uuid4()),
        "username": username,
        "password": generate_password_hash(password),
        "created_at": datetime.datetime.now(),
        "logs": {"api": []},
        "services": {},
    }

    users_cl.insert_one(user)
    return jsonify({"ok": True, "username": username, "password": password})


@blueprint.route("/regenerate_api_key", methods=["POST"])
def regenerate_api_key():
    """Regenerate the user's API key."""
    if "uuid" not in session:
        return jsonify({"ok": False, "error": "User not logged in"})

    user = users_cl.find_one({"uuid": session["uuid"]})
    if not user:
        session.pop("uuid", None)
        return jsonify({"ok": False, "error": "Session expired"})

    # Generate a new API key
    new_api_key = str(uuid.uuid4())

    # Update the user's API key in the database
    users_cl.update_one({"uuid": user["uuid"]}, {"$set": {"api_key": new_api_key}})

    return jsonify({"ok": True, "new_api_key": new_api_key})
