"""
(c) 2024 Zachariah Michael Lagden (All Rights Reserved)
You may not use, copy, distribute, modify, or sell this code without the express permission of the author.
"""

import json
from flask import Blueprint, session, jsonify
from db import users_cl
from functools import wraps

blueprint = Blueprint("api_service", __name__, url_prefix="/api/service")


def load_services():
    with open("data/services.json", "r") as f:
        return json.load(f)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "uuid" not in session:
            return jsonify({"ok": False, "error": "User not logged in"}), 401
        user = users_cl.find_one({"uuid": session["uuid"]})
        if not user:
            session.pop("uuid", None)
            return jsonify({"ok": False, "error": "Session expired"}), 401
        return f(user, *args, **kwargs)

    return decorated_function


def service_exists(f):
    @wraps(f)
    def decorated_function(user, serviceId, *args, **kwargs):
        services = load_services()
        if serviceId not in services:
            return jsonify({"ok": False, "error": "Invalid service"}), 404

        if "services" not in user:
            user["services"] = {}

        if serviceId not in user["services"]:
            user["services"][serviceId] = {
                "enabled": False,
                "public": True,
                "setup_complete": not services[serviceId].get("setup_required", False),
            }
            users_cl.update_one(
                {"uuid": user["uuid"]}, {"$set": {"services": user["services"]}}
            )

        return f(user, serviceId, services, *args, **kwargs)

    return decorated_function


@blueprint.route("/<serviceId>")
@login_required
@service_exists
def get_service(user, serviceId, services):
    user_service = user["services"][serviceId]
    user_service.update(
        {
            "id": serviceId,
            "name": services[serviceId]["name"],
            "description": services[serviceId]["description"],
        }
    )
    return jsonify({"ok": True, "service": user_service})


@blueprint.route("/<serviceId>/enable", methods=["POST"])
@login_required
@service_exists
def enable_service(user, serviceId, services):
    user["services"][serviceId]["enabled"] = True
    users_cl.update_one(
        {"uuid": user["uuid"]}, {"$set": {"services": user["services"]}}
    )
    return jsonify({"ok": True, "service": user["services"][serviceId]})


@blueprint.route("/<serviceId>/disable", methods=["POST"])
@login_required
@service_exists
def disable_service(user, serviceId, services):
    user["services"][serviceId]["enabled"] = False
    users_cl.update_one(
        {"uuid": user["uuid"]}, {"$set": {"services": user["services"]}}
    )
    return jsonify({"ok": True, "service": user["services"][serviceId]})


@blueprint.route("/<serviceId>/make_public", methods=["POST"])
@login_required
@service_exists
def make_service_public(user, serviceId, services):
    user["services"][serviceId]["public"] = True
    users_cl.update_one(
        {"uuid": user["uuid"]}, {"$set": {"services": user["services"]}}
    )
    return jsonify({"ok": True, "service": user["services"][serviceId]})


@blueprint.route("/<serviceId>/make_private", methods=["POST"])
@login_required
@service_exists
def make_service_private(user, serviceId, services):
    user["services"][serviceId]["public"] = False
    users_cl.update_one(
        {"uuid": user["uuid"]}, {"$set": {"services": user["services"]}}
    )
    return jsonify({"ok": True, "service": user["services"][serviceId]})
