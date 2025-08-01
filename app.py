from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
from byte import encrypt_api, Encrypt_ID

app = FastAPI()

@app.get("/visit_profile")
async def visit_profile(request: Request):
    player_id = request.query_params.get("player_id")
    token = request.query_params.get("token")

    if not player_id or not token:
        return JSONResponse({"error": "player_id and token are required"}, status_code=400)

    try:
        player_id = int(player_id)
    except ValueError:
        return JSONResponse({"error": "player_id must be an integer"}, status_code=400)

    encrypted_id = Encrypt_ID(player_id)
    encrypted_api = encrypt_api(f"08{encrypted_id}1007")
    TARGET = bytes.fromhex(encrypted_api)

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
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                "https://clientbp.common.ggbluefox.com/GetPlayerPersonalShow",
                headers=headers,
                content=TARGET
            )
        if response.status_code == 200:
            return {"status": "success", "message": f"[{player_id}] GOOD VISIT✅"}
        else:
            return {"status": "failed", "message": f"Request failed: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
