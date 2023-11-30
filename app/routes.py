from app import app, db
from flask import request, jsonify
from app.models import User
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Überprüfen, ob Benutzer bereits existiert
    if User.query.filter_by(username=username).first() is not None:
        return jsonify(message="Benutzername bereits vergeben"), 409

    if User.query.filter_by(email=email).first() is not None:
        return jsonify(message="E-Mail bereits vergeben"), 409

    # Neuen Benutzer erstellen
    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify(message="Benutzer erfolgreich registriert"), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify(message="Falscher Benutzername oder Passwort"), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200
