from datetime import datetime 
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import bcrypt
from models import db, Usuario, Inventario, MovimientoInventario

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui_cambiala'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Función para hashear contraseña
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# Función para verificar contraseña
def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

# Crear tablas y usuario admin por defecto
with app.app_context():
    db.create_all()
    # Crear usuario admin si no existe
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
        print("Usuario admin creado: usuario='admin', contraseña='admin123'")

# Ruta principal
@app.route('/')
def index():
    return redirect(url_for('login'))

# Endpoint de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        usuario = request.form.get('usuario')
        celular = request.form.get('celular')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Verificar si el usuario o email ya existe
        usuario_existente = Usuario.query.filter_by(usuario=usuario).first()
        email_existente = Usuario.query.filter_by(email=email).first()
        
        if usuario_existente:
            flash('El nombre de usuario ya está en uso', 'error')
            return redirect(url_for('registro'))
        
        if email_existente:
            flash('El correo electrónico ya está registrado', 'error')
            return redirect(url_for('registro'))
        
        # Hashear contraseña
        password_hash = hash_password(password)
        
        # Crear nuevo usuario (por defecto no es admin)
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

# Endpoint de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(usuario=usuario).first()
        
        if user and verify_password(password, user.password_hash):
            login_user(user)
            flash(f'Bienvenido {user.nombre}!', 'success')
            
            # Redirigir según rol
            if user.es_admin:
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('perfil'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

# Perfil de usuario normal
@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html', usuario=current_user)

# Dashboard de admin (CRUD de usuarios y productos)
@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.es_admin:
        flash('Acceso denegado. Se requieren permisos de administrador', 'error')
        return redirect(url_for('perfil'))
    
    usuarios = Usuario.query.all()
    
    # Obtener productos (usando una lista temporal, luego la reemplazarás con BD)
    # Aquí es donde cargarás los productos de tu base de datos
    productos = obtener_productos()  # Función que debes implementar
    productos = productos if productos else []  # Si no hay productos, lista vacía
    
    return render_template('dashboard.html', usuarios=usuarios, productos=productos, current_user=current_user)

# Función temporal para obtener productos (reemplázala con tu BD)
def obtener_productos():
    # Esto es temporal - reemplázalo con tu base de datos
    # Retorna una lista de productos de ejemplo
    return [
        {
            'id': 1,
            'nombre': 'Laptop',
            'categoria': 'electronica',
            'precio': 750.50,
            'stock': 10,
            'imagen': 'https://via.placeholder.com/50'
        },
        {
            'id': 2,
            'nombre': 'Mouse',
            'categoria': 'electronica',
            'precio': 25.99,
            'stock': 50,
            'imagen': 'https://via.placeholder.com/50'
        }
    ]

# BackEnd(Flask) Inventario - CORREGIDO
@app.route('/agregar_producto', methods=['GET', 'POST'])
@login_required  # Agregar decorador para requerir login
def agregar_producto():
    # Verificar si es admin
    if not current_user.es_admin:
        flash('Acceso denegado. Se requieren permisos de administrador', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Crear diccionario del producto
        nuevo_producto = {
            'id': len(obtener_productos()) + 1,  # ID autoincremental temporal
            'nombre': request.form['nombre_producto'],
            'categoria': request.form['categoria'],
            'precio': float(request.form['precio']),
            'stock': int(request.form['stock']),
            'descripcion': request.form['descripcion'],
            'imagen': request.form['imagen_url']
        }
        # Aquí guardas en tu base de datos
        # Por ahora mostramos en consola
        print(f"Producto guardado: {nuevo_producto}")
        
        flash('Producto agregado exitosamente', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('agregar_producto.html')

# API Endpoint para crear usuario (desde dashboard)
@app.route('/api/usuarios', methods=['POST'])
@login_required
def crear_usuario_api():
    if not current_user.es_admin:
        return jsonify({'error': 'Acceso denegado'}), 403
    
    data = request.json
    
    # Validar campos
    required_fields = ['nombre', 'usuario', 'celular', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo {field} requerido'}), 400
    
    # Verificar si existe
    if Usuario.query.filter_by(usuario=data['usuario']).first():
        return jsonify({'error': 'Usuario ya existe'}), 400
    
    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email ya existe'}), 400
    
    # Hashear contraseña
    password_hash = hash_password(data['password'])
    
    nuevo_usuario = Usuario(
        nombre=data['nombre'],
        usuario=data['usuario'],
        celular=data['celular'],
        email=data['email'],
        password_hash=password_hash,
        es_admin=data.get('es_admin', False)
    )
    
    db.session.add(nuevo_usuario)
    db.session.commit()
    #//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
   # ============ FUNCIONES PARA INVENTARIO ============

def obtener_productos_bd():
    """Obtiene todos los productos de la base de datos"""
    productos = Inventario.query.all()
    return [{
        'id': p.id,
        'codigo': p.codigo,
        'nombre': p.producto,
        'descripcion': p.descripcion,
        'categoria': p.categoria,
        'precio': p.precio,
        'stock': p.cantidad,
        'ubicacion': p.ubicacion,
        'stock_minimo': p.stock_minimo
    } for p in productos]
# ============ RUTAS PARA INVENTARIO ============

@app.route('/registro_producto', methods=['GET', 'POST'])
@login_required
def registro_producto():
    """Registrar nuevo producto en inventario"""
    if not current_user.es_admin:
        flash('Acceso denegado. Se requieren permisos de administrador', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        
        # Verificar si el código ya existe
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
        
        flash('Producto registrado exitosamente', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('registro_producto.html')

@app.route('/movimientos_inventario')
@login_required
def movimientos_inventario():
    """Página de movimientos de inventario"""
    if not current_user.es_admin:
        flash('Acceso denegado', 'error')
        return redirect(url_for('dashboard'))
    
    productos = Inventario.query.all()
    movimientos = MovimientoInventario.query.order_by(MovimientoInventario.fecha.desc()).all()
    
    return render_template('movimientos.html', 
                         productos=productos, 
                         movimientos=movimientos,
                         current_user=current_user)

@app.route('/api/inventarios', methods=['GET'])
@login_required
def get_inventarios():
    """API - Obtener todos los productos"""
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
        'stock_minimo': p.stock_minimo
    } for p in productos])

@app.route('/api/inventarios/<int:id>', methods=['GET'])
@login_required
def get_inventario(id):
    """API - Obtener un producto específico"""
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
        'stock_minimo': producto.stock_minimo
    })

@app.route('/api/inventarios', methods=['POST'])
@login_required
def crear_inventario():
    """API - Crear nuevo producto"""
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.json
    
    # Verificar código único
    if Inventario.query.filter_by(codigo=data['codigo']).first():
        return jsonify({'error': 'El código ya existe'}), 400
    
    nuevo_producto = Inventario(
        codigo=data['codigo'],
        producto=data['producto'],
        descripcion=data.get('descripcion', ''),
        cantidad=data.get('cantidad', 0),
        precio=data.get('precio', 0),
        categoria=data.get('categoria'),
        ubicacion=data.get('ubicacion'),
        stock_minimo=data.get('stock_minimo', 5),
        proveedor=data.get('proveedor')
    )
    
    db.session.add(nuevo_producto)
    db.session.commit()
    
    return jsonify({'message': 'Producto creado exitosamente', 'id': nuevo_producto.id}), 201

@app.route('/api/inventarios/<int:id>', methods=['PUT'])
@login_required
def actualizar_inventario_api(id):
    """API - Actualizar producto"""
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    producto = Inventario.query.get_or_404(id)
    data = request.json
    
    # Verificar código único si cambió
    if 'codigo' in data and data['codigo'] != producto.codigo:
        if Inventario.query.filter_by(codigo=data['codigo']).first():
            return jsonify({'error': 'El código ya existe'}), 400
        producto.codigo = data['codigo']
    
    # Actualizar campos
    producto.producto = data.get('producto', producto.producto)
    producto.descripcion = data.get('descripcion', producto.descripcion)
    producto.cantidad = data.get('cantidad', producto.cantidad)
    producto.precio = data.get('precio', producto.precio)
    producto.categoria = data.get('categoria', producto.categoria)
    producto.ubicacion = data.get('ubicacion', producto.ubicacion)
    producto.stock_minimo = data.get('stock_minimo', producto.stock_minimo)
    producto.proveedor = data.get('proveedor', producto.proveedor)
    producto.fecha_actualizacion = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'message': 'Producto actualizado exitosamente'})

