# render_callback.py
import os
import logging
from flask import Flask, request, jsonify
from integrations.mercadolivre.auth import exchange_code_for_token

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

# --------------------- REDIRECT URI AUTOMÁTICO ---------------------
@app.route("/ml/callback", methods=["GET"])
def ml_callback():
    """
    Callback para o Mercado Livre.
    Recebe 'code' e 'cliente_id' na URL, troca pelo access_token e refresh_token
    e atualiza o banco de dados.
    """
    code = request.args.get("code")
    cliente_id = request.args.get("cliente_id")

    if not code:
        logging.warning("Código não recebido no callback ML")
        return jsonify({"status": "error", "message": "Código não recebido"}), 400

    if not cliente_id:
        logging.warning("cliente_id não informado no callback ML")
        return jsonify({"status": "error", "message": "cliente_id não informado"}), 400

    try:
        data = exchange_code_for_token(int(cliente_id), code)
        logging.info(f"Cliente {cliente_id} autorizado com sucesso")
        return jsonify({
            "status": "success",
            "message": "Cliente autorizado e tokens atualizados",
            "data": data
        }), 200
    except Exception as e:
        logging.error(f"Erro ao processar callback ML para cliente {cliente_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --------------------- WEBHOOK DE NOTIFICAÇÕES ---------------------
@app.route("/ml/notifications", methods=["POST"])
def ml_notifications():
    """
    Recebe webhooks do Mercado Livre.
    Ex: atualização de estoque ou preço.
    """
    data = request.json
    if not data:
        logging.warning("Webhook ML recebido sem payload")
        return jsonify({"status": "error", "message": "Sem payload"}), 400

    logging.info(f"Webhook ML recebido: {data}")
    # Aqui você pode processar o webhook, ex: atualizar estoque no DB
    return jsonify({"status": "ok"}), 200

# --------------------- LINK AUTOMÁTICO PARA CLIENTE ---------------------
@app.route("/ml/generate_link/<int:cliente_id>", methods=["GET"])
def ml_generate_link(cliente_id):
    """
    Gera o link de autorização ML com cliente_id embutido.
    Esse link deve ser aberto pelo usuário para autorizar o app.
    """
    from integrations.mercadolivre.auth import generate_auth_link
    base_link = generate_auth_link(cliente_id)
    # Adiciona cliente_id na query string do redirect
    if "?" in base_link:
        link = f"{base_link}&cliente_id={cliente_id}"
    else:
        link = f"{base_link}?cliente_id={cliente_id}"
    logging.info(f"Link ML gerado para cliente {cliente_id}: {link}")
    return jsonify({"link": link})

# --------------------- EXEC ---------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Rodando Flask ML callback na porta {port}")
    app.run(host="0.0.0.0", port=port)