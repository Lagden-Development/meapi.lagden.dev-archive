from waitress import serve
from app import app

serve(app, host="0.0.0.0", port=40002, threads=100)
