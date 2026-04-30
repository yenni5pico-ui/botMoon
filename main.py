import telebot
from telebot import types
import sqlite3
import schedule
import time
import datetime
import threading
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


# --- CONFIGURACIÓN SEGURA ---
TOKEN = os.getenv('TOKEN_TELEGRAM')
MI_CHAT_ID = os.getenv('MI_CHAT_ID')
bot = telebot.TeleBot(TOKEN)
ID_STICKER_DESPEDIDA = "CAACAgIAAxkBAAEX4GVmN_Yf0Z8zG3Vl8y3_v9k7fQf9fAACQgMAAs-7BQAB4_l_8g_p9cQ0BA"


# --- UTILIDADES PARA "HUMANIZAR" ---
def enviar_escribiendo(chat_id, segundos=1.5):
    """Simula que el bot está escribiendo"""
    bot.send_chat_action(chat_id, 'typing')
    time.sleep(segundos)


# --- 2. BASE DE DATOS (Mantenida igual) ---
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


# --- 3. SISTEMA DE ALERTAS (Mantenida igual) ---
def verificar_alertas():
    # ... (Tu código original de alertas)
    pass


def hilo_horario():
    schedule.every(4).hours.do(verificar_alertas)
    verificar_alertas()
    while True:
        schedule.run_pending()
        time.sleep(60)


# --- 4. TECLADOS ---
def menu_principal():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('📅 Ver tareas pendientes'), types.KeyboardButton('📝 Nueva Tarea'))
    return markup


def teclado_si_no():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('Sí, por favor'), types.KeyboardButton('No, gracias'))
    return markup


# --- 5. MANEJADORES DE MENSAJES (MODIFICADOS) ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    enviar_escribiendo(message.chat.id)
    saludos = ["¡Hola! Qué alegría saludarte. 😊", "¡Hola, hola! Qué bueno verte por aquí. 👋"]
    bienvenida = f"{random.choice(saludos)}\nSoy **botMoon**. Para empezar, ¿cómo te llamas? Me encantaría conocerte."
    msg = bot.send_message(message.chat.id, bienvenida, parse_mode="Markdown")
    bot.register_next_step_handler(msg, proceso_nombre)


def proceso_nombre(message):
    nombre = message.text
    enviar_escribiendo(message.chat.id, 2)
    preguntas = [
        f"¡Mucho gusto, {nombre}! ✨ Cuéntame, ¿cómo vas con tus tareas pendientes? ¿Vas al día o tienes mucho acumulado?",
        f"¡Qué lindo nombre, {nombre}! 😊 ¿Cómo te trata la universidad? ¿Tienes muchos deberes pendientes?"
    ]
    msg = bot.send_message(message.chat.id, random.choice(preguntas))
    bot.register_next_step_handler(msg, analizar_estado_tareas)


def analizar_estado_tareas(message):
    respuesta = message.text.lower()
    enviar_escribiendo(message.chat.id, 2)

    if any(p in respuesta for p in ["mal", "mucho", "full", "colapsado", "estresado"]):
        reaccion = "¡Uy! Entiendo perfectamente, a veces las entregas se amontonan. 😰"
    elif any(p in respuesta for p in ["bien", "al día", "tranquilo", "poquito"]):
        reaccion = "¡Qué éxito! Vas por excelente camino. 👏"
    else:
        reaccion = "Ya veo. Siempre es bueno mantener el orden para que nada se nos escape. 🧐"

    msg = bot.send_message(
        message.chat.id,
        f"{reaccion}\n\n¿Te gustaría que te ayude a agendar tus tareas para llevar un control? 📋",
        reply_markup=teclado_si_no()
    )
    bot.register_next_step_handler(msg, manejar_decision_inicial)


def manejar_decision_inicial(message):
    if "sí" in message.text.lower() or "si" in message.text.lower():
        enviar_escribiendo(message.chat.id, 1)
        msg = bot.send_message(message.chat.id, "¡Perfecto! Vamos a organizarnos. 🚀\n📌 Dime: **Materia - Tema**",
                               parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, proceso_fecha)
    else:
        bot.send_message(message.chat.id, "Entendido. Aquí estaré cuando me necesites. ¡Mucho éxito! ✨",
                         reply_markup=menu_principal())


# --- 6. REGISTRO Y LISTADO (Integrados con tu lógica original) ---

@bot.message_handler(func=lambda message: True)
def manejar_mensajes_menu(message):
    texto = message.text.lower()
    if "pendientes" in texto or "ver" in texto:
        listar_tareas(message)
    elif "nueva" in texto or "tarea" in texto:
        enviar_escribiendo(message.chat.id, 1)
        msg = bot.send_message(message.chat.id, "📌 Dime: **Materia - Tema**", reply_markup=types.ReplyKeyboardRemove(),
                               parse_mode="Markdown")
        bot.register_next_step_handler(msg, proceso_fecha)
    else:
        bot.reply_to(message, "Usa los botones de abajo para que podamos trabajar mejor. 👇",
                     reply_markup=menu_principal())


def proceso_fecha(message):
    materia_tema = message.text
    enviar_escribiendo(message.chat.id, 1)
    msg = bot.send_message(message.chat.id, "🗓️ ¿Para qué fecha es la entrega? (Usa el formato AAAA-MM-DD):")
    bot.register_next_step_handler(msg, lambda m: confirmar_registro(m, materia_tema))


def confirmar_registro(message, materia_tema):
    fecha = message.text
    enviar_escribiendo(message.chat.id, 1.5)
    resumen = f"⚠️ **¿Confirmas que guarde esta tarea?**\n\n📖 {materia_tema}\n📅 {fecha}"
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('✅ Sí, guardar'), types.KeyboardButton('❌ Cancelar'))
    msg = bot.send_message(message.chat.id, resumen, parse_mode="Markdown", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: guardado_final(m, materia_tema, fecha))


def guardado_final(message, materia_tema, fecha):
    if message.text == '✅ Sí, guardar':
        enviar_escribiendo(message.chat.id, 1)
        # ... (Tu lógica de guardado en SQL se mantiene igual)
        bot.send_message(message.chat.id, "🚀 ¡Listo! Tarea guardada con éxito. Ya puedes relajarte un poco.",
                         reply_markup=menu_principal())
    else:
        bot.send_message(message.chat.id, "❌ No te preocupes, registro cancelado.", reply_markup=menu_principal())


def listar_tareas(message):
    # ... (Tu lógica original de listar_tareas con InlineButtons se mantiene igual)
    # Solo agregué un 'enviar_escribiendo' al inicio
    enviar_escribiendo(message.chat.id, 1.5)
    # Lógica de listar...
    pass


# --- 8. EJECUCIÓN (Mantenida igual) ---
if __name__ == "__main__":
    iniciar_db()
    keep_alive()
    threading.Thread(target=hilo_horario, daemon=True).start()
    print("🚀 BOTMOON ACTIVO Y MÁS HUMANO")
    bot.infinity_polling()