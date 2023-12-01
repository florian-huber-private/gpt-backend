import re
from app import app, db
from flask import request, jsonify
from app.models import User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from datetime import datetime

def validate_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

def validate_password(password):
    return len(password) >= 8 and any(c.isdigit() for c in password) \
        and any(c.isupper() for c in password) and any(c.islower() for c in password)

def validate_task_title(title):
    return title and isinstance(title, str)

def validate_task_priority(priority):
    return priority in [p.name for p in TaskPriority]

def validate_task_status(status):
    return status in [s.name for s in TaskStatus]

def validate_category_id(category_id):
    if category_id is not None:
        return Category.query.get(category_id) is not None
    return True

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not validate_email(email):
        return jsonify(message="Ungültiges E-Mail-Format"), 400

    if not validate_password(password):
        return jsonify(message="Passwort nicht stark genug"), 400

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
    return jsonify(access_token=access_token, user=user.to_dict()), 200

    @app.route('/user/profile', methods=['GET', 'PUT'])
    @jwt_required()
    def user_profile():
        current_user = get_jwt_identity()
        user = User.query.filter_by(username=current_user).first()

        if request.method == 'PUT':
            data = request.get_json()
            new_username = data.get('username')
            new_email = data.get('email', user.email)
            new_password = data.get('password')

            # Benutzername-Validierung
            if new_username and new_username != user.username:
                if User.query.filter_by(username=new_username).first():
                    return jsonify(message="Benutzername bereits vergeben"), 409
                user.username = new_username

            if new_email and new_email != user.email:
                if User.query.filter_by(email=new_email).first():
                    return jsonify(message="E-Mail bereits vergeben"), 409
            
                if not validate_email(new_email):
                        return jsonify(message="Ungültiges E-Mail-Format"), 400
                
                user.email = new_email

            if new_password and not user.check_password(new_password):
                if not validate_password(password):
                    return jsonify(message="Passwort nicht stark genug"), 400
                user.set_password(new_password)

            db.session.commit()
            return jsonify(message="Profil aktualisiert", user=user.to_dict()), 200

        return jsonify(user.to_dict()), 200

@app.route('/tasks', methods=['POST', 'GET'])
@jwt_required()
def tasks():
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()

    if request.method == 'POST':
        data = request.get_json()

        if not validate_task_title(data.get('title')):
            return jsonify(message="Ungültiger Titel"), 400

        if 'priority' in data and not validate_task_priority(data.get('priority')):
            return jsonify(message="Ungültige Priorität"), 400

        if 'status' in data and not validate_task_status(data.get('status')):
            return jsonify(message="Ungültiger Status"), 400

        if 'category_id' in data and not validate_category_id(data.get('category_id')):
            return jsonify(message="Ungültige Kategorie-ID"), 400

        new_task = Task(
            user_id=user.id,
            title=data['title'],
            description=data.get('description', ''),
            priority=data.get('priority', TaskPriority.MEDIUM),
            category_id=data.get('category_id'),
            due_date=data.get('due_date'),
            status=TaskStatus.TODO
        )
        db.session.add(new_task)
        db.session.commit()
        return jsonify(message="Aufgabe erstellt"), 201

    if request.method == 'GET':
        tasks = Task.query.filter_by(user_id=user.id).all()
        return jsonify([task.to_dict() for task in tasks]), 200

@app.route('/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def task(task_id):
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()

    if not task:
        return jsonify(message="Aufgabe nicht gefunden"), 404

    if request.method == 'GET':
        return jsonify(task.to_dict()), 200

    if request.method == 'PUT':
        data = request.get_json()
        task.title = data.get('title', task.title)
        task.description = data.get('description', task.description)
        task.priority = data.get('priority', task.priority)
        task.category_id = data.get('category_id', task.category_id)
        task.due_date = data.get('due_date', task.due_date)
        task.status = data.get('status', task.status)
        db.session.commit()
        return jsonify(message="Aufgabe aktualisiert", task=task.to_dict()), 200

    if request.method == 'DELETE':
        db.session.delete(task)
        db.session.commit()
        return jsonify(message="Aufgabe gelöscht"), 200

@app.route('/categories', methods=['POST', 'GET'])
def categories():
    if request.method == 'POST':
        data = request.get_json()
        new_category = Category(name=data['name'])
        db.session.add(new_category)
        db.session.commit()
        return jsonify(message="Kategorie erstellt"), 201

    if request.method == 'GET':
        categories = Category.query.all()
        return jsonify([category.to_dict() for category in categories]), 200

@app.route('/categories/<int:category_id>', methods=['PUT', 'DELETE'])
def category(category_id):
    category = Category.query.get(category_id)

    if not category:
        return jsonify(message="Kategorie nicht gefunden"), 404

    if request.method == 'PUT':
        data = request.get_json()
        category.name = data.get('name', category.name)
        db.session.commit()
        return jsonify(message="Kategorie aktualisiert", category=category.to_dict()), 200

    if request.method == 'DELETE':
        db.session.delete(category)
        db.session.commit()
        return jsonify(message="Kategorie gelöscht"), 200

