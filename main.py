from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,   
    filters,
)
import os
from dotenv import load_dotenv
from cedula import validacion
from Controller.administradores import lista
from Controller.new_user import new_user
from Controller.clave_reset import clave_reset
from Controller.auditlog import auditlog
from conexion2 import conectarsql
from Controller.reporte import generar_reporte_excel
import hashlib

ASK_ADMIN, ASK_CEDULA, ASK_OPTIONS, ASK_USER, ASK_COD_TIENDA, ASK_CENTRO_COSTO, ASK_FINAL, NEW_USER, CONFIRM_CHANGE,RESET_CLAVE,CEDULA, NOMBRES, APELLIDOS, ASK_CENTRO_COSTO_ORIGEN, ASK_CENTRO_COSTO_DESTINO, REPORTE = range(16)

INACTIVITY_TIMEOUT = 120

load_dotenv()

#########----------------------------------------------------------------------------------------------------------------------------------------------------------
async def start(update: Update, context: CallbackContext):
    
        await update.message.reply_text("¡Bienvenido! Por favor, ingresa tu usuario 👤:")
        return ASK_ADMIN
  

#########-----------------------------------------------------------------------------------------------------------------------------------------------------------
async def ask_cedula(update: Update, context: CallbackContext):
    """Pide la cédula después de recibir el usuario."""
    context.user_data["username"] = update.message.text
    await update.message.reply_text("Gracias. Ahora, por favor, ingresa tu clave 🗝️: \n(será eliminada del chat automáticamente por seguridad)")
    return ASK_CEDULA

#########------------------------------------------------------------------------------------------------------------------------------------------------------
async def validate_credentials(update: Update, context: CallbackContext):
    
    username = context.user_data.get("username")
    cedula = update.message.text
    clave_hash = hashlib.md5(cedula.encode('utf-8')).digest()  
    await update.message.delete()
    user_id = update.message.from_user.id 
    db_connection = conectarsql()
    cursor = db_connection.cursor()
    query = """
SELECT u.*,  p.nombre
FROM Users u
join Perfil p on u.Cod_Perfil = p.Cod_Perfil  
WHERE u.Usuario=? AND Clave = ? AND p.Nombre in (
'Administrador(Sistemas)',
'Gerente Operaciones',
'Sistemas',
'Auditor Local',
'Auditor Administrador',
'Gerente Operaciones Nac',
'Sistemas Desarrollo',
'Sistemas Operaciones',
'Planta Devoluciones y Pedidos',
'Sistemas Tercer Nivel',
'Administrador Recetas'
)"""
    cursor.execute(query, (username, clave_hash))
    result = cursor.fetchone()

    if result:
        context.user_data["cod_usuario"] = result[0]  
        await show_options(update, context)
        return ASK_OPTIONS
    else:
        if not lista(user_id):
            print("no esta registrado el id_telegram")
        await update.message.reply_text("❌ Credenciales incorrectas.\n ⚠️ O el usuario no esta autorizado.\n 🔄 Intenta de nuevo.")
        return ASK_ADMIN

