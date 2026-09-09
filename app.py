import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)

# ========== CONFIGURACIÓN DE RUTAS PERSISTENTES ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
DB_PATH = os.path.join(DATA_DIR, 'dnd.db')

# Crear carpetas si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

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
    order = db.Column(db.Integer, default=0)

class Ability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    icon = db.Column(db.String(50), default='fa-star')
    order = db.Column(db.Integer, default=0)

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
    return render_template('index.html')

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

# ==================== API ====================

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

@app.route('/api/upload_sprite', methods=['POST'])
@login_required
def upload_sprite():
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Archivo vacío'}), 400
    if file:
        try:
            img = Image.open(file.stream)
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (0,0,0))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            filename = f"{current_user.id}_{int(datetime.now().timestamp())}.webp"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            img.save(filepath, 'webp', quality=80)
            url = f"/uploads/{filename}"
            return jsonify({'url': url})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Error al procesar'}), 400

# Ruta para servir archivos subidos
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/items', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def api_items():
    if request.method == 'GET':
        items = Item.query.filter_by(user_id=current_user.id).order_by(Item.order).all()
        return jsonify([{
            'id': i.id,
            'name': i.name,
            'quantity': i.quantity,
            'icon': i.icon,
            'order': i.order
        } for i in items])

    if request.method == 'POST':
        data = request.json
        max_order = db.session.query(db.func.max(Item.order)).filter_by(user_id=current_user.id).scalar() or 0
        item = Item(
            user_id=current_user.id,
            name=data['name'],
            quantity=data.get('quantity', 1),
            icon=data.get('icon', 'fa-box'),
            order=max_order + 1
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'id': item.id, 'message': 'Item añadido'}), 201

    if request.method == 'PUT':
        data = request.json
        item = Item.query.filter_by(id=data['id'], user_id=current_user.id).first()
        if not item:
            return jsonify({'error': 'Item no encontrado'}), 404
        item.name = data.get('name', item.name)
        item.quantity = data.get('quantity', item.quantity)
        item.icon = data.get('icon', item.icon)
        db.session.commit()
        return jsonify({'message': 'Item actualizado'})

    if request.method == 'DELETE':
        item_id = request.args.get('id')
        item = Item.query.filter_by(id=item_id, user_id=current_user.id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            return jsonify({'message': 'Item eliminado'})
        return jsonify({'error': 'Item no encontrado'}), 404

@app.route('/api/items/reorder', methods=['PUT'])
@login_required
def reorder_items():
    data = request.json
    ids = data.get('ids', [])
    for order, item_id in enumerate(ids, start=1):
        item = Item.query.filter_by(id=item_id, user_id=current_user.id).first()
        if item:
            item.order = order
    db.session.commit()
    return jsonify({'message': 'Orden actualizado'})

@app.route('/api/abilities', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def api_abilities():
    if request.method == 'GET':
        abilities = Ability.query.filter_by(user_id=current_user.id).order_by(Ability.order).all()
        return jsonify([{
            'id': a.id,
            'name': a.name,
            'type': a.type,
            'icon': a.icon,
            'order': a.order
        } for a in abilities])

    if request.method == 'POST':
        data = request.json
        max_order = db.session.query(db.func.max(Ability.order)).filter_by(user_id=current_user.id).scalar() or 0
        ability = Ability(
            user_id=current_user.id,
            name=data['name'],
            type=data['type'],
            icon=data.get('icon', 'fa-star'),
            order=max_order + 1
        )
        db.session.add(ability)
        db.session.commit()
        return jsonify({'id': ability.id, 'message': 'Añadido'}), 201

    if request.method == 'PUT':
        data = request.json
        ability = Ability.query.filter_by(id=data['id'], user_id=current_user.id).first()
        if not ability:
            return jsonify({'error': 'No encontrado'}), 404
        ability.name = data.get('name', ability.name)
        ability.type = data.get('type', ability.type)
        ability.icon = data.get('icon', ability.icon)
        db.session.commit()
        return jsonify({'message': 'Actualizado'})

    if request.method == 'DELETE':
        ability_id = request.args.get('id')
        ability = Ability.query.filter_by(id=ability_id, user_id=current_user.id).first()
        if ability:
            db.session.delete(ability)
            db.session.commit()
            return jsonify({'message': 'Eliminado'})
        return jsonify({'error': 'No encontrado'}), 404

@app.route('/api/abilities/reorder', methods=['PUT'])
@login_required
def reorder_abilities():
    data = request.json
    ids = data.get('ids', [])
    for order, ability_id in enumerate(ids, start=1):
        ability = Ability.query.filter_by(id=ability_id, user_id=current_user.id).first()
        if ability:
            ability.order = order
    db.session.commit()
    return jsonify({'message': 'Orden actualizado'})

# ==================== INICIO ====================

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
