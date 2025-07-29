import ccxt
import time
import traceback
import json
import os
from datetime import datetime
import requests
import streamlit as st
from queue import Queue
from threading import Thread
import re
import logging
from tenacity import retry, stop_after_attempt, wait_fixed  # Para reintentos automáticos
import pandas as pd
import plotly.express as px

# === CONFIGURACIÓN DE LOGGING ===
logging.basicConfig(filename='bot_trading.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# === CONFIGURACIÓN SEGURA DE CLAVES API ===
api_key = os.getenv("BINANCE_API_KEY")
secret = os.getenv("BINANCE_SECRET")

if not api_key or not secret:
    raise ValueError("Claves API no configuradas. Asegúrate de configurar BINANCE_API_KEY y BINANCE_SECRET como variables de entorno.")

# === CARGA DE CONFIGURACIÓN ===
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    raise FileNotFoundError("El archivo 'config.json' no se encuentra. Asegúrate de que exista.")
except json.JSONDecodeError:
    raise ValueError("El archivo 'config.json' tiene errores de formato JSON. Verifica su contenido.")

# === VALIDACIÓN DE CONFIGURACIÓN ===
def validar_configuracion(config):
    required_keys = ['symbol', 'sl_ratio', 'tp_ratio', 'porcentaje_operacion', 'apalancamiento', 'min_tamano', 'max_tamano']
    for key in required_keys:
        if key not in config or config[key] is None:
            raise ValueError(f"La clave de configuración '{key}' no está configurada o es inválida.")
    if not (0 < config['sl_ratio'] < 1):
        raise ValueError("El sl_ratio debe ser un valor entre 0 y 1.")
    if not (0 < config['tp_ratio'] < 1):
        raise ValueError("El tp_ratio debe ser un valor entre 0 y 1.")

validar_configuracion(config)

# === CONFIGURACIÓN API BINANCE ===
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True
    }
})

if config.get('sandbox_mode', False):
    exchange.set_sandbox_mode(True)
    print("Modo Sandbox activado: Las operaciones no serán reales.")

# === CONTROLADOR DE VELOCIDAD DE LA API ===
class ControladorAPI:
    def __init__(self, limite=10):
        self.cola = Queue()
        self.limite = limite
        self.trabajador = Thread(target=self._procesar_cola)
        self.trabajador.daemon = True
        self.trabajador.start()

    def _procesar_cola(self):
        while True:
            funcion, args, kwargs = self.cola.get()
            try:
                time.sleep(1 / self.limite)
                funcion(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error en solicitud API: {e}")
            self.cola.task_done()

    def agregar_solicitud(self, funcion, *args, **kwargs):
        self.cola.put((funcion, args, kwargs))

controlador_api = ControladorAPI(limite=10)

# === FUNCIONES AUXILIARES ===
def enviar_notificacion_telegram(mensaje, nivel="info"):
    niveles = {"info": "ℹ️", "error": "❌", "success": "✅"}
    prefijo = niveles.get(nivel, "ℹ️")
    mensaje = f"{prefijo} {mensaje}"
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not telegram_bot_token or not telegram_chat_id:
        print("Telegram no configurado. Notificación no enviada.")
        return
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    data = {'chat_id': telegram_chat_id, 'text': mensaje}
    controlador_api.agregar_solicitud(requests.post, url, json=data)

def enviar_notificacion_slack(mensaje):
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        print("Slack no configurado. Notificación no enviada.")
        return
    data = {"text": mensaje}
    controlador_api.agregar_solicitud(requests.post, slack_webhook_url, json=data)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def obtener_balance_futuros():
    try:
        balance = exchange.fetch_balance({'type': 'future'})
        return balance['total']['USDT']
    except Exception as e:
        logging.error(f"Error al obtener el balance: {e}")
        raise

def log_orden(tipo, symbol, direccion, cantidad, precio, opciones):
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] Orden {tipo.upper()} enviada: {direccion.upper()} {cantidad} {symbol} a {precio}. Opciones: {opciones}"
    print(log_message)
    enviar_notificacion_telegram(log_message)
    enviar_notificacion_slack(log_message)

def obtener_precio_para_orden(simbolo, direccion, porcentaje_limite):
    try:
        ticker = exchange.fetch_ticker(simbolo)
        if direccion == 'buy':
            return ticker['bid'] * (1 - porcentaje_limite)
        elif direccion == 'sell':
            return ticker['ask'] * (1 + porcentaje_limite)
    except Exception as e:
        logging.error(f"Error al obtener el precio límite: {e}")
        return None

def enviar_orden_limite(simbolo, direccion, cantidad, precio):
    try:
        orden = exchange.create_order(
            symbol=simbolo,
            type='limit',
            side=direccion,
            amount=cantidad,
            price=precio
        )
        log_orden("límite", simbolo, direccion, cantidad, precio, orden)
        return orden
    except Exception as e:
        logging.error(f"Error al enviar la orden límite: {e}")
        return None

def obtener_precio_para_cierre(simbolo, direccion):
    try:
        ticker = exchange.fetch_ticker(simbolo)
        if direccion == 'sell':
            return ticker['bid'] * 0.99
        elif direccion == 'buy':
            return ticker['ask'] * 1.01
    except Exception as e:
        logging.error(f"Error al calcular el precio para cierre: {e}")
        return None