@app.route('/api/inventarios/<int:id>', methods=['DELETE'])
@login_required
def eliminar_inventario_api(id):
    """API - Eliminar producto"""
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    producto = Inventario.query.get_or_404(id)
    
    # Verificar si tiene movimientos asociados
    if producto.movimientos:
        return jsonify({'error': 'No se puede eliminar producto con movimientos registrados'}), 400
    
    db.session.delete(producto)
    db.session.commit()
    
    return jsonify({'message': 'Producto eliminado exitosamente'})

@app.route('/api/movimientos', methods=['POST'])
@login_required
def registrar_movimiento():
    """API - Registrar entrada o salida de inventario"""
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    data = request.json
    
    producto = Inventario.query.get(data['producto_id'])
    if not producto:
        return jsonify({'error': 'Producto no encontrado'}), 404
    
    # Validar stock para salidas
    if data['tipo'] == 'salida' and producto.cantidad < data['cantidad']:
        return jsonify({'error': f'Stock insuficiente. Stock actual: {producto.cantidad}'}), 400
    
    # Crear movimiento
    movimiento = MovimientoInventario(
        producto_id=data['producto_id'],
        tipo=data['tipo'],
        cantidad=data['cantidad'],
        precio_unitario=data.get('precio_unitario'),
        observacion=data.get('observacion', ''),
        responsable=data.get('responsable', current_user.nombre),
        fecha=datetime.now()
    )
    
    # Actualizar stock
    if data['tipo'] == 'entrada':
        producto.cantidad += data['cantidad']
    else:
        producto.cantidad -= data['cantidad']
    
    producto.fecha_actualizacion = datetime.utcnow()
    
    db.session.add(movimiento)
    db.session.commit()
    
    return jsonify({
        'message': 'Movimiento registrado exitosamente',
        'id': movimiento.id,
        'nuevo_stock': producto.cantidad
    }), 201

