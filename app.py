from datetime import datetime 
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import bcrypt
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui_cambiala'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ============ MODELOS ============
class Usuario(db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    celular = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)
    
    def get_id(self):
        return str(self.id)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_anonymous(self):
        return False

class Inventario(db.Model):
    __tablename__ = 'inventario'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    producto = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(200))
    cantidad = db.Column(db.Integer, default=0)
    precio = db.Column(db.Float, default=0.0)
    categoria = db.Column(db.String(50))
    ubicacion = db.Column(db.String(100))
    stock_minimo = db.Column(db.Integer, default=5)
    proveedor = db.Column(db.String(100))

class MovimientoInventario(db.Model):
    __tablename__ = 'movimiento_inventario'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('inventario.id'))
    tipo = db.Column(db.String(20))
    cantidad = db.Column(db.Integer)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))

# ============ CONFIGURACIÓN LOGIN ============
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ============ FUNCIONES DE CONTRASEÑA ============
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

# ============ CREAR TABLAS Y ADMIN ============
with app.app_context():
    db.create_all()
    admin = Usuario.query.filter_by(usuario='admin').first()
    if not admin:
        admin_password = hash_password('admin123')
        admin = Usuario(
            nombre='Administrador',
            usuario='admin',
            celular='0000000000',
            email='admin@ejemplo.com',
            password_hash=admin_password,
            es_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Usuario admin creado: usuario='admin', contraseña='admin123'")

# ============ RUTAS PRINCIPALES ============
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/opciones')
def opciones():
    return render_template('opciones.html')

@app.route('/procesar-opcion', methods=['POST'])
def procesar_opcion():
    try:
        data = request.get_json()
        opcion = data.get('opcion')
        
        if opcion == 'producto':
            return jsonify({"status": "success", "redirect": url_for('registro_producto')})
        elif opcion == 'login':
            return jsonify({"status": "success", "redirect": url_for('login')})
        else:
            return jsonify({"status": "error", "mensaje": "Opción no válida"}), 400
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

# ============ RUTAS DE USUARIO ============
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        usuario = request.form.get('usuario')
        celular = request.form.get('celular')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if Usuario.query.filter_by(usuario=usuario).first():
            flash('El nombre de usuario ya está en uso', 'error')
            return redirect(url_for('registro'))
        
        if Usuario.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado', 'error')
            return redirect(url_for('registro'))
        
        password_hash = hash_password(password)
        nuevo_usuario = Usuario(
            nombre=nombre, 
            usuario=usuario, 
            celular=celular,
            email=email, 
            password_hash=password_hash, 
            es_admin=False
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash('Registro exitoso. Por favor inicia sesión', 'success')
        return redirect(url_for('login'))
    
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        user = Usuario.query.filter_by(usuario=usuario).first()
        
        if user and verify_password(password, user.password_hash):
            login_user(user)
            flash(f'Bienvenido {user.nombre}!', 'success')
            if user.es_admin:
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('perfil'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html', usuario=current_user)

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.es_admin:
        flash('Acceso denegado. Se requieren permisos de administrador', 'error')
        return redirect(url_for('perfil'))
    
    usuarios = Usuario.query.all()
    inventarios = Inventario.query.all()
    
    return render_template('dashboard.html', usuarios=usuarios, inventarios=inventarios, current_user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))

# ============ RUTAS DE INVENTARIO ============
@app.route('/registro_producto', methods=['GET', 'POST'])
@login_required
def registro_producto():
    if not current_user.es_admin:
        flash('Acceso denegado', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        
        if Inventario.query.filter_by(codigo=codigo).first():
            flash('El código del producto ya existe', 'error')
            return redirect(url_for('registro_producto'))
        
        nuevo_producto = Inventario(
            codigo=codigo,
            producto=request.form.get('producto'),
            descripcion=request.form.get('descripcion', ''),
            cantidad=int(request.form.get('cantidad_inicial', 0)),
            precio=float(request.form.get('precio', 0)),
            categoria=request.form.get('categoria'),
            ubicacion=request.form.get('ubicacion'),
            stock_minimo=int(request.form.get('stock_minimo', 5)),
            proveedor=request.form.get('proveedor')
        )
        
        db.session.add(nuevo_producto)
        db.session.commit()
        
        flash('✅ Producto registrado exitosamente', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('registro_producto.html')

@app.route('/movimientos_inventario')
@login_required
def movimientos_inventario():
    if not current_user.es_admin:
        flash('Acceso denegado', 'error')
        return redirect(url_for('dashboard'))
    
    productos = Inventario.query.all()
    movimientos = MovimientoInventario.query.order_by(MovimientoInventario.fecha.desc()).all()
    
    return render_template('movimientos.html', 
                         productos=productos, 
                         movimientos=movimientos,
                         current_user=current_user)

# ============ API ENDPOINTS ============
@app.route('/api/inventarios', methods=['GET'])
@login_required
def get_inventarios():
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    productos = Inventario.query.all()
    return jsonify([{
        'id': p.id, 
        'codigo': p.codigo, 
        'producto': p.producto,
        'descripcion': p.descripcion, 
        'cantidad': p.cantidad, 
        'precio': p.precio,
        'categoria': p.categoria, 
        'ubicacion': p.ubicacion, 
        'stock_minimo': p.stock_minimo,
        'proveedor': p.proveedor
    } for p in productos])

@app.route('/api/inventarios/<int:id>', methods=['GET'])
@login_required
def get_inventario(id):
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    producto = Inventario.query.get_or_404(id)
    return jsonify({
        'id': producto.id, 
        'codigo': producto.codigo, 
        'producto': producto.producto,
        'descripcion': producto.descripcion, 
        'cantidad': producto.cantidad, 
        'precio': producto.precio,
        'categoria': producto.categoria, 
        'ubicacion': producto.ubicacion,
        'stock_minimo': producto.stock_minimo, 
        'proveedor': producto.proveedor
    })

@app.route('/api/inventarios', methods=['POST'])
@login_required
def crear_inventario():
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.json
    
    # Verificar si el código ya existe
    if Inventario.query.filter_by(codigo=data.get('codigo')).first():
        return jsonify({'error': 'El código ya existe'}), 400
    
    nuevo_producto = Inventario(
        codigo=data.get('codigo'),
        producto=data.get('producto'),
        descripcion=data.get('descripcion', ''),
        cantidad=int(data.get('cantidad', 0)),
        precio=float(data.get('precio', 0)),
        categoria=data.get('categoria', ''),
        ubicacion=data.get('ubicacion', ''),
        stock_minimo=int(data.get('stock_minimo', 5)),
        proveedor=data.get('proveedor', '')
    )
    
    db.session.add(nuevo_producto)
    db.session.commit()
    
    return jsonify({'message': 'Producto creado exitosamente', 'id': nuevo_producto.id}), 201

@app.route('/api/inventarios/<int:id>', methods=['PUT'])
@login_required
def actualizar_inventario(id):
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    producto = Inventario.query.get_or_404(id)
    data = request.json
    
    producto.codigo = data.get('codigo', producto.codigo)
    producto.producto = data.get('producto', producto.producto)
    producto.descripcion = data.get('descripcion', producto.descripcion)
    producto.cantidad = int(data.get('cantidad', producto.cantidad))
    producto.precio = float(data.get('precio', producto.precio))
    producto.categoria = data.get('categoria', producto.categoria)
    producto.ubicacion = data.get('ubicacion', producto.ubicacion)
    producto.stock_minimo = int(data.get('stock_minimo', producto.stock_minimo))
    producto.proveedor = data.get('proveedor', producto.proveedor)
    
    db.session.commit()
    
    return jsonify({'message': 'Producto actualizado exitosamente'})

@app.route('/api/inventarios/<int:id>', methods=['DELETE'])
@login_required
def eliminar_inventario(id):
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    producto = Inventario.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    
    return jsonify({'message': 'Producto eliminado exitosamente'})

@app.route('/api/usuarios', methods=['POST'])
@login_required
def crear_usuario_api():
    if not current_user.es_admin:
        return jsonify({'error': 'Acceso denegado'}), 403
    
    data = request.json
    
    if Usuario.query.filter_by(usuario=data.get('usuario')).first():
        return jsonify({'error': 'Usuario ya existe'}), 400
    
    if Usuario.query.filter_by(email=data.get('email')).first():
        return jsonify({'error': 'Email ya existe'}), 400
    
    password_hash = hash_password(data.get('password'))
    
    nuevo_usuario = Usuario(
        nombre=data.get('nombre'),
        usuario=data.get('usuario'),
        celular=data.get('celular'),
        email=data.get('email'),
        password_hash=password_hash,
        es_admin=data.get('es_admin', False)
    )
    
    db.session.add(nuevo_usuario)
    db.session.commit()
    
    return jsonify({'mensaje': 'Usuario creado exitosamente'}), 201

@app.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
@login_required
def actualizar_usuario_api(usuario_id):
    if not current_user.es_admin:
        return jsonify({'error': 'Acceso denegado'}), 403
    
    usuario = Usuario.query.get_or_404(usuario_id)
    data = request.json
    
    if 'nombre' in data:
        usuario.nombre = data['nombre']
    if 'usuario' in data:
        if Usuario.query.filter_by(usuario=data['usuario']).first() and usuario.usuario != data['usuario']:
            return jsonify({'error': 'Nombre de usuario ya existe'}), 400
        usuario.usuario = data['usuario']
    if 'celular' in data:
        usuario.celular = data['celular']
    if 'email' in data:
        if Usuario.query.filter_by(email=data['email']).first() and usuario.email != data['email']:
            return jsonify({'error': 'Email ya existe'}), 400
        usuario.email = data['email']
    if 'es_admin' in data:
        usuario.es_admin = data['es_admin']
    
    db.session.commit()
    
    return jsonify({'mensaje': 'Usuario actualizado exitosamente'})

@app.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
@login_required
def eliminar_usuario_api(usuario_id):
    if not current_user.es_admin:
        return jsonify({'error': 'Acceso denegado'}), 403
    
    usuario = Usuario.query.get_or_404(usuario_id)
    
    if usuario.id == current_user.id:
        return jsonify({'error': 'No puedes eliminar tu propio usuario'}), 400
    
    db.session.delete(usuario)
    db.session.commit()
    
    return jsonify({'mensaje': 'Usuario eliminado exitosamente'})

@app.route('/api/verificar-codigo/<codigo>', methods=['GET'])
@login_required
def verificar_codigo(codigo):
    existe = Inventario.query.filter_by(codigo=codigo).first() is not None
    return jsonify({'existe': existe})

# ============ INICIAR APLICACIÓN ============
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)