#########----------------------------------------------------------Despliega las opciones existentes----------------------------------------------------------------------------------------------
async def show_options(update: Update, context: CallbackContext):
    
    keyboard = [
        [InlineKeyboardButton("Cambio de centro de costo", callback_data="option_2")],
        [InlineKeyboardButton("Agregar Centro de costo", callback_data="option_3")],
        [InlineKeyboardButton("Crear Usuario", callback_data="option_4")],
        [InlineKeyboardButton("Cambio de contraseña", callback_data="option_5")],
        [InlineKeyboardButton("Generar Reporte", callback_data="option_6")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        "¿Qué opción quieres realizar?", reply_markup=reply_markup
    )
    return ASK_OPTIONS

#########-----------------------------------------------------------Maneja la opcion q se escogio---------------------------------------------------------------------------------------------
async def handle_option_click(update: Update, context: CallbackContext):
   
    query = update.callback_query
    await query.answer()

    option = query.data
    context.user_data["option"] = option 

    if option == "option_2":
        await query.message.reply_text("Ingrese el usuario al que quiere realizar el cambio de centro de costo:")
        return ASK_USER
    elif option == "option_3":
        await query.message.reply_text("Ingrese el usuario al que quiere agregar un centro de costo:")
        return ASK_USER
    elif option == "option_4":
        await query.message.reply_text("Ingrese el numero de cédula del nuevo usuario:")
       
        return CEDULA
    elif option == "option_5":
        await query.message.reply_text("Ingrese el usuario al que desea resetear la clave:")
        return RESET_CLAVE
    elif option == "option_6":
        username = context.user_data.get("username")
        db_connection = conectarsql()
        with db_connection.cursor() as cursor:
            query_sql = """ 
            select Nombre from Perfil p
            join Users u on u.Cod_Perfil=p.Cod_Perfil
            where u.Usuario = ?
            """
            cursor.execute(query_sql, (username,))
            perfil = cursor.fetchone()
            perfil = perfil[0] if perfil else None
            print(f"Perfil obtenido: {repr(perfil)}")
            print(f"Longitud: {len(perfil)}")
            if perfil != "Administrador(Sistemas)":
                await query.message.reply_text("❌ No tienes permisos para generar el reporte.")
                await show_options(update, context)
                return ASK_OPTIONS
            
            await query.message.reply_text("Generando reporte...")
            path = generar_reporte_excel()
            if not path:
                await query.message.reply_text("No hay datos en el reporte.")
                await show_options(update, context)
                return ASK_OPTIONS
            else:
                with open(path, "rb") as file:
                    await query.message.reply_document(document=file, filename="reporte.xlsx")
                    await query.message.reply_text(
                        "¿Desea continuar con otro proceso?",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Realizar otro proceso", callback_data="again")],
                            [InlineKeyboardButton("🚪 Cerrar sesión", callback_data="End")]
                        ])
                    )
                    return ASK_FINAL
                    return ASK_FINAL
    

#########----------------------------------------------------------------------------------------------------------------------------------------------------------
async def ask_user(update: Update, context: CallbackContext):
    
    user = update.message.text
    context.user_data["user"] = user
    option = context.user_data.get("option")

    if option == "option_2":
        return await handle_change_centro_costo(update, context)
    elif option == "option_3":
        return await handle_add_centro_costo(update, context)


#########-------------------------------------------------------------Validacion perfil para cambiar centro de costo---------------------------------------------------------------------------------------------
async def handle_change_centro_costo(update: Update, context: CallbackContext):
    
    db_connection = conectarsql()
    cursor = db_connection.cursor()

    # Validar perfil
    query_sql = """
    SELECT P.Nombre 
    FROM Users U
    JOIN Perfil P ON U.Cod_Perfil = P.Cod_Perfil
    WHERE U.Usuario = ? AND P.Nombre IN ('Gerente Local', 'Gerente Tienda');
    """
    cursor.execute(query_sql, (context.user_data["user"],))
    result = cursor.fetchone()

    if not result:
        await update.message.reply_text(
            "❌ Acceso denegado. Solo a los usuarios con perfil 'Gerente Local' o 'Gerente Tienda' se les puede realizar esta acción."
        )
        await show_options(update, context)
        return ASK_OPTIONS

    await update.message.reply_text("✅ Acceso concedido: Cambio de centro de costo.")

    # Traer centros de costo
    query_centro_costo = """
    SELECT R.Cod_Tienda, R.Cod_Cadena 
    FROM Restaurante R
    JOIN UserRestaurante UR ON R.Cod_Restaurante = UR.Cod_Restaurante
    JOIN Users U ON UR.Cod_Usuario = U.Cod_Usuario
    WHERE U.Usuario = ?
    """
    cursor.execute(query_centro_costo, (context.user_data["user"],))
    centros_costo = cursor.fetchall()

    # Nombre de usuario
    query_nombre = """
    SELECT Descripcion FROM Users WHERE Usuario = ?
    """
    cursor.execute(query_nombre, (context.user_data["user"],))
    nombre = cursor.fetchone()[0]

    # Perfil del usuario
    query_perfil = """
    SELECT p.Nombre 
    FROM Perfil p
    JOIN Users u ON p.Cod_Perfil = u.Cod_Perfil
    WHERE u.Usuario = ?
    """
    cursor.execute(query_perfil, (context.user_data["user"],))
    perfil = cursor.fetchone()[0]

    if centros_costo:
        if len(centros_costo) == 1:
            # Usuario tiene un solo centro de costo
            cod_tienda, cod_cadena = centros_costo[0]
            context.user_data["cod_tienda_actual"] = cod_tienda
            context.user_data["cod_cadena_actual"] = cod_cadena

            await update.message.reply_text(
                f"El centro de costo actual de {context.user_data['user']} es:\n{cod_tienda}\n"
                f"Nombre del usuario: {nombre}\n"
                f"Perfil: {perfil}"
            )
            await update.message.reply_text("Escribe el centro de costo al que deseas cambiar:")
            return ASK_CENTRO_COSTO

        else:
            # Usuario tiene varios centros de costo
            
            if not(len(centros_costo)>3):
                context.user_data["centros_costo"] = centros_costo

                lista_centro = "\n".join([f"- {cc[0]}" for cc in centros_costo])
                await update.message.reply_text(
                    f"Los centros de costo de {context.user_data['user']} son:\n{lista_centro}\n\n"
                    f"Nombre del usuario: {nombre}\n"
                    f"Perfil: {perfil}"
                )
                await update.message.reply_text("¿Desde qué centro de costo deseas cambiar?")
                return ASK_CENTRO_COSTO_ORIGEN
            else:
                await update.message.reply_text(
                    "❌ El usuario tiene demasiados centros de costo asignados. "
                    "Por favor, contacta al administrador para realizar el cambio."
                )
                await show_options(update, context)
                return ASK_OPTIONS

    else:
        await update.message.reply_text("❌ El usuario no tiene centros de costo asignados.")
        await show_options(update, context)
        return ASK_OPTIONS