@app.route('/api/verificar-codigo/<codigo>')
@login_required
def verificar_codigo(codigo):
    """API - Verificar si un código de producto ya existe"""
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    producto = Inventario.query.filter_by(codigo=codigo).first()
    return jsonify({'existe': producto is not None})

@app.route('/api/estadisticas/inventario')
@login_required
def estadisticas_inventario():
    """API - Estadísticas del inventario"""
    if not current_user.es_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    total_productos = Inventario.query.count()
    stock_bajo = Inventario.query.filter(Inventario.cantidad <= Inventario.stock_minimo).count()
    valor_total = db.session.query(db.func.sum(Inventario.cantidad * Inventario.precio)).scalar() or 0
    
    return jsonify({
        'total_productos': total_productos,
        'stock_bajo': stock_bajo,
        'valor_total_inventario': float(valor_total),
        'productos_con_stock_bajo': [{
            'nombre': p.producto,
            'stock': p.cantidad,
            'minimo': p.stock_minimo
        } for p in Inventario.query.filter(Inventario.cantidad <= Inventario.stock_minimo).all()]
    })
#///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
 
   
   
    return jsonify({
        'mensaje': 'Usuario creado exitosamente',
        'usuario': {
            'id': nuevo_usuario.id,
            'nombre': nuevo_usuario.nombre,
            'usuario': nuevo_usuario.usuario,
            'email': nuevo_usuario.email
        }
    }), 201

