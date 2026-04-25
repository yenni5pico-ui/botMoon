import telebot
from telebot import types
import sqlite3
import schedule
import time
import datetime
import threading
import os
# --- AGREGA ESTO AQUÍ ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "BotMoon está operando"

def run():
    app.run(host='0.0.0.0', port=10000) # Render suele usar el puerto 10000 por defecto

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 1. CONFIGURACIÓN SEGURA ---
import os # Esta librería es la que lee las llaves ocultas

TOKEN = os.getenv('TOKEN_TELEGRAM')
MI_CHAT_ID = os.getenv('MI_CHAT_ID')

bot = telebot.TeleBot(TOKEN)
ID_STICKER_DESPEDIDA = "CAACAgIAAxkBAAEX4GVmN_Yf0Z8zG3Vl8y3_v9k7fQf9fAACQgMAAs-7BQAB4_l_8g_p9cQ0BA"


# --- 2. BASE DE DATOS ---
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
    try:
        cursor.execute("ALTER TABLE tareas ADD COLUMN estado INTEGER DEFAULT 0")
    except:
        pass
    conn.commit()
    conn.close()


# --- 3. SISTEMA DE ALERTAS ---
def verificar_alertas():
    hoy_dt = datetime.date.today()
    hoy_str = hoy_dt.strftime('%Y-%m-%d')
    tres_dias_str = (hoy_dt + datetime.timedelta(days=3)).strftime('%Y-%m-%d')

    conn = sqlite3.connect('tareas.db')
    cursor = conn.cursor()

    # Notificación para HOY
    cursor.execute("SELECT materia, descripcion FROM tareas WHERE fecha = ? AND estado = 0", (hoy_str,))
    hoy = cursor.fetchall()
    for t in hoy:
        bot.send_message(MI_CHAT_ID, f"🚨 **ENTREGA PARA HOY**\n\n📖 {t[0]}\n📝 {t[1]}", parse_mode="Markdown")

    # Notificación 3 días antes
    cursor.execute("SELECT materia, descripcion FROM tareas WHERE fecha = ? AND estado = 0", (tres_dias_str,))
    antes = cursor.fetchall()
    for t in antes:
        bot.send_message(MI_CHAT_ID, f"⏰ **FALTAN 3 DÍAS**\n\n📖 {t[0]}\n📝 {t[1]}", parse_mode="Markdown")
    conn.close()


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


def teclado_confirmar():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('✅ Sí, guardar'), types.KeyboardButton('❌ Cancelar'))
    return markup


def teclado_si_no():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('Sí'), types.KeyboardButton('No'))
    return markup


# --- 5. MANEJADORES DE MENSAJES ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    lema = "🤯 *¡Basta de caos académico!*\n\nTu semestre está a un clic de dejar de ser un laberinto de estrés. Estoy listo para ayudarte a organizar tus tareas."
    bot.send_message(message.chat.id, lema, parse_mode="Markdown", reply_markup=menu_principal())


@bot.message_handler(func=lambda message: True)
def manejar_mensajes(message):
    texto = message.text.lower()
    if "pendientes" in texto or "ver" in texto:
        listar_tareas(message)
    elif "nueva" in texto or "tarea" in texto:
        msg = bot.reply_to(message, "📌 Dime: **Materia - Tema**", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, proceso_fecha)
    else:
        bot.reply_to(message, "Usa los botones 👇", reply_markup=menu_principal())


# --- 6. REGISTRO DE TAREAS ---
def proceso_fecha(message):
    materia_tema = message.text
    msg = bot.reply_to(message, "🗓️ Fecha de entrega (AAAA-MM-DD):")
    bot.register_next_step_handler(msg, lambda m: confirmar_registro(m, materia_tema))


def confirmar_registro(message, materia_tema):
    fecha = message.text
    resumen = f"⚠️ **¿Confirmas esta tarea?**\n\n📝 {materia_tema}\n📅 {fecha}"
    msg = bot.send_message(message.chat.id, resumen, parse_mode="Markdown", reply_markup=teclado_confirmar())
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
        bot.reply_to(message, "🚀 ¡Guardada!", reply_markup=menu_principal())
    else:
        bot.reply_to(message, "❌ Registro cancelado.", reply_markup=menu_principal())


# --- 7. LISTAR Y FINALIZAR (EL BARRIDO Y CIERRE) ---
def listar_tareas(message):
    hoy = datetime.date.today().strftime('%Y-%m-%d')
    conn = sqlite3.connect('tareas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, materia, descripcion, fecha FROM tareas WHERE estado = 0 ORDER BY fecha ASC")
    tareas = cursor.fetchall()
    conn.close()

    if not tareas:
        msg = bot.send_message(message.chat.id, "☕ ¡Todo al día! ¿Deseas agendar una nueva tarea?",
                               reply_markup=teclado_si_no())
        bot.register_next_step_handler(msg, manejar_decision_final)
    else:
        bot.send_message(message.chat.id, "📅 **ESTO ES LO QUE TIENES PENDIENTE:**")
        for t in tareas:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Marcar Finalizada", callback_data=f"done_{t[0]}"))
            texto = f"📖 **{t[1]}**\n📝 {t[2]}\n🗓️ Entrega: {t[3]}"
            bot.send_message(message.chat.id, texto, parse_mode="Markdown", reply_markup=markup)

        time.sleep(1)
        msg = bot.send_message(message.chat.id, "✨ ¿Tienes otra tarea que agendar?", reply_markup=teclado_si_no())
        bot.register_next_step_handler(msg, manejar_decision_final)


def manejar_decision_final(message):
    texto = message.text.lower()
    if texto == "sí" or texto == "si":
        msg = bot.send_message(message.chat.id, "📌 Dime: **Materia - Tema**", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, proceso_fecha)
    else:
        bot.send_message(message.chat.id, "👋 ¡Entendido! Éxito en tus estudios.",
                         reply_markup=menu_principal())
        try:
            bot.send_sticker(message.chat.id, ID_STICKER_DESPEDIDA)
        except:
            pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('done_'))
def callback_finalizar(call):
    id_tarea = call.data.split('_')[1]
    conn = sqlite3.connect('tareas.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE tareas SET estado = 1 WHERE id = ?", (id_tarea,))
    conn.commit()
    conn.close()

    bot.edit_message_text("✨ **¡Tarea completada y archivada!** ✅",
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id)
    bot.answer_callback_query(call.id, "¡Bravo!")


# --- 8. EJECUCIÓN ---
if __name__ == "__main__":
    iniciar_db()

    # --- AGREGA ESTO AQUÍ ---
    keep_alive()
    # ------------------------

    threading.Thread(target=hilo_horario, daemon=True).start()
    print("🚀 BOT ACTIVO")

    while True:
        try:
            bot.infinity_polling(timeout=10)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)