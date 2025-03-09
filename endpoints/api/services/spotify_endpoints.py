import datetime, json
import requests
from flask import Blueprint, request, jsonify, send_file, current_app
from db import users_cl
from PIL import Image
import io
from config import CONFIG
from functools import wraps
from bson.objectid import ObjectId

blueprint = Blueprint("api_services_spotify", __name__, url_prefix="/api/spotify")


def handle_error(message, status_code):
    current_app.logger.error(f"Error: {message}")
    return jsonify({"ok": False, "error": message}), status_code


def format_time(ms):
    try:
        progress = datetime.timedelta(milliseconds=ms)
        total_seconds = int(progress.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return (
            f"{hours}:{minutes:02}:{seconds:02}"
            if hours > 0
            else f"{minutes}:{seconds:02}"
        )
    except Exception as e:
        current_app.logger.error(f"Error formatting time: {str(e)}")
        return "00:00"


def convert_spotify_asset_url(url: str):
    try:
        id = url.replace("https://i.scdn.co/image/", "").replace(
            "http://i.scdn.co/image/", ""
        )
        return f"https://meapi.lagden.dev/api/spotify/asset/{id}"
    except Exception as e:
        current_app.logger.error(f"Error converting Spotify asset URL: {str(e)}")
        return url


def process_track(playback_data, track_data, include_progress=False):
    try:
        processed_track = {
            "title": track_data.get("name", "Unknown Title"),
            "artists": [
                {
                    "name": artist.get("name", "Unknown Artist"),
                    "uri": artist.get("uri", ""),
                }
                for artist in track_data.get("artists", [])
            ],
            "album": {
                "name": track_data.get("album", {}).get("name", "Unknown Album"),
                "uri": track_data.get("album", {}).get("uri", ""),
                "image": convert_spotify_asset_url(
                    track_data.get("album", {}).get("images", [{}])[0].get("url", "")
                ),
            },
        }

        if include_progress:
            progress_ms = playback_data.get("progress_ms", 0)
            duration_ms = playback_data.get("duration_ms", 0)

            processed_track["progress"] = {
                "progress_ms": progress_ms,
                "progress_percentage": (
                    round((progress_ms / duration_ms) * 100, 2)
                    if duration_ms > 0
                    else 0
                ),
                "progress_formatted": format_time(progress_ms),
            }

            processed_track["duration"] = {
                "duration_ms": duration_ms,
                "duration_formatted": format_time(duration_ms),
            }

        return processed_track
    except Exception as e:
        current_app.logger.error(f"Error processing track: {str(e)}")
        return {"error": "Failed to process track data"}


@blueprint.route("/")
def _route():
    return handle_error("No endpoint specified", 400)


@blueprint.route("/asset/<string:id>")
def _get_asset(id: str):
    try:
        url = f"https://i.scdn.co/image/{id}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return handle_error(
                f"Failed to fetch asset: {response.text}", response.status_code
            )

        image = Image.open(io.BytesIO(response.content))

        if "resize" in request.args:
            try:
                resize = int(request.args.get("resize", 0))
                if resize <= 0 or resize > 3000:
                    return handle_error("Invalid resize value", 400)
                image = image.resize((resize, resize), Image.Resampling.LANCZOS)
            except ValueError:
                return handle_error("Invalid resize parameter", 400)

        output = io.BytesIO()
        image.save(output, format="JPEG")
        output.seek(0)

        return send_file(output, mimetype="image/jpeg")
    except requests.RequestException as e:
        return handle_error(f"Network error: {str(e)}", 500)
    except Exception as e:
        return handle_error(f"Error processing image: {str(e)}", 500)


