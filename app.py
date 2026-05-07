from datetime import datetime, timedelta
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
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    celular = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)
    es_cliente = db.Column(db.Boolean, default=False)
    saldo_ficticio = db.Column(db.Float, default=1000.00)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    precio_unitario = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    observacion = db.Column(db.String(500))
    responsable = db.Column(db.String(100))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

class Venta(db.Model):
    __tablename__ = 'ventas'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0)
    estado = db.Column(db.String(20), default='completada')
    
    cliente = db.relationship('Usuario', backref='ventas', lazy=True)
    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True, cascade='all, delete-orphan')

class DetalleVenta(db.Model):
    __tablename__ = 'detalles_venta'
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('inventario.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    
    producto = db.relationship('Inventario', backref='detalles_venta', lazy=True)

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
            es_admin=True,
            es_cliente=False,
            saldo_ficticio=0
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Usuario admin creado: usuario='admin', contraseña='admin123'")
    
    cliente_ejemplo = Usuario.query.filter_by(usuario='cliente1').first()
    if not cliente_ejemplo:
        cliente_password = hash_password('cliente123')
        cliente_ejemplo = Usuario(
            nombre='Cliente Ejemplo',
            usuario='cliente1',
            celular='1234567890',
            email='cliente@ejemplo.com',
            password_hash=cliente_password,
            es_admin=False,
            es_cliente=True,
            saldo_ficticio=5000.00
        )
        db.session.add(cliente_ejemplo)
        db.session.commit()
        print("✅ Cliente de ejemplo creado: usuario='cliente1', contraseña='cliente123', saldo=5000")

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
        es_cliente = request.form.get('es_cliente') == 'on'
        
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
            es_admin=False,
            es_cliente=es_cliente,
            saldo_ficticio=1000.00 if es_cliente else 0.00
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
            elif user.es_cliente:
                return redirect(url_for('tienda'))
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
    
    total_ventas = db.session.query(db.func.sum(Venta.total)).scalar() or 0
    total_productos_vendidos = db.session.query(db.func.sum(DetalleVenta.cantidad)).scalar() or 0
    
    producto_mas_vendido = db.session.query(
        Inventario.producto,
        db.func.sum(DetalleVenta.cantidad).label('total_vendido')
    ).join(DetalleVenta, Inventario.id == DetalleVenta.producto_id)\
     .group_by(Inventario.id)\
     .order_by(db.func.sum(DetalleVenta.cantidad).desc())\
     .first()
    
    total_clientes = Usuario.query.filter_by(es_cliente=True).count()
    ventas_recientes = Venta.query.order_by(Venta.fecha.desc()).limit(10).all()
    
    return render_template('dashboard.html', 
                         usuarios=usuarios, 
                         inventarios=inventarios, 
                         current_user=current_user,
                         total_ventas=total_ventas,
                         total_productos_vendidos=total_productos_vendidos,
                         producto_mas_vendido=producto_mas_vendido,
                         total_clientes=total_clientes,
                         ventas_recientes=ventas_recientes)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))

# ============ RUTAS DE TIENDA ============
@app.route('/tienda')
@login_required
def tienda():
    if not current_user.es_cliente and not current_user.es_admin:
        flash('Esta sección es solo para clientes', 'error')
        return redirect(url_for('perfil'))
    
    productos = Inventario.query.filter(Inventario.cantidad > 0).all()
    return render_template('tienda.html', productos=productos, usuario=current_user)

