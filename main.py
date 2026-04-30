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


# --- BASE DE DATOS ---
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
    markup.add(types.KeyboardButton('📅 Ver tareas pendientes'), types.KeyboardButton('📝 Nueva Tarea'))
    return markup


def teclado_ahora_despues():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('Sí, agendar ahora'), types.KeyboardButton('Lo realizo más tarde'))
    return markup


# --- MANEJADORES DE MENSAJES (MÁS HUMANOS Y DINÁMICOS) ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # 1. OCULTAR EL /START: Borra el comando del profesor para que el chat se vea limpio
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        print(f"No se pudo borrar el start: {e}")

    enviar_escribiendo(message.chat.id, 1)
    saludos = ["¡Hola! Qué alegría saludarte. 😊", "¡Hola, hola! Qué bueno verte por aquí. 👋",
               "¡Hola! Soy botMoon, un gusto saludarte."]
    bienvenida = f"{random.choice(saludos)}\nPara empezar, ¿podrías decirme tu nombre? Me encantaría saber con quién hablo."
    msg = bot.send_message(message.chat.id, bienvenida)
    bot.register_next_step_handler(msg, proceso_nombre)


def proceso_nombre(message):
    nombre = message.text
    enviar_escribiendo(message.chat.id, 1.5)

    # Si el nombre es muy raro o corto, preguntamos qué quiso decir
    if len(nombre) < 2:
        msg = bot.reply_to(message, "¿Perdona? No te entendí bien... ¿Ese es tu nombre o qué quisiste decir? 😅")
        bot.register_next_step_handler(msg, proceso_nombre)
        return

    preguntas = [
        f"¡Mucho gusto, {nombre}! ✨ Cuéntame, ¿cómo vas con tus tareas pendientes? ¿Te sientes al día o tienes mucho acumulado?",
        f"¡Qué lindo nombre, {nombre}! 😊 ¿Cómo te ha tratado la universidad estos días? ¿Mucha carga de tareas?"
    ]
    msg = bot.send_message(message.chat.id, random.choice(preguntas))
    bot.register_next_step_handler(msg, analizar_estado_tareas)


def analizar_estado_tareas(message):
    respuesta = message.text.lower()
    enviar_escribiendo(message.chat.id, 2)

    # INTERFAZ DE CAPTURA: Si el prof dice algo fuera de contexto
    palabras_clave = ["bien", "mal", "full", "estres", "nada", "poco", "mucho", "dia", "clase", "tarea"]
    if not any(palabra in respuesta for palabra in palabras_clave):
        msg = bot.reply_to(message, f"Vaya, me perdí un poco... ¿Qué quisiste decir con '{message.text}'? 🤔")
        bot.register_next_step_handler(msg, retomar_hilo_tareas)
        return

    if any(p in respuesta for p in ["mal", "mucho", "full", "colapsado", "estres"]):
        reaccion = "¡Uy! Entiendo perfectamente, a veces las entregas se amontonan de forma estresante. 😰"
    elif any(p in respuesta for p in ["bien", "al día", "tranquilo", "poc"]):
        reaccion = "¡Qué éxito! Me alegra que lleves ese control. 👏"
    else:
        reaccion = "Entiendo. Siempre es un reto mantenerse al día con todo. 🧐"

    ofrecer_agenda(message, reaccion)


def retomar_hilo_tareas(message):
    enviar_escribiendo(message.chat.id, 1)
    bot.send_message(message.chat.id, "¡Ah, ya entiendo! Gracias por explicarme. 😊")
    ofrecer_agenda(message, "Volviendo a lo nuestro...")


def ofrecer_agenda(message, reaccion):
    enviar_escribiendo(message.chat.id, 1.5)
    msg = bot.send_message(
        message.chat.id,
        f"{reaccion}\n\n¿Te gustaría que te ayude a **agendar una tarea ahora** para llevar el control, o prefieres **realizarlo más tarde**? ✨",
        reply_markup=teclado_ahora_despues(),
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, manejar_decision_agenda)


