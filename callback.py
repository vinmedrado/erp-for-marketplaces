# render_callback.py
import os
import logging
from flask import Flask, request, jsonify
from integrations.mercadolivre.auth import exchange_code_for_token

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

@app.route("/ml/callback", methods=["GET"])
def ml_callback():
    """
    Callback para o Mercado Livre.
    Recebe 'code' e 'cliente_id', troca pelo access_token e refresh_token
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
        return jsonify({"status": "success", "message": "Cliente autorizado e tokens atualizados", "data": data}), 200
    except Exception as e:
        logging.error(f"Erro ao processar callback ML para cliente {cliente_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Rodando Flask ML callback na porta {port}")
    app.run(host="0.0.0.0", port=port)