#########--------------------------------------------------------Validacion de perfil para añadir centro de costo--------------------------------------------------------------------------------------------------
async def handle_add_centro_costo(update: Update, context: CallbackContext):
    
    db_connection = conectarsql()
    cursor = db_connection.cursor()
    
    query_sql = """
    SELECT P.Nombre 
    FROM Users U
    JOIN Perfil P ON U.Cod_Perfil = P.Cod_Perfil
    WHERE U.Usuario = ? AND P.Nombre IN (
        'Administrador(Sistemas)',
        'Gerente Operaciones',
        'Auditor Local',
        'Auditor Administrador',
        'Gerente Operaciones Nac',
        'Planta Devoluciones y Pedidos',
        'Sistemas Tercer Nivel',
        'Administrador Recetas',
        'CAR Mayores Contables PyG Presupuesto',
        'Gerente Local',
        'Gerente Tienda'
    );
    """
    
    cursor.execute(query_sql, (context.user_data["user"],))
    result = cursor.fetchone()
    
    if result:
        query_nombre = """
        Select Descripcion From Users where usuario = ?
        """
        cursor.execute(query_nombre, (context.user_data["user"],))
        nombre = cursor.fetchone()
        nombre = nombre[0]
        
        query_perfil = """
        SELECT p.Nombre 
        FROM Perfil p
        JOIN users u ON p.Cod_Perfil = u.Cod_Perfil
        WHERE u.Usuario = ?;
        """
        cursor.execute(query_perfil, (context.user_data["user"],))
        perfil = cursor.fetchone()
        perfil = perfil[0]
        context.user_data["perfil"] = perfil
        
        query_registros = """
        SELECT COUNT(*) AS total_registros FROM UserRestaurante UR
        join users u ON UR.Cod_Usuario = u.Cod_Usuario
        where u.Usuario = ?;
        """
        cursor.execute(query_registros, (context.user_data["user"],))
        registros = cursor.fetchone()
        registros = registros[0]
        
        # Validación para Gerente Local y Gerente Tienda
        if perfil.strip() in ("Gerente Local", "Gerente Tienda") and registros >= 2:
            await update.message.reply_text(
                f"⛔ El usuario con perfil '{perfil}' ya tiene {registros} centro(s) de costo registrado.\n"
                "No se permite agregar más centros de costo para este tipo de perfil."
            )
            await show_options(update, context)
            return ASK_OPTIONS
        
        await update.message.reply_text(
            f"El usuario:\n{context.user_data['user']}\n"
            f"De nombre:\n{nombre}\n"
            f"Con perfil de:\n{perfil}\n"
            f"Tiene un total de:\n{registros} centros de costos registrados.\n\n"
            "Acceso concedido, ingrese el código de tienda del nuevo centro de costo:"
        )
        return ASK_COD_TIENDA
    else:
        await update.message.reply_text("El usuario no tiene acceso para esa característica.")
        await show_options(update, context)
        return ASK_OPTIONS

