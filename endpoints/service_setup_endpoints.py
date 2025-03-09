"""
(c) 2024 Zachariah Michael Lagden (All Rights Reserved)
You may not use, copy, distribute, modify, or sell this code without the express permission of the author.

This is the main endpoints file for the website. It contains the main endpoints for the website and their
associated logic.
"""

# Import the required modules

# Python Standard Library
import json
from typing import Dict, Any

# Flask Modules
from flask import Blueprint, redirect, render_template, session, abort, request
import requests
import base64
import urllib.parse
import time
import uuid

# Configuration
from config import CONFIG


# Database Modules
from db import users_cl

# Create a Blueprint for main routes
blueprint = Blueprint("service_setup", __name__, url_prefix="/")

# Spotify Setup
CLIENT_ID = CONFIG["spotify"]["client_id"]
CLIENT_SECRET = CONFIG["spotify"]["client_secret"]
REDIRECT_URI = "https://meapi.lagden.dev/api/auth/callback/spotify"

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
SCOPE = "user-read-currently-playing user-read-recently-played user-read-playback-state"


# Route Endpoints


@blueprint.route("/services/spotify/setup")
def spotify_setup():
    if "uuid" not in session:
        return redirect("/login")

    user = users_cl.find_one({"uuid": session["uuid"]})

    if not user:
        del session["uuid"]
        print("User not found")
        return redirect("/login")

    if "services" not in user:
        print("User does not have services")
        return redirect("/services")

    if "spotify" not in user["services"]:
        print("User does not have spotify")
        return redirect("/services")

    if "setup_complete" not in user["services"]["spotify"]:
        print("User does not have spotify setup complete")
        user["services"]["spotify"]["setup_complete"] = False
        users_cl.update_one({"uuid": session["uuid"]}, {"$set": user})

    if user["services"]["spotify"]["setup_complete"]:
        print("User has spotify setup complete")
        return redirect("/services")

    auth_query_parameters = {
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "client_id": CLIENT_ID,
        "state": str(uuid.uuid4()),
    }

    user["services"]["spotify"]["auth_query_parameters"] = auth_query_parameters
    users_cl.update_one({"uuid": session["uuid"]}, {"$set": user})

    url_args = urllib.parse.urlencode(auth_query_parameters)
    auth_url = f"{SPOTIFY_AUTH_URL}/?{url_args}"
    return redirect(auth_url)


@blueprint.route("/api/auth/callback/spotify")
def callback():
    if "uuid" not in session:
        print("User not in session")
        return redirect("/login")

    user = users_cl.find_one({"uuid": session["uuid"]})

    if not user:
        del session["uuid"]
        print("User not found")
        return redirect("/login")

    if "services" not in user:
        print("User does not have services")
        return redirect("/services")

    if "spotify" not in user["services"]:
        print("User does not have spotify")
        return redirect("/services")

    if "setup_complete" not in user["services"]["spotify"]:
        print("User does not have spotify setup complete")
        return redirect("/services")

    if user["services"]["spotify"]["setup_complete"]:
        print("User has spotify setup complete")
        return redirect("/services")

    if "auth_query_parameters" not in user["services"]["spotify"]:
        print("User does not have spotify auth query parameters")
        return redirect("/services")

    auth_query_parameters = user["services"]["spotify"]["auth_query_parameters"]

    # Get the authorization code from the URL parameters
    code = request.args.get("code")
    state = request.args.get("state")

    if state != auth_query_parameters["state"]:
        return "State mismatch error", 400

    # Exchange the authorization code for access and refresh tokens
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    client_creds = f"{CLIENT_ID}:{CLIENT_SECRET}"
    client_creds_b64 = base64.b64encode(client_creds.encode())

    token_headers = {
        "Authorization": f"Basic {client_creds_b64.decode()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    r = requests.post(SPOTIFY_TOKEN_URL, data=token_data, headers=token_headers)
    if r.status_code != 200:
        return f"Failed to get token: {r.text}", r.status_code

    token_info = r.json()

    # Save the tokens and expiry time in the database
    user["services"]["spotify"]["access_token"] = token_info["access_token"]
    user["services"]["spotify"]["refresh_token"] = token_info["refresh_token"]
    user["services"]["spotify"]["expiry_time"] = time.time() + token_info["expires_in"]
    user["services"]["spotify"]["setup_complete"] = True
    del user["services"]["spotify"]["auth_query_parameters"]
    users_cl.update_one({"uuid": session["uuid"]}, {"$set": user})

    return redirect("/services/spotify")