@app.route('/comprar', methods=['POST'])
@login_required
def comprar():
    if not current_user.es_cliente:
        return jsonify({'error': 'Solo clientes pueden comprar'}), 403
    
    data = request.json
    items = data.get('items', [])
    
    if not items:
        return jsonify({'error': 'Carrito vacío'}), 400
    
    total_compra = 0
    productos_a_comprar = []
    
    for item in items:
        producto = Inventario.query.get(item['producto_id'])
        if not producto:
            return jsonify({'error': f'Producto no existe'}), 400
        
        if producto.cantidad < item['cantidad']:
            return jsonify({'error': f'Stock insuficiente para {producto.producto}. Disponible: {producto.cantidad}'}), 400
        
        subtotal = producto.precio * item['cantidad']
        total_compra += subtotal
        productos_a_comprar.append({
            'producto': producto,
            'cantidad': item['cantidad'],
            'subtotal': subtotal
        })
    
    if current_user.saldo_ficticio < total_compra:
        return jsonify({'error': f'Saldo insuficiente. Tu saldo es ${current_user.saldo_ficticio:.2f} y el total es ${total_compra:.2f}'}), 400
    
    nueva_venta = Venta(
        cliente_id=current_user.id,
        total=total_compra,
        estado='completada'
    )
    db.session.add(nueva_venta)
    db.session.flush()
    
    for item_data in productos_a_comprar:
        producto = item_data['producto']
        cantidad = item_data['cantidad']
        subtotal = item_data['subtotal']
        
        detalle = DetalleVenta(
            venta_id=nueva_venta.id,
            producto_id=producto.id,
            cantidad=cantidad,
            precio_unitario=producto.precio,
            subtotal=subtotal
        )
        db.session.add(detalle)
        
        producto.cantidad -= cantidad
        
        movimiento = MovimientoInventario(
            producto_id=producto.id,
            tipo='salida',
            cantidad=cantidad,
            precio_unitario=producto.precio,
            observacion=f'Venta #{nueva_venta.id} - Cliente: {current_user.nombre}',
            responsable=current_user.nombre
        )
        db.session.add(movimiento)
    
    current_user.saldo_ficticio -= total_compra
    db.session.commit()
    
    return jsonify({
        'success': True,
        'mensaje': f'¡Compra realizada con éxito! Total: ${total_compra:.2f}',
        'venta_id': nueva_venta.id,
        'nuevo_saldo': current_user.saldo_ficticio
    })

@app.route('/mis-compras')
@login_required
def mis_compras():
    if not current_user.es_cliente:
        flash('Acceso denegado', 'error')
        return redirect(url_for('perfil'))
    
    ventas = Venta.query.filter_by(cliente_id=current_user.id).order_by(Venta.fecha.desc()).all()
    return render_template('mis_compras.html', ventas=ventas, usuario=current_user)

@app.route('/recargar-saldo', methods=['POST'])
@login_required
def recargar_saldo():
    if not current_user.es_cliente:
        return jsonify({'error': 'Acceso denegado'}), 403
    
    data = request.json
    monto = float(data.get('monto', 0))
    
    if monto <= 0:
        return jsonify({'error': 'El monto debe ser mayor a 0'}), 400
    
    current_user.saldo_ficticio += monto
    db.session.commit()
    
    return jsonify({
        'success': True,
        'nuevo_saldo': current_user.saldo_ficticio,
        'mensaje': f'¡Se recargaron ${monto:.2f} exitosamente!'
    })

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
    codigo = data.get('codigo')
    
    producto_existente = Inventario.query.filter_by(codigo=codigo).first()
    
    if producto_existente:
        cantidad_nueva = int(data.get('cantidad', 0))
        cantidad_anterior = producto_existente.cantidad
        producto_existente.cantidad += cantidad_nueva
        
        if data.get('producto'):
            producto_existente.producto = data.get('producto')
        if data.get('descripcion'):
            producto_existente.descripcion = data.get('descripcion')
        if data.get('precio'):
            producto_existente.precio = float(data.get('precio'))
        if data.get('categoria'):
            producto_existente.categoria = data.get('categoria')
        if data.get('ubicacion'):
            producto_existente.ubicacion = data.get('ubicacion')
        if data.get('stock_minimo'):
            producto_existente.stock_minimo = int(data.get('stock_minimo'))
        if data.get('proveedor'):
            producto_existente.proveedor = data.get('proveedor')
        
        db.session.commit()
        
        return jsonify({
            'message': f'Producto existente. Cantidad actualizada',
            'id': producto_existente.id,
            'existente': True,
            'cantidad_anterior': cantidad_anterior,
            'cantidad_agregada': cantidad_nueva,
            'nueva_cantidad': producto_existente.cantidad
        }), 200
    else:
        nuevo_producto = Inventario(
            codigo=codigo,
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
        
        return jsonify({
            'message': 'Producto nuevo creado exitosamente', 
            'id': nuevo_producto.id,
            'existente': False,
            'nueva_cantidad': nuevo_producto.cantidad
        }), 201

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
        es_admin=data.get('es_admin', False),
        es_cliente=data.get('es_cliente', False),
        saldo_ficticio=data.get('saldo_ficticio', 1000.00 if data.get('es_cliente') else 0)
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
    if 'es_cliente' in data:
        usuario.es_cliente = data['es_cliente']
    if 'saldo_ficticio' in data:
        usuario.saldo_ficticio = data['saldo_ficticio']
    
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)