#########----------------------------------------------------------------Confirmacion de nuevo centro de costo------------------------------------------------------------------------------------------
async def recibir_cod_tienda(update: Update, context: CallbackContext):
    cod_tienda = update.message.text.strip()
    context.user_data["cod_tienda"] = cod_tienda
    db_connection = conectarsql()
    cursor = db_connection.cursor()

    # 1) Verificar si el centro ya está asignado al usuario objetivo
    query_sql = """
        SELECT UR.*
        FROM users U
        JOIN UserRestaurante UR ON U.Cod_Usuario = UR.Cod_Usuario
        JOIN Restaurante R ON UR.Cod_Restaurante = R.Cod_Restaurante
        WHERE U.Usuario = ? AND R.Cod_Tienda = ?;
    """
    cursor.execute(query_sql, (context.user_data["user"], cod_tienda))
    result1 = cursor.fetchone()
    if result1:
        await update.message.reply_text("Este centro de costo ya está asignado. Inténtalo nuevamente.")
        return ASK_COD_TIENDA

    # 2) Obtener info de la tienda nueva (Cod_Restaurante, Cod_Cadena) y checar que esté activa
    cursor.execute(
        "SELECT Cod_Restaurante, Cod_Cadena FROM Restaurante WHERE Cod_Tienda = ? AND Estado = 1",
        (cod_tienda,)
    )
    tienda_row = cursor.fetchone()
    if not tienda_row:
        await update.message.reply_text("El centro de costo no está activo o no existe. Inténtalo nuevamente.")
        return ASK_COD_TIENDA

    tienda_cod_restaurante, nuevo_cod_cadena = tienda_row
    print(f"DEBUG -> tienda_cod_restaurante={tienda_cod_restaurante}, nuevo_cod_cadena={nuevo_cod_cadena}")

    # 3) Obtener cod_cadena actual del usuario objetivo (tomamos TOP 1 por si tiene varios; ajusta si necesitas otra lógica)
    actualcod_cadenasql = """
        SELECT TOP 1 r.cod_cadena
        FROM Restaurante r
        JOIN UserRestaurante ur ON r.Cod_Restaurante = ur.Cod_Restaurante 
        JOIN Users u ON ur.Cod_Usuario = u.Cod_Usuario
        WHERE u.Usuario = ?;
    """
    cursor.execute(actualcod_cadenasql, (context.user_data["user"],))
    row = cursor.fetchone()
    actual_cod_cadena = row[0] if row else None
    print(f"DEBUG Actual cod_cadena: {actual_cod_cadena}")

    # 4) Perfil del usuario (normalizado)
    perfil = context.user_data.get("perfil")
    perfil_norm = perfil.strip().lower() if isinstance(perfil, str) else None
    print(f"DEBUG Perfil obtenido: {repr(perfil)} -> normalizado: {perfil_norm}")

    # 5) Validación estricta para Gerente Local / Gerente Tienda
    if perfil_norm in ("gerente local", "gerente tienda"):
        # asegurar enteros y existencia
        try:
            actual_cod_cadena = int(actual_cod_cadena)
            nuevo_cod_cadena = int(nuevo_cod_cadena)
        except (TypeError, ValueError):
            await update.message.reply_text("⛔ No se pudo validar el código de cadena. Intenta nuevamente.")
            return ASK_COD_TIENDA

        pares_permitidos = {(10, 11), (11, 10), (36, 37), (37, 36)}
        cambio_permitido = (
            nuevo_cod_cadena == actual_cod_cadena or
            (actual_cod_cadena, nuevo_cod_cadena) in pares_permitidos
        )

        print(f"DEBUG cambio_permitido={cambio_permitido} (actual={actual_cod_cadena}, nuevo={nuevo_cod_cadena})")

        if not cambio_permitido:
            await update.message.reply_text(
                "⛔ Solo se puede agregar entre centros de la misma cadena, "
                "o entre cadenas KFC y HeladeriasKFC, o entre BaskinRobins y Cinnabon. Intenta nuevamente."
            )
            return ASK_COD_TIENDA  # <-- detiene la ejecución aquí

    # 6) Obtener Cod_Usuario del usuario objetivo
    cursor.execute("SELECT Cod_Usuario FROM Users WHERE Usuario = ?", (context.user_data["user"],))
    usuario_row = cursor.fetchone()
    if not usuario_row:
        await update.message.reply_text("⛔ Usuario objetivo no encontrado en la base de datos.")
        return ASK_COD_TIENDA
    usuario_id = usuario_row[0]

    try:
        # 7) Usuario que realiza la acción (modificador)
        modificador_usuario = context.user_data.get('username') or (update.effective_user.username if update.effective_user else None)
        mod_id = None
        if modificador_usuario:
            cursor.execute("SELECT cod_usuario FROM Users WHERE Usuario = ?", (modificador_usuario,))
            mod_row = cursor.fetchone()
            mod_id = mod_row[0] if mod_row else None

        # 8) Insertar en AuditLog si tenemos un modificador
        if mod_id:
            insert_query2 = """
                INSERT INTO AuditLog (Cod_Restaurante, Cod_Usuario, Accion, Modificador, Fecha_Log) 
                VALUES (?, ?, ?, ?, GETDATE())
            """
            cursor.execute(insert_query2, (tienda_cod_restaurante, usuario_id, "Bot agrego un centro", mod_id))
            db_connection.commit()

        # 9) Insertar el centro de costo
        insert_query = "INSERT INTO UserRestaurante (Cod_Usuario, Cod_Restaurante) VALUES (?, ?)"
        cursor.execute(insert_query, (usuario_id, tienda_cod_restaurante))
        db_connection.commit()

        await update.message.reply_text(
            f"✅ Centro de costo agregado con éxito.\n"
            f"Al usuario {context.user_data['user']} se le agregó el centro de costo: {cod_tienda}"
        )

        await update.message.reply_text(
            "¿Desea continuar con otro proceso?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Realizar otro proceso", callback_data="again")],
                [InlineKeyboardButton("🚪 Cerrar sesión", callback_data="End")]
            ])
        )
        return ASK_FINAL

    except Exception as e:
        db_connection.rollback()
        await update.message.reply_text(f"Error al agregar el centro de costo: {str(e)}.")
        return ASK_COD_TIENDA