# Endpoint para actualizar usuario
@app.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
@login_required
def actualizar_usuario_api(usuario_id):
    if not current_user.es_admin:
        return jsonify({'error': 'Acceso denegado'}), 403
    
    usuario = Usuario.query.get_or_404(usuario_id)
    data = request.json
    
    # Actualizar campos
    if 'nombre' in data:
        usuario.nombre = data['nombre']
    if 'usuario' in data:
        # Verificar que el nuevo usuario no exista
        if Usuario.query.filter_by(usuario=data['usuario']).first() and usuario.usuario != data['usuario']:
            return jsonify({'error': 'Nombre de usuario ya existe'}), 400
        usuario.usuario = data['usuario']
    if 'celular' in data:
        usuario.celular = data['celular']
    if 'email' in data:
        if Usuario.query.filter_by(email=data['email']).first() and usuario.email != data['email']:
            return jsonify({'error': 'Email ya existe'}), 400
        usuario.email = data['email']
    if 'password' in data and data['password']:
        usuario.password_hash = hash_password(data['password'])
    if 'es_admin' in data:
        # No permitir que se quite el admin al último administrador
        admin_count = Usuario.query.filter_by(es_admin=True).count()
        if not data['es_admin'] and admin_count == 1 and usuario.es_admin:
            return jsonify({'error': 'No puedes quitar permisos de admin al único administrador'}), 400
        usuario.es_admin = data['es_admin']
    
    db.session.commit()
    
    return jsonify({
        'mensaje': 'Usuario actualizado exitosamente',
        'usuario': {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'usuario': usuario.usuario,
            'email': usuario.email,
            'es_admin': usuario.es_admin
        }
    })

# Endpoint para eliminar usuario
@app.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
@login_required
def eliminar_usuario_api(usuario_id):
    if not current_user.es_admin:
        return jsonify({'error': 'Acceso denegado'}), 403
    
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # No permitir eliminar al propio admin
    if usuario.id == current_user.id:
        return jsonify({'error': 'No puedes eliminar tu propio usuario'}), 400
    
    # No permitir eliminar al último administrador
    if usuario.es_admin:
        admin_count = Usuario.query.filter_by(es_admin=True).count()
        if admin_count == 1:
            return jsonify({'error': 'No puedes eliminar al único administrador'}), 400
    
    db.session.delete(usuario)
    db.session.commit()
    
    return jsonify({'mensaje': 'Usuario eliminado exitosamente'})

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))


# enpoints al entrar a la pagina 
@app.route('/opciones')
def opciones():
    """
    Endpoint para mostrar la plantilla de selección.
    Esto NO interfiere con otros endpoints porque usa una ruta específica.
    """
    return render_template('Ingreso.html')

# endpoints para opciones

@app.route('/procesar-opcion', methods=['POST'])
def procesar_opcion():
    """
    Endpoint que recibe la selección del usuario (producto o login).
    Puedes conectar esto con tu lógica existente.
    """
    try:
        data = request.get_json()
        opcion = data.get('opcion')
        
        logger.info(f"Usuario seleccionó: {opcion}")
        
        if opcion == 'producto':
            # Aquí puedes redirigir a tu formulario existente de productos
            # o llamar a tus funciones actuales
            return jsonify({
                "status": "success",
                "redirect": url_for('formulario_producto'),  # Si tienes un endpoint
                "mensaje": "Preparando formulario de producto"
            })
        
        elif opcion == 'login':
            # Aquí puedes redirigir a tu página de login existente
            return jsonify({
                "status": "success", 
                "redirect": url_for('login_page'),  # Si tienes un endpoint
                "mensaje": "Preparando autenticación"
            })
        
        else:
            return jsonify({
                "status": "error",
                "mensaje": "Opción no válida"
            }), 400
            
    except Exception as e:
        logger.error(f"Error procesando opción: {e}")
        return jsonify({
            "status": "error",
            "mensaje": "Error interno del servidor"
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

#////////////////////////////////////////////////////////////////////////

