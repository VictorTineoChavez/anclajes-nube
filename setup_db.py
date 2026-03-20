from app import app, db
from models import User, Product, Category
from werkzeug.security import generate_password_hash  # <--- IMPORTANTE

with app.app_context():
    # 1. Borrar todo y crear de nuevo
    db.drop_all()
    db.create_all()
    print(">>> Base de datos reiniciada.")
    
    # 2. CREAR USUARIOS (Con contraseñas seguras)
    admin = User(
        username='admin', 
        password=generate_password_hash('123'),  # <--- ENCRIPTADO
        nombre_completo='Administrador General',
        role='admin'
    )
    
    jefe_ventas = User(
        username='jefe', 
        password=generate_password_hash('123'),  # <--- ENCRIPTADO
        nombre_completo='Roberto Gómez (Jefe Ventas)', 
        role='administracion'
    )
    
    vendedor = User(
        username='juan', 
        password=generate_password_hash('123'),  # <--- ENCRIPTADO
        nombre_completo='Juan Pérez (Vendedor)', 
        role='vendedor'
    )
    
    almacen = User(
        username='pedro', 
        password=generate_password_hash('123'),  # <--- ENCRIPTADO
        nombre_completo='Pedro Castillo (Almacén)', 
        role='almacen'
    )
    
    db.session.add_all([admin, jefe_ventas, vendedor, almacen])
    db.session.commit()
    print(">>> Usuarios y tablas creadas exitosamente con seguridad activa.")