#########--------------------------------------------------------------Validacion de centro de costo para el cambio-------------------------------------------------------------------------------------------------
async def handle_centro_costo(update: Update, context: CallbackContext):

    nuevo_centro_costo = update.message.text
    context.user_data["nuevo_centro_costo"] = nuevo_centro_costo

    db_connection = conectarsql()
    cursor = db_connection.cursor()

    query = "SELECT Cod_Cadena, Cod_Restaurante FROM Restaurante WHERE Cod_Tienda = ? and Estado = 1"
    cursor.execute(query, (nuevo_centro_costo,))
    result = cursor.fetchone()

    if not result:
        await update.message.reply_text(
            "El centro de costo no existe o no esta activo. Intenta nuevamente."
        )
        return ASK_CENTRO_COSTO

    nuevo_cod_cadena, nuevo_cod_restaurante = result
    context.user_data["nuevo_cod_cadena"] = nuevo_cod_cadena
    context.user_data["nuevo_cod_restaurante"] = nuevo_cod_restaurante

    if (
    nuevo_cod_cadena != context.user_data["cod_cadena_actual"] and
    not (
        (context.user_data["cod_cadena_actual"] == 10 and nuevo_cod_cadena == 11) or
        (context.user_data["cod_cadena_actual"] == 11 and nuevo_cod_cadena == 10) or
        (context.user_data["cod_cadena_actual"] == 36 and nuevo_cod_cadena == 37) or
        (context.user_data["cod_cadena_actual"] == 37 and nuevo_cod_cadena == 36)
    )
    ):
        await update.message.reply_text(
            "Solo se puede realizar el cambio entre centros de la misma cadena, "
            "o entre cadenas KFC y HeladeriasKFC, o entre BaskinRobins y Cinnabon. Intenta nuevamente."
        )
        return ASK_CENTRO_COSTO

    keyboard = [
        [InlineKeyboardButton("Sí", callback_data="confirm_yes")],
        [InlineKeyboardButton("No", callback_data="confirm_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"¿Desea continuar con el cambio al centro de costo {nuevo_centro_costo}?",
        reply_markup=reply_markup,
    )
    return CONFIRM_CHANGE

async def handle_centro_costo_origen(update: Update, context: CallbackContext):
    centro_origen = update.message.text.strip()
    centros_validos = [cc[0] for cc in context.user_data.get("centros_costo", [])]

    if centro_origen not in centros_validos:
        await update.message.reply_text(
            "El centro de costo ingresado no es válido. Por favor, escribe uno de los siguientes:\n" +
            "\n".join([f"- {cc}" for cc in centros_validos])
        )
        return ASK_CENTRO_COSTO_ORIGEN

    context.user_data["cod_tienda_actual"] = centro_origen

####--------- Obtener cod_cadena del centro actual
    db_connection = conectarsql()
    cursor = db_connection.cursor()
    query = "SELECT Cod_Cadena FROM Restaurante WHERE Cod_Tienda = ?"
    cursor.execute(query, (centro_origen,))
    result = cursor.fetchone()

    if not result:
        await update.message.reply_text("Error al validar el centro de costo actual.")
        return ASK_CENTRO_COSTO_ORIGEN

    context.user_data["cod_cadena_actual"] = result[0]

    await update.message.reply_text("¿A qué centro de costo deseas cambiar?")
    return ASK_CENTRO_COSTO_DESTINO

async def handle_centro_costo_destino(update: Update, context: CallbackContext):
    nuevo_centro_costo = update.message.text.strip()
    context.user_data["nuevo_centro_costo"] = nuevo_centro_costo

    db_connection = conectarsql()
    cursor = db_connection.cursor()

    query = "SELECT Cod_Cadena, Cod_Restaurante FROM Restaurante WHERE Cod_Tienda = ? AND Estado = 1"
    cursor.execute(query, (nuevo_centro_costo,))
    result = cursor.fetchone()

    if not result:
        await update.message.reply_text("El centro de costo no existe o no está activo. Intenta nuevamente.")
        return ASK_CENTRO_COSTO

    nuevo_cod_cadena, nuevo_cod_restaurante = result
    context.user_data["nuevo_cod_cadena"] = nuevo_cod_cadena
    context.user_data["nuevo_cod_restaurante"] = nuevo_cod_restaurante

    cod_cadena_actual = context.user_data["cod_cadena_actual"]

    # Validación de cambio permitido
    if (
    nuevo_cod_cadena != cod_cadena_actual and
    not (
        (cod_cadena_actual == 10 and nuevo_cod_cadena == 11) or
        (cod_cadena_actual == 11 and nuevo_cod_cadena == 10) or
        (cod_cadena_actual == 36 and nuevo_cod_cadena == 37) or
        (cod_cadena_actual == 37 and nuevo_cod_cadena == 36)
    )
    ):
        await update.message.reply_text(
            "Solo se puede realizar el cambio entre centros de la misma cadena, "
            "o entre cadenas 10 y 11, o entre 36 y 37. Intenta nuevamente."
        )
        return ASK_CENTRO_COSTO

    # Confirmación
    keyboard = [
        [InlineKeyboardButton("Sí", callback_data="confirm_yes")],
        [InlineKeyboardButton("No", callback_data="confirm_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"¿Desea continuar con el cambio al centro de costo {nuevo_centro_costo}?",
        reply_markup=reply_markup,
    )
    return CONFIRM_CHANGE


#########-----------------------------------------------------------Confirmacion cambio centro de costo----------------------------------------------------------------------------------------------
async def confirm_change(update: Update, context: CallbackContext):
    
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("Cambio cancelado. Intenta nuevamente.")
        return ASK_CENTRO_COSTO

    if query.data == "confirm_yes":
        db_connection = conectarsql()
        cursor = db_connection.cursor()

        try:
            codusuario = """select cod_usuario from users where usuario = ?"""
            cursor.execute(codusuario, (context.user_data["user"]))
            cod = cursor.fetchone()
            cod = cod[0]
            
            select_query = "SELECT Cod_Restaurante FROM Restaurante WHERE  Cod_Tienda = ?"
            cursor.execute(select_query, (context.user_data["cod_tienda_actual"],))
            cod_actual = cursor.fetchone()
            cod_actual = cod_actual[0] 
            
            delete_query = "DELETE FROM UserRestaurante WHERE Cod_Usuario = ? and Cod_Restaurante = ?"
            cursor.execute(delete_query, (cod,cod_actual))

            insert_query = """
            INSERT INTO UserRestaurante (Cod_Usuario, Cod_Restaurante) 
            VALUES (?, ?)
            """
            cursor.execute(
                insert_query,
                (
                   cod, 
                    context.user_data["nuevo_cod_restaurante"],
                ),
            )
            db_connection.commit()
            
            codUsuario = """Select cod_usuario From Users where Usuario= ?"""
            cursor.execute(codUsuario,(context.user_data['username']))
            UsuarioM = cursor.fetchone()
            
            if UsuarioM: 
                UsuarioM = UsuarioM[0] 

                insert_query2 = """
                INSERT INTO AuditLog (Cod_Restaurante, Cod_Usuario, Accion, Modificador, Fecha_Log) 
                VALUES (?, ?, ?, ?, GETDATE())
                """
                cursor.execute(
                    insert_query2,
                    (
                        context.user_data["nuevo_cod_restaurante"],
                        cod, 
                        "Bot realizo cambio centro",
                        UsuarioM  
                    ),

                )
                
                centro = """Select cod_tienda from Restaurante where cod_restaurante = ?"""
                cursor.execute(centro,context.user_data["nuevo_cod_restaurante"])
                centro = cursor.fetchone()
                centro = centro[0]
                
                db_connection.commit()

            await query.edit_message_text(f"✅ Cambio de centro de costo realizado con éxito. \nEl usuario {context.user_data['user']} se lo cambió al centro de costo: {centro}")

            await query.message.reply_text(
                "¿Desea continuar con otro proceso?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Realizar otro proceso", callback_data="again")],
                    [InlineKeyboardButton("🚪 Cerrar sesión", callback_data="End")]
                ])
            )
            return ASK_FINAL

        except Exception as e:
            db_connection.rollback() 
            await query.edit_message_text(f"⚠️ Ocurrió un error: {str(e)}. Intenta nuevamente.")
            return ASK_CENTRO_COSTO
      
