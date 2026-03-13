# render_callback.py
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from integrations.mercadolivre.auth import exchange_code_for_token, generate_auth_link

# Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)
CORS(app)

# --------------------- CALLBACK ML ---------------------
@app.route("/ml/callback", methods=["GET"])
def ml_callback():
    code = request.args.get("code")
    cliente_id = request.args.get("state")  # pegando state

    if not code:
        logging.warning("Código não recebido no callback ML")
        return "<h3>Erro: código não recebido</h3>", 400
    if not cliente_id:
        logging.warning("cliente_id não informado no callback ML")
        return "<h3>Erro: cliente_id não informado</h3>", 400

    try:
        data = exchange_code_for_token(int(cliente_id), code)
        logging.info(f"Cliente {cliente_id} autorizado com sucesso")
        return f"<h3>Cliente {cliente_id} autorizado com sucesso!</h3>", 200
    except Exception as e:
        logging.error(f"Erro no callback ML para cliente {cliente_id}: {e}")
        return f"<h3>Erro ao processar callback: {e}</h3>", 500

# --------------------- WEBHOOK NOTIFICAÇÕES ---------------------
@app.route("/ml/notifications", methods=["POST"])
def ml_notifications():
    data = request.json
    if not data:
        logging.warning("Webhook ML recebido sem payload")
        return jsonify({"status": "error", "message": "Sem payload"}), 400
    logging.info(f"Webhook ML recebido: {data}")
    # Aqui você pode processar o webhook (ex: atualizar estoque no DB)
    return jsonify({"status": "ok"}), 200

# --------------------- GERAR LINK ML ---------------------
@app.route("/ml/generate_link/<int:cliente_id>", methods=["GET"])
def ml_generate_link(cliente_id):
    base_link = generate_auth_link(cliente_id)
    # Adiciona state para receber de volta no callback
    if "?" in base_link:
        link = f"{base_link}&state={cliente_id}"
    else:
        link = f"{base_link}?state={cliente_id}"
    logging.info(f"Link ML gerado para cliente {cliente_id}: {link}")
    return jsonify({"link": link})

# --------------------- EXEC ---------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Rodando Flask ML callback na porta {port}")
    app.run(host="0.0.0.0", port=port)