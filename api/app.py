from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegisterForm
from models import db, User
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-muy-segura-cambiar-en-produccion'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Crear las tablas de base de datos
with app.app_context():
    db.create_all()

# Decorador para rutas que requieren suscripción activa
def suscripcion_activa_required(func):
    @login_required
    def decorated_view(*args, **kwargs):
        # Comprueba si la suscripción está activa por fecha y flag
        if (not current_user.is_subscribed or 
            not current_user.subscription_end_date or 
            current_user.subscription_end_date < datetime.utcnow()):
            flash('Necesitas una suscripción activa para acceder a esta sección.', 'warning')
            return redirect(url_for('dashboard'))
        return func(*args, **kwargs)
    decorated_view.__name__ = func.__name__
    return decorated_view

# Rutas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('El correo electrónico ya está registrado.', 'danger')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registro exitoso. Por favor inicia sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    now = datetime.utcnow()
    return render_template('dashboard.html', username=current_user.username, now=now)

@app.route('/suscribirse', methods=['POST'])
@login_required
def suscribirse():
    user = current_user
    user.is_subscribed = True
    user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
    db.session.commit()
    flash('¡Gracias por suscribirte! Ahora tienes acceso completo durante 30 días.', 'success')
    return redirect(url_for('dashboard'))

# Ruta ejemplo solo para usuarios suscritos activamente
@app.route('/zona-premium')
@suscripcion_activa_required
def zona_premium():
    return "<h2>Esto solo lo ve un usuario con suscripción activa.</h2>"

if __name__ == '__main__':
    app.run(debug=True)
