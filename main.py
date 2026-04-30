import telebot
from telebot import types
import sqlite3
import time
import datetime
import os
import random
from flask import Flask
from threading import Thread

# --- CONFIGURACIÓN FLASK PARA RENDER ---
app = Flask('')


@app.route('/')
def home():
    return "BotMoon está operando"


def run():
    app.run(host='0.0.0.0', port=10000)


def keep_alive():
    t = Thread(target=run)
    t.start()


# --- CONFIGURACIÓN DEL BOT ---
TOKEN = os.getenv('TOKEN_TELEGRAM')
bot = telebot.TeleBot(TOKEN)

# Diccionario para que el bot "recuerde" cuántas cosas fuera de contexto le han dicho
contador_charla = {}


# --- UTILIDADES ---
def enviar_escribiendo(chat_id, segundos=1.5):
    bot.send_chat_action(chat_id, 'typing')
    time.sleep(segundos)


def iniciar_db():
    conn = sqlite3.connect('tareas.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS tareas
                      (
                          id
                          INTEGER
                          PRIMARY
                          KEY
                          AUTOINCREMENT,
                          materia
                          TEXT,
                          descripcion
                          TEXT,
                          fecha
                          TEXT,
                          estado
                          INTEGER
                          DEFAULT
                          0
                      )''')
    conn.commit()
    conn.close()


# --- TECLADOS ---
def menu_principal():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('📅 Ver tareas'), types.KeyboardButton('📝 Nueva Tarea'))
    return markup


def teclado_ahora_despues():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('Sí, agendar ahora'), types.KeyboardButton('Lo realizo más tarde'))
    return markup


# --- LÓGICA DE CONVERSACIÓN ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # ELIMINA EL /START PARA LIMPIAR LA INTERFAZ
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    contador_charla[message.chat.id] = 0  # Reset contador
    enviar_escribiendo(message.chat.id, 1)
    saludos = ["¡Hola! Qué alegría saludarte. 😊", "¡Hola, hola! Qué bueno verte por aquí. 👋"]
    msg = bot.send_message(message.chat.id,
                           f"{random.choice(saludos)}\nSoy **botMoon**. Para empezar, ¿cómo te llamas?",
                           parse_mode="Markdown")
    bot.register_next_step_handler(msg, proceso_nombre)


def proceso_nombre(message):
    nombre = message.text
    enviar_escribiendo(message.chat.id, 1)
    msg = bot.send_message(message.chat.id,
                           f"¡Mucho gusto, {nombre}! ✨ Cuéntame, ¿cómo vas con tus tareas de la universidad? ¿Estás muy full o vas al día?")
    bot.register_next_step_handler(msg, analizar_estado_tareas)


def seguir_corriente(message):
    chat_id = message.chat.id
    if chat_id not in contador_charla:
        contador_charla[chat_id] = 0

    contador_charla[chat_id] += 1
    enviar_escribiendo(chat_id, 2)

    respuestas_curiosas = [
        f"¡Vaya! No me esperaba eso de '{message.text}'. Cuéntame más, me dio curiosidad. 😊",
        "Interesante... nunca lo había pensado así. ¿Y qué más? 🧐",
        "Entiendo perfectamente. Es un tema curioso, ¿no crees?"
    ]

    if contador_charla[chat_id] < 3:
        msg = bot.send_message(chat_id, random.choice(respuestas_curiosas))
        bot.register_next_step_handler(msg, seguir_corriente)
    else:
        # A LA TERCERA VEZ, EL BOT RETOMA EL CONTROL
        contador_charla[chat_id] = 0
        msg = bot.send_message(
            chat_id,
            "Jajaja, ¡qué buena charla! Pero antes de que se me olvide... ⏳\n\n"
            "**¿Quieres que sigamos con el registro de tu tarea o prefieres hacerlo más tarde?**",
            reply_markup=teclado_ahora_despues(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, manejar_decision_agenda)


# --- BUSCA Y REEMPLAZA ESTAS FUNCIONES EN TU CÓDIGO ---

def analizar_estado_tareas(message):
    respuesta = message.text.lower()
    chat_id = message.chat.id
    enviar_escribiendo(chat_id, 1.5)

    # Palabras que indican que SÍ está hablando de la universidad/tareas
    palabras_clave = ["bien", "mal", "full", "estres", "nada", "poco", "mucho", "dia", "clase", "tarea", "uni",
                      "estudiando"]

    if any(p in respuesta for p in palabras_clave):
        # FLUJO NORMAL: Si responde sobre sus tareas, vamos directo a agendar
        if any(p in respuesta for p in ["mal", "mucho", "full", "estres"]):
            reaccion = "¡Uy! Entiendo, a veces las entregas se amontonan. 😰"
        else:
            reaccion = "¡Qué éxito! Me alegra que lleves ese control. 👏"

        msg = bot.send_message(chat_id, f"{reaccion}\n\n¿Qué te parece si empezamos agendando una tarea ahora mismo?")
        bot.register_next_step_handler(msg, proceso_materia_directo)  # Va directo al grano
    else:
        # FLUJO DE DESVÍO: Si el prof dice otra cosa, activamos el contador
        seguir_corriente(message)


def seguir_corriente(message):
    chat_id = message.chat.id
    if chat_id not in contador_charla:
        contador_charla[chat_id] = 0

    contador_charla[chat_id] += 1
    enviar_escribiendo(chat_id, 2)

    # Respuestas para cuando el bot "sigue la corriente"
    respuestas_curiosas = [
        f"¡Vaya! No me esperaba eso de '{message.text}'. Cuéntame más. 😊",
        "Qué tema tan interesante... ¿Y qué más pasó con eso? 🧐",
        "Entiendo perfectamente, me dejas pensando. ¿Y entonces?"
    ]

    if contador_charla[chat_id] < 3:
        # Sigue la corriente hasta 3 veces
        msg = bot.send_message(chat_id, random.choice(respuestas_curiosas))
        bot.register_next_step_handler(msg, seguir_corriente)
    else:
        # EL RESCATE: Aquí es donde ofrece hacerlo más tarde porque ya se desviaron mucho
        contador_charla[chat_id] = 0
        msg = bot.send_message(
            chat_id,
            "Jajaja, ¡qué buena charla! Pero para que no se nos pase el tiempo... ⏳\n\n"
            "**¿Quieres que retomemos y agendemos tu tarea ahora o prefieres que lo realicemos más tarde?**",
            reply_markup=teclado_ahora_despues(),
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, manejar_decision_agenda)


def proceso_materia_directo(message):
    # Esta función se llama cuando el flujo es normal y directo
    enviar_escribiendo(message.chat.id, 1)
    msg = bot.send_message(message.chat.id,
                           "🚀 ¡Perfecto! Vamos a organizarnos.\n📌 Dime: **¿Qué materia o tema quieres anotar?**",
                           reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, proceso_fecha)


def manejar_decision_agenda(message):
    texto = message.text.lower()
    if "ahora" in texto or "sí" in texto or "vale" in texto:
        enviar_escribiendo(message.chat.id, 1)
        msg = bot.send_message(message.chat.id,
                               "¡Perfecto! Vamos a organizarnos. 🚀\n📌 Dime: **¿Qué tarea quieres anotar?** (Materia y tema)",
                               reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
        bot.register_next_step_handler(msg, proceso_fecha)
    else:
        enviar_escribiendo(message.chat.id, 1)
        bot.send_message(message.chat.id, "¡Entendido! Aquí estaré en el menú principal para cuando lo necesites. ✨",
                         reply_markup=menu_principal())


# --- FLUJO DE AGENDADO FLEXIBLE ---

def proceso_fecha(message):
    materia_tema = message.text
    enviar_escribiendo(message.chat.id, 1)
    msg = bot.send_message(message.chat.id,
                           f"Vale, anoto: *{materia_tema}*.\n\n¿Para qué fecha es? (Dime el día o la fecha)",
                           parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: confirmar_registro(m, materia_tema))


def confirmar_registro(message, materia_tema):
    fecha_usuario = message.text
    enviar_escribiendo(message.chat.id, 1.5)
    resumen = (
        f"A ver si entendí bien... 🤔\n\n"
        f"📝 Tarea: **{materia_tema}**\n"
        f"📅 Fecha: **{fecha_usuario}**\n\n"
        f"¿Lo guardamos así o prefieres corregir algo?"
    )
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('✅ ¡Así está perfecto!'), types.KeyboardButton('🔄 Corregir algo'))
    msg = bot.send_message(message.chat.id, resumen, parse_mode="Markdown", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: guardado_final(m, materia_tema, fecha_usuario))


def guardado_final(message, materia_tema, fecha):
    if "perfecto" in message.text.lower() or "sí" in message.text.lower():
        conn = sqlite3.connect('tareas.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tareas (materia, descripcion, fecha, estado) VALUES (?, ?, ?, 0)",
                       (materia_tema, "Fecha: " + fecha, str(datetime.date.today())))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "🚀 ¡Listo! Tarea guardada. ¡A por ello!", reply_markup=menu_principal())
    else:
        msg = bot.send_message(message.chat.id, "¡Oído al tambor! 📝 Dime de nuevo, ¿qué tarea quieres agendar?",
                               reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, proceso_fecha)


# --- MENÚ GENERAL ---
@bot.message_handler(func=lambda message: True)
def manejar_menu_general(message):
    texto = message.text.lower()
    if "ver" in texto or "tareas" in texto:
        listar_tareas(message)
    elif "nueva" in texto or "agendar" in texto:
        msg = bot.send_message(message.chat.id, "📌 Dime: **Materia - Tema**", reply_markup=types.ReplyKeyboardRemove(),
                               parse_mode="Markdown")
        bot.register_next_step_handler(msg, proceso_fecha)
    else:
        bot.reply_to(message, "Usa los botones para que sea más fácil, o dime 'Nueva Tarea'. 👇",
                     reply_markup=menu_principal())


def listar_tareas(message):
    conn = sqlite3.connect('tareas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, materia, descripcion, fecha FROM tareas WHERE estado = 0 ORDER BY id DESC")
    tareas = cursor.fetchall()
    conn.close()

    if not tareas:
        bot.send_message(message.chat.id, "☕ ¡No tienes nada pendiente! Qué relax.", reply_markup=menu_principal())
    else:
        bot.send_message(message.chat.id, "📅 **Pendientes:**", parse_mode="Markdown")
        for t in tareas:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Finalizada", callback_data=f"done_{t[0]}"))
            bot.send_message(message.chat.id, f"📖 **{t[1]}**\n{t[2]}", parse_mode="Markdown", reply_markup=markup)


# --- INICIO ---
if __name__ == "__main__":
    iniciar_db()
    keep_alive()
    print("🚀 BOTMOON ACTIVO: Modo Humano con memoria de charla activado")
    bot.infinity_polling()