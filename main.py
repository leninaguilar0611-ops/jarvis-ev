import os
import re
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, request, jsonify

app = Flask(__name__)
# Permite acentos y ñ en el JSON (mejor lectura para el TTS)
app.json.ensure_ascii = False

# ---------- Configuración (se cambia en Render > Environment) ----------
ZONA_HORARIA = os.environ.get("TZ_LOCAL", "America/Mexico_City")
NOMBRE_ASISTENTE = os.environ.get("NOMBRE_ASISTENTE", "Ev")
INICIO = time.time()  # para calcular el tiempo encendido


# ---------- Utilidades ----------
def contiene_palabra(texto, palabra):
    # Busca la palabra completa, así "hora" no coincide con "ahora"
    return re.search(rf"\b{re.escape(palabra)}\b", texto) is not None


# ---------- Comandos por VOZ (texto en "mensaje") ----------
def cmd_hora():
    ahora = datetime.now(ZoneInfo(ZONA_HORARIA))
    return f"Son las {ahora.strftime('%H:%M')}."


def cmd_estado():
    minutos = int((time.time() - INICIO) // 60)
    return f"Todos los sistemas operativos. Llevo {minutos} minutos en línea."


def cmd_saludo():
    return f"A sus órdenes. Soy {NOMBRE_ASISTENTE}. ¿En qué puedo ayudarle?"


def cmd_ayuda():
    return ("Puedo decirle la hora, el estado de los sistemas, lanzar un dado "
            "o una moneda, y saludar. Un doble aplauso activa el modo de inicio.")


def cmd_dado():
    return f"Salió un {random.randint(1, 6)}."


def cmd_moneda():
    return f"Salió {random.choice(['cara', 'cruz'])}."


# Palabras clave -> función. Aquí agregarás nuevos comandos de voz.
COMANDOS_VOZ = {
    ("hora", "qué hora"): cmd_hora,
    ("estado", "sistemas", "status"): cmd_estado,
    ("hola", "buenos días", "buenas"): cmd_saludo,
    ("ayuda", "qué puedes hacer"): cmd_ayuda,
    ("dado", "dados"): cmd_dado,
    ("moneda", "cara o cruz"): cmd_moneda,
}


def procesar_voz(mensaje: str) -> str:
    texto = mensaje.lower().strip()
    # Quitamos el nombre del asistente, solo cuando es la palabra completa
    texto = re.sub(rf"\b{re.escape(NOMBRE_ASISTENTE.lower())}\b", "", texto)
    for palabras, funcion in COMANDOS_VOZ.items():
        if any(contiene_palabra(texto, p) for p in palabras):
            return funcion()
    return "No reconozco ese comando todavía."


# ---------- Eventos NO verbales (aplausos, etc.) ----------
def evento_doble_aplauso():
    return "Doble aplauso detectado. Modo de inicio activado. Bienvenido de nuevo."


def evento_aplauso():
    return "Aplauso detectado."


# Nombre del evento -> función. Aquí agregarás nuevos gestos.
EVENTOS = {
    "doble_aplauso": evento_doble_aplauso,
    "aplauso": evento_aplauso,
}


def procesar_evento(evento: str) -> str:
    funcion = EVENTOS.get(evento.lower().strip())
    return funcion() if funcion else "Evento desconocido."


# ---------- Rutas ----------
@app.route("/", methods=["GET"])
def inicio():
    # Sirve para comprobar desde el navegador que el servidor vive
    return f"{NOMBRE_ASISTENTE} en línea."


@app.route("/comando", methods=["POST"])
def comando():
    datos = request.get_json(silent=True) or {}

    # 1) Si llega un evento (aplausos, etc.), tiene prioridad
    evento = datos.get("evento", "").strip()
    if evento:
        return jsonify({"respuesta": procesar_evento(evento)})

    # 2) Si no, procesamos el texto de voz
    mensaje = datos.get("mensaje", "").strip()
    if not mensaje:
        return jsonify({"respuesta": "No recibí ningún mensaje ni evento."}), 400
    return jsonify({"respuesta": procesar_voz(mensaje)})


# Solo para pruebas locales; en Render lo ejecuta Gunicorn
if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
