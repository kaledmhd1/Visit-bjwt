from flask import Flask, request, jsonify import httpx from Crypto.Cipher import AES from Crypto.Util.Padding import pad import base64

app = Flask(name)

x = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "0a", "0b", "0c", "0d", "0e", "0f"] dec = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "0a", "0b", "0c", "0d", "0e", "0f"]

KEY = b'Yg&tc%DEuh6%Zc^8' IV = b'67H@uysZx8e&h9Lp'

def encrypt_api(plain_text): cipher = AES.new(KEY, AES.MODE_CBC, IV) ct_bytes = cipher.encrypt(pad(bytes.fromhex(plain_text), AES.block_size)) return ct_bytes.hex()

def Encrypt_ID(ID): final_result = "" x = ID while x > 0: mod = x % 128 result = hex(mod)[2:].zfill(2) final_result = result + final_result x //= 128 return final_result

@app.route("/visit_profile", methods=["GET"]) def visit_profile(): player_id = request.args.get("player_id") token = request.args.get("token")

if not player_id or not token: return jsonify({"error": "player_id and token are required in query params"}), 400 try: player_id = int(player_id) except ValueError: return jsonify({"error": "player_id must be an integer"}), 400 encrypted_id = Encrypt_ID(player_id) encrypted_api = encrypt_api(f"08{encrypted_id}1007") TARGET = bytes.fromhex(encrypted_api) url = "https://clientbp.common.ggbluefox.com/GetPlayerPersonalShow" headers = { 'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)', 'Connection': 'Keep-Alive', 'Expect': '100-continue', 'Authorization': f'Bearer {token}', 'X-Unity-Version': '2018.4.11f1', 'X-GA': 'v1 1', 'ReleaseVersion': 'OB50', 'Content-Type': 'application/x-www-form-urlencoded', } try: with httpx.Client(verify=False) as client: response = client.post(url, headers=headers, data=TARGET) if response.status_code == 200: return jsonify({"status": "success", "message": f"[{player_id}] GOOD VISIT✅"}), 200 else: return jsonify({"status": "failed", "message": f"Request failed with status {response.status_code}"}), response.status_code except httpx.RequestError as e: return jsonify({"status": "error", "message": str(e)}), 500 

if name == "main": app.run(debug=True, host="0.0.0.0", port=5000)

        with httpx.Client(verify=False) as client:
            response = client.post(url, headers=headers, data=TARGET)

        if response.status_code == 200:
            return jsonify({"status": "success", "message": f"[{player_id}] GOOD VISIT✅"}), 200
        else:
            return jsonify({"status": "failed", "message": f"Request failed with status {response.status_code}"}), response.status_code

    except httpx.RequestError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