def manejar_decision_agenda(message):
    texto = message.text.lower()
    if "ahora" in texto or "sí" in texto:
        enviar_escribiendo(message.chat.id, 1)
        msg = bot.send_message(message.chat.id, "¡Perfecto! Vamos a organizarnos. 🚀\n📌 Dime: **Materia - Tema**",
                               reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
        bot.register_next_step_handler(msg, proceso_fecha)
    else:
        enviar_escribiendo(message.chat.id, 1)
        bot.send_message(message.chat.id,
                         "¡Entendido! No hay problema. Aquí estaré en el menú principal para cuando decidas poner orden. ¡Mucho éxito! ✨",
                         reply_markup=menu_principal())


# --- REGISTRO DE TAREAS (Tu lógica original mejorada) ---

def proceso_fecha(message):
    materia_tema = message.text
    enviar_escribiendo(message.chat.id, 1)
    msg = bot.send_message(message.chat.id, "🗓️ ¿Para qué fecha es la entrega? (Formato: AAAA-MM-DD):")
    bot.register_next_step_handler(msg, lambda m: confirmar_registro(m, materia_tema))


def confirmar_registro(message, materia_tema):
    fecha = message.text
    enviar_escribiendo(message.chat.id, 1)
    resumen = f"⚠️ **¿Confirmas esta tarea?**\n\n📝 {materia_tema}\n📅 {fecha}"
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('✅ Sí, guardar'), types.KeyboardButton('❌ Cancelar'))
    msg = bot.send_message(message.chat.id, resumen, parse_mode="Markdown", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: guardado_final(m, materia_tema, fecha))


def guardado_final(message, materia_tema, fecha):
    if message.text == '✅ Sí, guardar':
        partes = materia_tema.split('-')
        materia = partes[0].strip()
        desc = partes[1].strip() if len(partes) > 1 else "General"

        conn = sqlite3.connect('tareas.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tareas (materia, descripcion, fecha, estado) VALUES (?, ?, ?, 0)",
                       (materia, desc, fecha))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "🚀 ¡Tarea guardada! Ya puedes respirar un poco más tranquilo.",
                         reply_markup=menu_principal())
    else:
        bot.send_message(message.chat.id, "❌ Registro cancelado. Volvamos al inicio.", reply_markup=menu_principal())


# --- LISTAR TAREAS (Mantenido) ---
@bot.message_handler(func=lambda message: True)
def manejar_menu_general(message):
    texto = message.text.lower()
    if "pendientes" in texto or "ver" in texto:
        listar_tareas(message)
    elif "nueva" in texto or "tarea" in texto:
        msg = bot.send_message(message.chat.id, "📌 Dime: **Materia - Tema**", reply_markup=types.ReplyKeyboardRemove(),
                               parse_mode="Markdown")
        bot.register_next_step_handler(msg, proceso_fecha)
    else:
        bot.reply_to(message, "Usa los botones de abajo para navegar, ¡es más fácil! 👇", reply_markup=menu_principal())


def listar_tareas(message):
    conn = sqlite3.connect('tareas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, materia, descripcion, fecha FROM tareas WHERE estado = 0 ORDER BY fecha ASC")
    tareas = cursor.fetchall()
    conn.close()

    if not tareas:
        bot.send_message(message.chat.id, "☕ ¡Felicidades! No tienes nada pendiente. ¿Quieres agendar algo nuevo?",
                         reply_markup=menu_principal())
    else:
        bot.send_message(message.chat.id, "📅 **Esto es lo que tienes pendiente:**", parse_mode="Markdown")
        for t in tareas:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Finalizada", callback_data=f"done_{t[0]}"))
            texto = f"📖 **{t[1]}**\n📝 {t[2]}\n🗓️ {t[3]}"
            bot.send_message(message.chat.id, texto, parse_mode="Markdown", reply_markup=markup)


# --- EJECUCIÓN ---
if __name__ == "__main__":
    iniciar_db()
    keep_alive()
    print("🚀 BOTMOON ACTIVO: Start oculto y modo humano activado")
    bot.infinity_polling()