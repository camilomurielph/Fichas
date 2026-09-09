import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dnd.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ==================== MODELOS ====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    character = db.relationship('Character', backref='user', uselist=False, cascade='all, delete-orphan')

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), default='Aventurero')
    sprite_url = db.Column(db.String(300), default='https://via.placeholder.com/150/2c2c2c/ffffff?text=⚔️')
    hp_current = db.Column(db.Integer, default=10)
    hp_max = db.Column(db.Integer, default=10)
    stamina_current = db.Column(db.Integer, default=10)
    stamina_max = db.Column(db.Integer, default=10)
    mana_current = db.Column(db.Integer, default=10)
    mana_max = db.Column(db.Integer, default=10)
    strength = db.Column(db.Integer, default=10)
    dexterity = db.Column(db.Integer, default=10)
    intelligence = db.Column(db.Integer, default=10)
    charisma = db.Column(db.Integer, default=10)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    icon = db.Column(db.String(50), default='fa-box')

class Ability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'habilidad' o 'bonus'
    icon = db.Column(db.String(50), default='fa-star')

# ==================== LOGIN ====================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== RUTAS FRONTEND ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Usuario o contraseña incorrectos')
    return render_template('index.html')  # el frontend maneja el login con fetch

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('El usuario ya existe')
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        user = User(username=username, password_hash=hashed)
        db.session.add(user)
        db.session.commit()
        # Crear personaje por defecto
        char = Character(user_id=user.id)
        db.session.add(char)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ==================== API (protegidas) ====================

@app.route('/api/character', methods=['GET', 'PUT'])
@login_required
def api_character():
    char = current_user.character
    if not char:
        return jsonify({'error': 'Personaje no encontrado'}), 404

    if request.method == 'GET':
        return jsonify({
            'id': char.id,
            'name': char.name,
            'sprite_url': char.sprite_url,
            'hp_current': char.hp_current,
            'hp_max': char.hp_max,
            'stamina_current': char.stamina_current,
            'stamina_max': char.stamina_max,
            'mana_current': char.mana_current,
            'mana_max': char.mana_max,
            'strength': char.strength,
            'dexterity': char.dexterity,
            'intelligence': char.intelligence,
            'charisma': char.charisma
        })

    if request.method == 'PUT':
        data = request.json
        char.name = data.get('name', char.name)
        char.sprite_url = data.get('sprite_url', char.sprite_url)
        char.hp_current = data.get('hp_current', char.hp_current)
        char.hp_max = data.get('hp_max', char.hp_max)
        char.stamina_current = data.get('stamina_current', char.stamina_current)
        char.stamina_max = data.get('stamina_max', char.stamina_max)
        char.mana_current = data.get('mana_current', char.mana_current)
        char.mana_max = data.get('mana_max', char.mana_max)
        char.strength = data.get('strength', char.strength)
        char.dexterity = data.get('dexterity', char.dexterity)
        char.intelligence = data.get('intelligence', char.intelligence)
        char.charisma = data.get('charisma', char.charisma)
        db.session.commit()
        return jsonify({'message': 'Personaje actualizado'})

@app.route('/api/items', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_items():
    if request.method == 'GET':
        items = Item.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': i.id,
            'name': i.name,
            'quantity': i.quantity,
            'icon': i.icon
        } for i in items])

    if request.method == 'POST':
        data = request.json
        item = Item(
            user_id=current_user.id,
            name=data['name'],
            quantity=data.get('quantity', 1),
            icon=data.get('icon', 'fa-box')
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'id': item.id, 'message': 'Item añadido'}), 201

    if request.method == 'DELETE':
        item_id = request.args.get('id')
        item = Item.query.filter_by(id=item_id, user_id=current_user.id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            return jsonify({'message': 'Item eliminado'})
        return jsonify({'error': 'Item no encontrado'}), 404

@app.route('/api/abilities', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_abilities():
    if request.method == 'GET':
        abilities = Ability.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': a.id,
            'name': a.name,
            'type': a.type,
            'icon': a.icon
        } for a in abilities])

    if request.method == 'POST':
        data = request.json
        ability = Ability(
            user_id=current_user.id,
            name=data['name'],
            type=data['type'],
            icon=data.get('icon', 'fa-star')
        )
        db.session.add(ability)
        db.session.commit()
        return jsonify({'id': ability.id, 'message': 'Habilidad/Bonus añadido'}), 201

    if request.method == 'DELETE':
        ability_id = request.args.get('id')
        ability = Ability.query.filter_by(id=ability_id, user_id=current_user.id).first()
        if ability:
            db.session.delete(ability)
            db.session.commit()
            return jsonify({'message': 'Eliminado'})
        return jsonify({'error': 'No encontrado'}), 404

# ==================== INICIO ====================

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
