import sys
import os

import hashlib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from conexion2 import conectarsql
from cedula import validacion

def clave_reset(usuario: str) -> tuple[bool, str]:

    try:
        conexion = conectarsql()
        with conexion.cursor() as cursor:
            # Verificar si el usuario existe
            sql = "SELECT * FROM Users WHERE Usuario = ?"
            cursor.execute(sql, (usuario,))
            user = cursor.fetchone()

            if not user:
                print("El usuario no existe.")
                return False, "❌ Usuario no encontrado."
            
            sql2 = "SELECT Estado FROM Users WHERE Usuario = ?"
            cursor.execute(sql2, (usuario,))
            estado = cursor.fetchone()
            estado = estado[0] 
            
            if not estado or estado !=4:
                print("El usuario no está habilitado para resetear la clave.")
                return False, "⚠️ El usuario no está habilitado para resetear la clave."

            # Actualizar la clave del usuario
            clave_hash = hashlib.md5(usuario.encode('utf-8')).digest() 
            sql_cod = "SELECT Cod_Usuario FROM Users WHERE Usuario = ?"
            cursor.execute(sql_cod, (usuario,))
            cod_usuario = cursor.fetchone()
            sql_update = "UPDATE Users SET Clave = ?, Estado ='1' WHERE Cod_usuario = ?"
            cursor.execute(sql_update, (clave_hash, cod_usuario[0]))

        conexion.commit()
        print("Clave actualizada exitosamente.")
        return True,"✅ Clave reseteada exitosamente."

    except Exception as e:
        print(f"Error al actualizar la clave: {e}")
        return False
    
if __name__ == "__main__":
    usuario = "imolina"
    
    try:
        resultado = clave_reset(usuario)
        if resultado:
            print("Clave reseteada exitosamente.")
        else:
            print("No se pudo resetear la clave.")
    except Exception as e:
        print(f"Error inesperado: {e}")