import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from conexion2 import conectarsql



def auditlog(Usuario1, Usuario2, accion, restaurante1):
    
    db_connection = conectarsql()
    cursor = db_connection.cursor()

    # Obtener el código del usuario modificador (quien está creando el usuario)
    codUsuario = """SELECT cod_usuario FROM Users WHERE Usuario = ?"""
    cursor.execute(codUsuario, (Usuario1,))
    print("Usuario1:", Usuario1)
    UsuarioM = cursor.fetchone()
    if UsuarioM:
            UsuarioM = UsuarioM[0]
    else:
            UsuarioM = None  # O maneja el caso de error si es necesario

        # Obtener el código del restaurante si está disponible
    
    restaurante = """Select Cod_Restaurante from Restaurante where Cod_Tienda = ?"""
    cursor.execute(restaurante, (restaurante1,))
    cod_restaurante = cursor.fetchone()
    if cod_restaurante:
            cod_restaurante = cod_restaurante[0]    
            print("Cod_Restaurante:", cod_restaurante)
    else:
            cod_restaurante = None
        # Obtener el código del usuario creado (si lo necesitas, aquí 'cod' no está definido, así que lo dejamos como None)
    codUsuario1 = """SELECT cod_usuario FROM Users WHERE Usuario = ?"""
    cursor.execute(codUsuario1,(Usuario2) )
    cod = cursor.fetchone()
    if cod:
            cod = cod[0]
    else:
            cod = None
            
    if accion == 1:
        accion_texto = "Bot creo usuario"
    elif accion == 2: 
        accion_texto = "Bot reseteo clave"
    elif accion == 3:
        accion_texto = "Bot agrego un centro"
    elif accion == 4:       
        accion_texto = "Bot realizo cambio centro"
        
    
        # Insertar el registro en la tabla AuditLog
    insert_query2 = """
                INSERT INTO AuditLog (Cod_Restaurante, Cod_Usuario, Accion, Modificador, Fecha_Log) 
                VALUES (?, ?, ?, ?, GETDATE())
                """
    cursor.execute(
                    insert_query2,
                    (
                        cod_restaurante,
                        cod, 
                        accion_texto,
                        UsuarioM
                    ),

                )
    db_connection.commit()
    
if __name__ == "__main__":
    Usuario1 = "mduque"
    Usuario2 = "lmolina"
    restaurante = "V005"
    accion = 2  # 1 para crear usuario, 2 para resetear clave
    
    try:
        auditlog(Usuario1, Usuario2, accion, restaurante)
        print("Registro de auditoría creado exitosamente.")
    except Exception as e:
        print(f"Error al crear el registro de auditoría: {e}")
    