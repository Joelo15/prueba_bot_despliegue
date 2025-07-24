def validacion(cedula: str) -> bool:
    # Debe tener exactamente 10 dígitos numéricos
    if len(cedula) != 10 or not cedula.isdigit():
        return False

    # Validar que el primer dígito (provincia) esté entre 01 y 24
    provincia = int(cedula[:2])
    if provincia < 1 or provincia > 24:
        return False

    # El tercer dígito debe ser menor que 6 (personas naturales)
    if int(cedula[2]) >= 6:
        return False

    # Aplicar el algoritmo de validación (módulo 10)
    digitos = [int(d) for d in cedula]
    suma = 0

    for i in range(9):
        if i % 2 == 0:  # posiciones impares
            digito = digitos[i] * 2
            if digito > 9:
                digito -= 9
        else:  # posiciones pares
            digito = digitos[i]
        suma += digito

    verificador = (10 - (suma % 10)) % 10
    return verificador == digitos[9]
