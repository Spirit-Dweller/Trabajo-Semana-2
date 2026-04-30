from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'  # Cambiado a 'usuarios' (plural) para evitar conflicto
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    celular = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)  # Cambiado de 'password' a 'password_hash'
    es_admin = db.Column(db.Boolean, default=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

class Inventario(db.Model):
    __tablename__ = 'inventario'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    producto = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(500))
    cantidad = db.Column(db.Integer, default=0)
    precio = db.Column(db.Float, default=0)
    categoria = db.Column(db.String(50))
    ubicacion = db.Column(db.String(100))
    stock_minimo = db.Column(db.Integer, default=5)
    proveedor = db.Column(db.String(100))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MovimientoInventario(db.Model):
    __tablename__ = 'movimientos_inventario'
    
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('inventario.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'entrada' o 'salida'
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    observacion = db.Column(db.String(500))
    responsable = db.Column(db.String(100))
    
    producto = db.relationship('Inventario', backref='movimientos', lazy=True)