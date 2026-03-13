# render_callback.py
from flask import Flask, request
from integrations.mercadolivre.auth import exchange_code_for_token

app = Flask(__name__)

@app.route("/ml/callback")
def ml_callback():
    code = request.args.get("code")
    cliente_id = request.args.get("cliente_id")  # opcional: identifica o cliente
    if not code:
        return "❌ Código não recebido", 400

    exchange_code_for_token(cliente_id, code)
    return "✅ Cliente autorizado e tokens atualizados!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)