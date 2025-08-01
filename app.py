from flask import Flask, request, jsonify
import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
from byte import encrypt_api, Encrypt_ID

app = Flask(__name__)

@app.route("/visit_profile", methods=["GET"])
def visit_profile():
    player_id = request.args.get("player_id")
    token = request.args.get("token")

    if not player_id or not token:
        return jsonify({"error": "player_id and token are required in query params"}), 400

    try:
        player_id = int(player_id)
    except ValueError:
        return jsonify({"error": "player_id must be an integer"}), 400

    try:
        encrypted_id = Encrypt_ID(player_id)
        encrypted_api = encrypt_api(f"08{encrypted_id}1007")
        TARGET = bytes.fromhex(encrypted_api)
    except Exception as e:
        return jsonify({"error": f"Encryption failed: {str(e)}"}), 500

    url = "https://clientbp.common.ggbluefox.com/GetPlayerPersonalShow"
    headers = {
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)',
        'Connection': 'Keep-Alive',
        'Expect': '100-continue',
        'Authorization': f'Bearer {token}',
        'X-Unity-Version': '2018.4.11f1',
        'X-GA': 'v1 1',
        'ReleaseVersion': 'OB50',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    try:
        with httpx.Client(verify=False) as client:
            response = client.post(url, headers=headers, data=TARGET)

        if response.status_code == 200:
            return jsonify({
                "status": "success",
                "message": f"[{player_id}] ✅ زيارة ناجحة"
            }), 200
        else:
            return jsonify({
                "status": "failed",
                "message": f"❌ فشل في الزيارة - الكود {response.status_code}"
            }), response.status_code

    except httpx.RequestError as e:
        return jsonify({
            "status": "error",
            "message": f"Request error: {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