#########--------------------------------------------------------------inicio de creacion de nuevo usuario------------------------------------------------------------------------------------------

async def change_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pide la cédula para validar si es un usuario nuevo."""
    await update.message.reply_text("Ingrese el número de cédula del nuevo usuario:")
    return CEDULA

#########--------------------------------------------------------------Creacion nuevo usuario------------------------------------------------------------------------------------------

async def start_crear_usuario(update: Update, context: CallbackContext):
    await update.message.reply_text("Ingrese la cédula del nuevo usuario:")
    return CEDULA

async def pedir_nombres(update: Update, context: CallbackContext):
    cedula = update.message.text
    context.user_data["cedula"] = cedula

    if not validacion(cedula):
        await update.message.reply_text("Cédula no válida. Inténtalo de nuevo.")
        return CEDULA

    await update.message.reply_text("Ingrese los nombres del nuevo usuario:")
    return NOMBRES

async def pedir_apellidos(update: Update, context: CallbackContext):
    nombres = update.message.text
    context.user_data["nombres"] = nombres

    await update.message.reply_text("Ingrese los apellidos del nuevo usuario:")
    return APELLIDOS

async def crear_usuario(update: Update, context: CallbackContext):
    apellidos = update.message.text
    context.user_data["apellidos"] = apellidos

    cedula = context.user_data["cedula"]
    nombres = context.user_data["nombres"]

    resultado = new_user(cedula, nombres, apellidos)

    if resultado: 
        await update.message.reply_text("✅ Usuario creado exitosamente.")
        await update.message.reply_text(f"👤 Nombre de usuario generado: *{resultado}*", parse_mode="Markdown")
        await update.message.reply_text("Usuario con perfil Gerente Local.")
        await ask_final(update, context)
        
        auditlog(context.user_data.get('username'), resultado, 1, None)  # 1 para crear
        
        return ASK_FINAL
    else:
        await update.message.reply_text("❌ Error al crear el usuario. Inténtalo nuevamente.")
        return CEDULA
        
#########--------------------------------------------------------Tiempo de espera----------------------------------------------------------------------------------------------       
async def timeout_handler(update: Update, context: CallbackContext):
   
    if update.callback_query:
        await update.callback_query.message.reply_text("⏳ Tiempo finalizado, inicie sesión de nuevo.")
        db_connection = conectarsql()
        if db_connection:
            db_connection.close()
    else:
        await update.message.reply_text("⏳ Tiempo finalizado, inicie sesión de nuevo.")
        db_connection = conectarsql()
        if db_connection:
            db_connection.close()
    
    return ConversationHandler.END
#########--------------------------------------------------------Reseteo de clave----------------------------------------------------------------------------------------------       
async def reset_password(update: Update, context: CallbackContext):
    
    username = update.message.text
    
    if not username:
        await update.message.reply_text("❗No se ha proporcionado un usuario válido./nPor favor, ingresa de nuevo el usuario:")
        await reset_password(update, context)
        return RESET_CLAVE

    resultado, mensaje = clave_reset(username)
    await update.message.reply_text(mensaje)
    if resultado:
        auditlog( context.user_data.get('username'), username, 2, None)  # 2 para resetear clave
        await ask_final(update, context)
        return ASK_FINAL
    else:
        await show_options(update, context)
        return ASK_OPTIONS


#########---------------------------------------------------Confirmacion final---------------------------------------------------------------------------------------------------
async def ask_final(update: Update, context: CallbackContext):
    db_connection = conectarsql()
    keyboard = [
        [InlineKeyboardButton("🔄 Realizar otro proceso", callback_data="again")],
        [InlineKeyboardButton("🚪 Cerrar sesión", callback_data="End")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        option = query.data

        if option == "again":
            await show_options(update, context)
            return ASK_OPTIONS
        elif option == "End":
            await query.message.reply_text("Sesión cerrada. Hasta pronto.")
            if db_connection:
                db_connection.close()
            return ConversationHandler.END

    await update.message.reply_text("¿Desea continuar con otro proceso?", reply_markup=reply_markup)
    return ASK_FINAL

#########--------------------------------------------------------Reporte en excel----------------------------------------------------------------------------------------------

async def reporte(update: Update, context: CallbackContext):
    path = generar_reporte_excel()
    if not path:
        await update.message.reply_text("No hay datos en el reporte.")
    else:
        with open(path, "rb") as file:
            await update.message.reply_document(document=file, filename="reporte.xlsx")

#########--------------------------------------------------------Cancelar----------------------------------------------------------------------------------------------
async def cancel(update: Update, context: CallbackContext):
    db_connection = conectarsql()
    if db_connection:
            db_connection.close()
    await update.message.reply_text("Sesión cancelada.")
    return ConversationHandler.END

#########------------------------------------------------------------------------------------------------------------------------------------------------------
def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(lambda app: app.job_queue.start()).build()

    conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states = {
        ASK_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cedula)],
        ASK_CEDULA: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_credentials)],
        ASK_OPTIONS: [CallbackQueryHandler(handle_option_click)],
        ASK_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_user)],
        ASK_COD_TIENDA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_cod_tienda)],
        ASK_CENTRO_COSTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_centro_costo)],
        ASK_CENTRO_COSTO_ORIGEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_centro_costo_origen)],
        ASK_CENTRO_COSTO_DESTINO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_centro_costo_destino)],
        CEDULA: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_nombres)],
        NOMBRES: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_apellidos)],
        APELLIDOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, crear_usuario)],
        REPORTE: [CommandHandler("reporte", reporte)],
        ASK_FINAL: [
            CallbackQueryHandler(ask_final, pattern="^(again|End)$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_final)
        ],
        RESET_CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_password)],
        CONFIRM_CHANGE: [CallbackQueryHandler(confirm_change, pattern="^confirm_")],
        ConversationHandler.TIMEOUT: [
            MessageHandler(filters.ALL, timeout_handler),
            CallbackQueryHandler(timeout_handler)
        ],
    },  

    fallbacks=[CommandHandler("cancel", cancel)],
    conversation_timeout=INACTIVITY_TIMEOUT,
    
)

    app.add_handler(conv_handler)

    print("El bot está corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()