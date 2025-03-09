"""
(c) 2024 Zachariah Michael Lagden (All Rights Reserved)
You may not use, copy, distribute, modify, or sell this code without the express permission of the author.

This is the main endpoints file for the website. It contains the main endpoints for the website and their
associated logic.
"""

# Import the required modules

# Python Standard Library
import json
import uuid

# Flask Modules
from flask import Blueprint, render_template, session, abort, current_app

# Database Modules
from db import users_cl

# Create a Blueprint for main routes
blueprint = Blueprint("main", __name__, url_prefix="/")


# Helper Functions


def get_user_from_session():
    """Get user from session or return None."""
    if "uuid" not in session:
        return None
    user = users_cl.find_one({"uuid": session["uuid"]})
    if not user:
        session.pop("uuid", None)
    return user


def load_available_services():
    """Load available services from JSON file."""
    with current_app.open_resource("data/services.json") as f:
        return json.load(f)


def update_user_services(user, available_services):
    """Update user services based on available services."""
    user_services = user.get("services", {})
    services_updated = False

    for service_id, service_info in available_services.items():
        if service_id not in user_services:
            user_services[service_id] = {
                "enabled": False,
                "public": True,
                "setup_complete": not service_info.get("setup_required", False),
            }
            services_updated = True

        user_services[service_id].update(
            {
                "id": service_id,
                "name": service_info["name"],
                "description": service_info["description"],
                "routes": service_info.get("routes", {}),
            }
        )

    if services_updated:
        users_cl.update_one(
            {"uuid": user["uuid"]}, {"$set": {"services": user_services}}
        )

    return user_services


# Route Endpoints


@blueprint.route("/")
def index():
    if not get_user_from_session():
        return render_template("login_register.html")
    return render_template("dashboard.html", active_page="home")


@blueprint.route("/services")
def services():
    user = get_user_from_session()
    if not user:
        return render_template("login_register.html")

    available_services = load_available_services()
    user_services = update_user_services(user, available_services)

    return render_template(
        "services.html", services=user_services, active_page="services"
    )


@blueprint.route("/api")
def api_page():
    user = get_user_from_session()
    if not user:
        return render_template("login_register.html")

    if "api_key" not in user:
        api_key = str(uuid.uuid4())
        users_cl.update_one({"uuid": user["uuid"]}, {"$set": {"api_key": api_key}})
    else:
        api_key = user["api_key"]

    available_services = load_available_services()
    user_services = update_user_services(user, available_services)

    return render_template(
        "api.html",
        services=user_services,
        active_page="api",
        user_uuid=user["uuid"],
        api_key=api_key,
    )


@blueprint.route("/services/<service>")
def _service(service: str):
    user = get_user_from_session()
    if not user:
        return render_template("login_register.html")

    user_services = user.get("services", {})
    if service not in user_services:
        abort(404, description="Service not found in user services.")

    available_services = load_available_services()
    if service not in available_services:
        del user_services[service]
        users_cl.update_one(
            {"uuid": user["uuid"]}, {"$set": {"services": user_services}}
        )
        abort(
            404,
            description="Service not found in available services, deleted from user services.",
        )

    service_info = user_services[service]
    service_info.update(
        {
            "id": service,
            "name": available_services[service]["name"],
            "description": available_services[service]["description"],
        }
    )

    return render_template(
        "services/service.html", service=service_info, active_page="services"
    )
