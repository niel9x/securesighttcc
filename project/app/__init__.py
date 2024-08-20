from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '#'

    # Registro dos blueprints
    from app.routes import routes
    app.register_blueprint(routes)

    socketio.init_app(app)
    return app
