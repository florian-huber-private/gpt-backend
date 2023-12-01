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

            user.email = new_email
            if new_password:
                user.password_hash = generate_password_hash(new_password)

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

