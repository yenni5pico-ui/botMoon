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

# Diccionario para la memoria de la charla
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


# --- FLUJO INICIAL ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    contador_charla[message.chat.id] = 0
    enviar_escribiendo(message.chat.id, 1)
    msg = bot.send_message(message.chat.id,
                           "¡Hola! Qué alegría saludarte. 😊\nSoy **botMoon**. Para empezar, ¿cómo te llamas?",
                           parse_mode="Markdown")
    bot.register_next_step_handler(msg, proceso_nombre)


def proceso_nombre(message):
    nombre = message.text
    enviar_escribiendo(message.chat.id, 1)
    msg = bot.send_message(message.chat.id,
                           f"¡Mucho gusto, {nombre}! ✨ Cuéntame, ¿cómo vas con tus tareas de la universidad? ¿Estás muy full o vas al día?")
    bot.register_next_step_handler(msg, analizar_estado_tareas)


# --- LÓGICA DE CONVERSACIÓN E INTERRUPCIONES ---

def analizar_estado_tareas(message):
    respuesta = message.text.lower()
    chat_id = message.chat.id

    # NUEVO: Si dice gracias aquí, saltamos al flujo de despedida
    if any(p in respuesta for p in ["gracias", "gracia", "agradecido"]):
        despedida_amable(message)
        return

    enviar_escribiendo(chat_id, 1)
    palabras_clave = ["bien", "mal", "full", "estres", "nada", "poco", "mucho", "dia", "clase", "tarea", "uni"]

    if any(p in respuesta for p in palabras_clave):
        if any(p in respuesta for p in ["mal", "mucho", "full", "estres"]):
            reaccion = "¡Uy! Entiendo, a veces las entregas se amontonan. 😰"
        else:
            reaccion = "¡Qué éxito! Me alegra que lleves ese control. 👏"

        msg = bot.send_message(chat_id, f"{reaccion}\n\n¿Qué te parece si empezamos agendando una tarea ahora mismo?")
        bot.register_next_step_handler(msg, proceso_materia_directo)
    else:
        seguir_corriente(message)


def seguir_corriente(message):
    chat_id = message.chat.id
    respuesta = message.text.lower()

    # NUEVO: Si dice gracias mientras le seguimos la corriente, despedimos
    if any(p in respuesta for p in ["gracias", "gracia", "agradecido"]):
        despedida_amable(message)
        return

    if chat_id not in contador_charla:
        contador_charla[chat_id] = 0

    contador_charla[chat_id] += 1
    enviar_escribiendo(chat_id, 2)

    respuestas = [
        f"¡Vaya! No esperaba eso de '{message.text}'. Cuéntame más. 😊",
        "Interesante... ¿y qué más me puedes decir de eso? 🧐",
        "Entiendo, me dejas pensando. ¿Y entonces?"
    ]

    if contador_charla[chat_id] < 3:
        msg = bot.send_message(chat_id, random.choice(respuestas))
        bot.register_next_step_handler(msg, seguir_corriente)
    else:
        contador_charla[chat_id] = 0
        msg = bot.send_message(chat_id,
                               "Jajaja, ¡qué buena charla! Pero para que no se nos pase el tiempo... ⏳\n\n**¿Quieres que sigamos con el registro de tu tarea o prefieres que lo realicemos más tarde?**",
                               reply_markup=teclado_ahora_despues(), parse_mode="Markdown")
        bot.register_next_step_handler(msg, manejar_decision_agenda)


def manejar_decision_agenda(message):
    texto = message.text.lower()
    if any(p in texto for p in ["ahora", "sí", "dale", "va"]):
        proceso_materia_directo(message)
    else:
        bot.send_message(message.chat.id,
                         "¡Entendido! No hay problema. Aquí estaré en el menú para cuando decidas poner orden. ¡Vuelve pronto! ✨",
                         reply_markup=menu_principal())


def proceso_materia_directo(message):
    enviar_escribiendo(message.chat.id, 1)
    msg = bot.send_message(message.chat.id,
                           "🚀 ¡Perfecto! Vamos a organizarnos.\n📌 Dime: **¿Qué materia o tema quieres anotar?**",
                           reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, proceso_fecha)


# --- FLUJO DE AGENDADO ---

def proceso_fecha(message):
    materia_tema = message.text
    enviar_escribiendo(message.chat.id, 1)
    msg = bot.send_message(message.chat.id,
                           f"Vale, anoto: *{materia_tema}*.\n\n¿Para qué fecha es? (Dime el día o la fecha)",
                           parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: confirmar_registro(m, materia_tema))


def confirmar_registro(message, materia_tema):
    fecha_usuario = message.text
    enviar_escribiendo(message.chat.id, 1)
    resumen = f"A ver si entendí bien... 🤔\n\n📝 Tarea: **{materia_tema}**\n📅 Fecha: **{fecha_usuario}**\n\n¿Lo guardamos así?"
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('✅ ¡Perfecto!'), types.KeyboardButton('🔄 Corregir'))
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
        msg = bot.send_message(message.chat.id, "📝 Dime de nuevo, ¿qué materia y tema quieres agendar?",
                               reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, proceso_fecha)


# --- MANEJO DE DESPEDIDA (DEBE IR ANTES DEL MENÚ GENERAL) ---

@bot.message_handler(
    func=lambda message: any(p in message.text.lower() for p in ["gracias", "gracia", "agradecido", "graci"]))
def despedida_amable(message):
    enviar_escribiendo(message.chat.id, 1)
    respuestas = [
        "¡De nada! Fue un placer ayudarte. 😊 ¡Vuelve pronto!",
        "¡A la orden! Éxito con tus tareas. ✨ ¡Vuelve pronto!",
        "¡No hay de qué! Aquí estaré cuando me necesites. 🌙 ¡Vuelve pronto!"
    ]
    bot.send_message(message.chat.id, random.choice(respuestas), reply_markup=menu_principal())


# --- MENÚ GENERAL ---

@bot.message_handler(func=lambda message: True)
def manejar_menu_general(message):
    texto = message.text.lower()
    if "ver" in texto or "tareas" in texto:
        listar_tareas(message)
    elif "nueva" in texto or "agendar" in texto:
        proceso_materia_directo(message)
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


@bot.callback_query_handler(func=lambda call: call.data.startswith('done_'))
def finalizar_tarea(call):
    tarea_id = call.data.split('_')[1]
    conn = sqlite3.connect('tareas.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE tareas SET estado = 1 WHERE id = ?", (tarea_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "¡Tarea completada! 🎉")
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="✅ Esta tarea ya fue realizada.")


# --- INICIO ---
if __name__ == "__main__":
    iniciar_db()
    keep_alive()
    print("🚀 BOTMOON ACTIVO")
    bot.infinity_polling()