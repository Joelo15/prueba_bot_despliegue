import sys
import os
import hashlib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from conexion2 import conectarsql
from cedula import validacion


def generar_usuario_unico(nombres: str, apellidos: str, cursor) -> str:
    nombres_lista = nombres.strip().split()
    nombre_completo = ''.join(nombres_lista).lower()
    apellido_base = apellidos.strip().split()[0].lower()

    intentos = []

    # Paso 1: Probar una letra a la vez del nombre completo + apellido
    for i in range(len(nombre_completo)):
        intento = nombre_completo[i] + apellido_base
        intentos.append(intento)

    # Paso 2: Si todas las letras individuales fallan, combinar de 2, 3, etc.
    for i in range(2, len(nombre_completo) + 1):
        intento = nombre_completo[:i] + apellido_base
        intentos.append(intento)

    # Probar cada nombre de usuario generado
    for usuario in intentos:
        sql = "SELECT 1 FROM Users WHERE Usuario = ?"
        cursor.execute(sql, (usuario,))
        if not cursor.fetchone():
            return usuario

    raise Exception("No se pudo generar un nombre de usuario único sin números.")




def new_user(cedula: str, nombres: str, apellidos: str) -> bool:
    
    descripcion = nombres + " " + apellidos
    iniciales= nombres[0].upper() + apellidos[0].upper()
    if not validacion(cedula):
        print("Cédula no válida.")
        return False

    try:
        conexion = conectarsql()
        with conexion.cursor() as cursor:
            usuario = generar_usuario_unico(nombres, apellidos, cursor)
            clave = hashlib.md5(usuario.encode('utf-8')).digest() 

            sql = """
            INSERT INTO Users (Cedula, Descripcion, Usuario,Iniciales, Clave, Fecha_creacion, Estado,Cod_Perfil, Tipo_Documento)
            VALUES (?, ?, ?, ?, ?, GETDATE(),'3','150','1')
            """
            cursor.execute(sql, (cedula, descripcion, usuario, iniciales, clave))

        conexion.commit()
        print(f"Usuario generado: {usuario}")
        return usuario

    except Exception as e:
        print(f"Error al crear el usuario: {e}")
        return False


if __name__ == "__main__":
    cedula = "1725507915"
    nombres = "Ana CArlota"
    apellidos = "Molina Guerra"
    

    try:
        resultado = new_user(cedula, nombres, apellidos)
        if resultado:
            print("Usuario creado exitosamente.")
        else:
            print("No se pudo crear el usuario.")
    except Exception as e:
        print(f"Error inesperado: {e}")
