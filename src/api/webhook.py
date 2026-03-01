from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
import uvicorn
import os
import logging
from src.services.whatsapp_service import WhatsAppService

app = FastAPI()
whatsapp_service = WhatsAppService()
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "my_secure_token_123")

@app.get("/api/webhook/whatsapp")
async def verify_webhook(hub_mode: str = Query(None, alias="hub.mode"), hub_challenge: str = Query(None, alias="hub.challenge"), hub_verify_token: str = Query(None, alias="hub.verify_token")):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN: return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/api/webhook/whatsapp")
async def handle_whatsapp_event(request: Request):
    try:
        data = await request.json()
        whatsapp_service.handle_webhook(data)
        return {"status": "success"}
    except Exception as e: return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
