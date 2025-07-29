from flask import Flask, request, jsonify
from trading_bot import ejecutar_senal_tv

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)

    mensaje = data.get('message') or data.get('alert_message') or ''
    if not mensaje:
        return jsonify({'error': 'No se encontró mensaje en el webhook'}), 400

    ejecutar_senal_tv(mensaje)
    return jsonify({'status': 'Señal recibida y ejecutada correctamente'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)