def cerrar_posicion_con_limite(simbolo):
    try:
        posiciones = exchange.fapiPrivate_get_positionrisk()
        posicion = next((p for p in posiciones if p['symbol'] == simbolo.replace('/', '') and float(p['positionAmt']) != 0), None)

        if posicion:
            cantidad = abs(float(posicion['positionAmt']))
            direccion = 'sell' if float(posicion['positionAmt']) > 0 else 'buy'
            precio_limite = obtener_precio_para_cierre(simbolo, direccion)

            if precio_limite is None:
                print(f"No se pudo calcular el precio límite para cerrar la posición en {simbolo}.")
                return

            orden = exchange.create_order(
                symbol=simbolo,
                type='limit',
                side=direccion,
                amount=cantidad,
                price=precio_limite
            )
            log_orden("cierre_límite", simbolo, direccion, cantidad, precio_limite, orden)
            print(f"Posición cerrada con orden límite para {simbolo}: {orden}")
        else:
            print(f"No hay posiciones abiertas para {simbolo}.")
    except Exception as e:
        logging.error(f"Error al cerrar posición con límite: {e}")

def obtener_step_size(simbolo):
    try:
        mercados = exchange.fetch_markets()
        for mercado in mercados:
            if mercado['symbol'] == simbolo:
                return float(mercado['info']['filters'][2]['stepSize'])
        raise ValueError(f"Step size para {simbolo} no encontrado.")
    except Exception as e:
        logging.error(f"Error al obtener step size para {simbolo}: {e}")
        return 0.01  # Valor por defecto si falla

def calcular_tamano_operacion(balance, porcentaje, apalancamiento, min_tamano, max_tamano, step_size):
    tamano = balance * (porcentaje / 100) * apalancamiento
    tamano = max(min_tamano, min(tamano, max_tamano))
    tamano = round(tamano / step_size) * step_size
    return tamano

def procesar_senal_tv(mensaje):
    try:
        accion_match = re.search(r"orden (\w+)", mensaje)
        ticker_match = re.search(r"en ([A-Z0-9/]+)", mensaje)
        posicion_match = re.search(r"nueva posición estratégica es ([\-0-9.]+)", mensaje)

        if not accion_match or not ticker_match or not posicion_match:
            logging.error("No se pudieron extraer todos los datos necesarios del mensaje.")
            return None

        accion = accion_match.group(1).lower()
        ticker = ticker_match.group(1)
        posicion_final = float(posicion_match.group(1))

        return {"accion": accion, "ticker": ticker, "posicion_final": posicion_final}
    except Exception as e:
        logging.error(f"Error al procesar la señal: {e}")
        return None

def ejecutar_senal_tv(mensaje):
    senal = procesar_senal_tv(mensaje)
    if not senal:
        return

    accion = senal["accion"]
    ticker = senal["ticker"]
    posicion_final = senal["posicion_final"]

    print(f"Procesando señal: Acción: {accion}, Ticker: {ticker}, Posición estratégica: {posicion_final}")

    try:
        posiciones = exchange.fapiPrivate_get_positionrisk()
        posicion_abierta = next((p for p in posiciones if p['symbol'] == ticker.replace('/', '') and float(p['positionAmt']) != 0), None)

        if posicion_abierta:
            lado_actual = 'buy' if float(posicion_abierta['positionAmt']) > 0 else 'sell'
            if lado_actual != accion:
                print(f"Posición contraria detectada en {ticker}. Cerrando posición abierta antes de continuar.")
                cerrar_posicion_con_limite(ticker)

        if posicion_final == 0:
            print(f"Cerrando posición en {ticker} debido a señal con posición estratégica = 0.")
            cerrar_posicion_con_limite(ticker)
        else:
            balance = obtener_balance_futuros()
            step_size = obtener_step_size(ticker)
            tamano = calcular_tamano_operacion(
                balance,
                config['porcentaje_operacion'],
                config['apalancamiento'],
                config['min_tamano'],
                config['max_tamano'],
                step_size
            )

            precio_limite = obtener_precio_para_orden(ticker, accion, 0.001)
            if precio_limite is None:
                print("No se pudo calcular el precio límite. Operación cancelada.")
                return

            enviar_orden_limite(ticker, accion, tamano, precio_limite)
    except Exception as e:
        logging.error(f"Error al ejecutar la señal: {e}")
        traceback.print_exc()

def mostrar_dashboard():
    st.title("Dashboard de Trading")
    try:
        balance = obtener_balance_futuros()
        st.metric("Balance Actual (USDT)", balance)

        posiciones = exchange.fapiPrivate_get_positionrisk()
        df_posiciones = pd.DataFrame(posiciones)
        st.write("Posiciones Actuales:")
        st.dataframe(df_posiciones[["symbol", "positionAmt", "entryPrice"]])

        fig = px.pie(df_posiciones, values='positionAmt', names='symbol', title="Distribución de Posiciones")
        st.plotly_chart(fig)
    except Exception as e:
        st.error(f"Error al mostrar el dashboard: {e}")

# === EJECUCIÓN PRINCIPAL ===
if __name__ == "__main__":
    mostrar_dashboard()