@blueprint.route("/listening/<string:uuid>")
def _get_listening(uuid: str):
    try:
        user = users_cl.find_one({"uuid": uuid})
        if not user:
            return handle_error("User not found", 404)

        spotify_service = user.get("services", {}).get("spotify", {})
        if not spotify_service.get("setup_complete") or not spotify_service.get(
            "enabled"
        ):
            return handle_error("Spotify service not set up or enabled", 404)

        # Check if the service is private and validate API key if it is
        if not spotify_service.get("public", True):
            api_key = request.args.get("api_key")
            if not api_key or api_key != user.get("api_key"):
                return handle_error("Invalid or missing API key", 403)

        access_token, refresh_token, expiry_time = (
            spotify_service.get("access_token"),
            spotify_service.get("refresh_token"),
            spotify_service.get("expiry_time", 0),
        )

        if expiry_time < datetime.datetime.now().timestamp():
            refresh_response = refresh_spotify_token(refresh_token)
            if not refresh_response["ok"]:
                return handle_error(
                    f"Failed to refresh token: {refresh_response.get('error', 'Unknown error')}",
                    500,
                )

            access_token, expiry_time = (
                refresh_response["access_token"],
                refresh_response["expiry_time"],
            )
            users_cl.update_one(
                {"uuid": uuid},
                {
                    "$set": {
                        "services.spotify.access_token": access_token,
                        "services.spotify.expiry_time": expiry_time,
                    }
                },
            )

        headers = {"Authorization": f"Bearer {access_token}"}

        currently_playing = get_currently_playing(headers)
        recent_tracks = get_recent_tracks(headers)

        return (
            jsonify(
                {
                    "ok": True,
                    "currently_playing": currently_playing,
                    "recent_tracks": recent_tracks,
                }
            ),
            200,
        )
    except Exception as e:
        return handle_error(f"Error fetching listening data: {str(e)}", 500)


def get_currently_playing(headers):
    try:
        response = requests.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 204:
            return {"is_playing": False}

        if response.status_code != 200:
            return {
                "is_playing": False,
                "error": f"Failed to fetch currently playing track: {response.text}",
            }

        currently_playing_data = response.json()
        if not currently_playing_data or not currently_playing_data.get("item"):
            return {"is_playing": False}

        playback_data = currently_playing_data
        playback_data["duration_ms"] = currently_playing_data["item"].get(
            "duration_ms", 0
        )

        track_data = currently_playing_data["item"]

        processed_track = process_track(
            playback_data, track_data, include_progress=True
        )
        processed_track["is_playing"] = track_data.get("is_playing", False)

        return processed_track
    except requests.RequestException as e:
        current_app.logger.error(f"Network error in get_currently_playing: {str(e)}")
        return {"is_playing": False, "error": "Network error occurred"}
    except Exception as e:
        current_app.logger.error(f"Error in get_currently_playing: {str(e)}")
        return {"is_playing": False, "error": "An unexpected error occurred"}


def get_recent_tracks(headers):
    try:
        response = requests.get(
            "https://api.spotify.com/v1/me/player/recently-played",
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            current_app.logger.error(f"Failed to fetch recent tracks: {response.text}")
            return []

        recent_tracks_raw = response.json()
        if not recent_tracks_raw or not recent_tracks_raw.get("items"):
            return []

        return [
            {
                **process_track(None, track["track"]),
                "played_at": track.get("played_at"),
            }
            for track in recent_tracks_raw["items"]
        ]
    except requests.RequestException as e:
        current_app.logger.error(f"Network error in get_recent_tracks: {str(e)}")
        return []
    except Exception as e:
        current_app.logger.error(f"Error in get_recent_tracks: {str(e)}")
        return []


def refresh_spotify_token(refresh_token):
    try:
        url = "https://accounts.spotify.com/api/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CONFIG["spotify"]["client_id"],
            "client_secret": CONFIG["spotify"]["client_secret"],
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(url, data=payload, headers=headers, timeout=10)

        if response.status_code == 400:
            return {
                "ok": False,
                "error": "Refresh token has expired, user needs to re-authenticate",
            }

        if response.status_code != 200:
            return {"ok": False, "error": f"Failed to refresh token: {response.text}"}

        data = response.json()

        user = users_cl.find_one({"services.spotify.refresh_token": refresh_token})
        if not user:
            return {"ok": False, "error": "User not found"}

        users_cl.update_one(
            {"_id": ObjectId(user["_id"])},
            {
                "$set": {
                    "services.spotify.access_token": data["access_token"],
                    "services.spotify.refresh_token": data.get(
                        "refresh_token", refresh_token
                    ),
                    "services.spotify.expiry_time": datetime.datetime.now().timestamp()
                    + data["expires_in"],
                }
            },
        )

        return {
            "ok": True,
            "access_token": data["access_token"],
            "expiry_time": datetime.datetime.now().timestamp() + data["expires_in"],
        }
    except requests.RequestException as e:
        current_app.logger.error(f"Network error in refresh_spotify_token: {str(e)}")
        return {"ok": False, "error": "Network error occurred while refreshing token"}
    except Exception as e:
        current_app.logger.error(f"Error in refresh_spotify_token: {str(e)}")
        return {
            "ok": False,
            "error": "An unexpected error occurred while refreshing token",
        }
