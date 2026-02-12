
import os
import json
import datetime as dt
import statistics
import jwt
import httpx

from fastapi import FastAPI, WebSocket, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer
from fastapi.templating import Jinja2Templates

SECRET_KEY = os.getenv("JWT_SECRET", "supersecret")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
ALLOWED_ROLE = os.getenv("DASHBOARD_ALLOWED_ROLE_ID")

STATE_FILE = "app/data/freegames_global_state.json"

app = FastAPI()
templates = Jinja2Templates(directory="app/dashboard/templates")
security = HTTPBearer()

def create_token(user_id):
    payload = {"sub": user_id, "exp": dt.datetime.utcnow() + dt.timedelta(hours=2)}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid session")

@app.get("/login")
async def login():
    return RedirectResponse(
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=identify%20guilds.members.read"
    )

@app.get("/callback")
async def callback(code: str):
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = await client.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
        token_data = r.json()

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="OAuth failed")

        user = await client.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
        user_id = user.json()["id"]

    jwt_token = create_token(user_id)
    response = RedirectResponse("/dashboard")
    response.set_cookie("session", jwt_token, httponly=True)
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("heatmap.html", {"request": request})

@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()

    while True:
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except:
            state = {"offers": []}

        counts = {}
        for o in state.get("offers", []):
            platform = o.get("platform", "unknown")
            counts[platform] = counts.get(platform, 0) + 1

        # AI anomaly detection (z-score simple model)
        values = list(counts.values())
        anomaly = False
        if len(values) > 1:
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            for v in values:
                if stdev > 0 and abs((v - mean) / stdev) > 2:
                    anomaly = True

        payload = {
            "counts": counts,
            "anomaly_detected": anomaly
        }

        await ws.send_json(payload)
        await ws.receive_text()
