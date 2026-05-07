# modules/etl_financiero.py
import pandas as pd
from models import Venta, Producto, db
from datetime import datetime
import json

class ETLFinanciero:
    """ETL para procesar datos financieros del ecommerce"""
    
    def extract(self):
        """Extraer datos de ventas y productos"""
        ventas = Venta.query.all()
        productos = Inventario.query.all()  # Usar Inventario en lugar de Producto
        
        datos_ventas = [{
            'venta_id': v.id,
            'usuario_id': v.usuario_id,
            'total': v.total,
            'fecha': v.fecha,
            'items': len(v.items)
        } for v in ventas]
        
        datos_productos = [{
            'producto_id': p.id,
            'nombre': p.producto,  # Cambiar de 'nombre' a 'producto'
            'precio': p.precio,
            'cantidad_vendida': p.vendidos if hasattr(p, 'vendidos') else 0,
            'ingreso_total': p.precio * (p.vendidos if hasattr(p, 'vendidos') else 0)
        } for p in productos]
        
        return {
            'ventas': pd.DataFrame(datos_ventas),
            'productos': pd.DataFrame(datos_productos)
        }
    
    def transform(self, data):
        """Transformar datos para análisis financiero"""
        df_ventas = data['ventas']
        df_productos = data['productos']
        
        metricas = {
            'total_ingresos': float(df_ventas['total'].sum()) if not df_ventas.empty else 0,
            'num_transacciones': len(df_ventas),
            'ticket_promedio': float(df_ventas['total'].mean()) if not df_ventas.empty else 0,
            'producto_mas_vendido': df_productos.loc[df_productos['cantidad_vendida'].idxmax(), 'nombre'] if not df_productos.empty and df_productos['cantidad_vendida'].max() > 0 else 'N/A',
            'ingreso_por_producto': df_productos.to_dict('records') if not df_productos.empty else [],
            'ventas_por_dia': df_ventas.groupby(df_ventas['fecha'].dt.date)['total'].sum().to_dict() if not df_ventas.empty else {}
        }
        
        return metricas
    
    def load(self, metricas):
        """Cargar métricas procesadas a archivo"""
        with open('reportes_financieros.json', 'w', encoding='utf-8') as f:
            json.dump(metricas, f, indent=2, default=str)
        
        return metricas
    
    def run_etl(self):
        """Ejecutar proceso ETL completo"""
        print("Iniciando ETL financiero...")
        data = self.extract()
        print("✅ Datos extraídos")
        metricas = self.transform(data)
        print("✅ Datos transformados")
        resultado = self.load(metricas)
        print("✅ Datos cargados")
        return resultado