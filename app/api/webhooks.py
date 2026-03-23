# ©2026 VIDO Mahin Ltd develop by (Tanvir)

from fastapi import APIRouter, Request, HTTPException, status, Header
from datetime import datetime, timedelta
import logging
import httpx
import base64

from app.db.mongodb import get_database
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_paypal_access_token() -> str:
    """Helper function to get PayPal OAuth2 Access Token"""
    base_url = "https://api-m.sandbox.paypal.com" if settings.PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"
    auth_string = f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_SECRET}"
    b64_auth = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{base_url}/v1/oauth2/token", headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]

async def verify_paypal_webhook(request: Request, payload: dict) -> bool:
    """Verifies the webhook signature with PayPal"""
    try:
        access_token = await get_paypal_access_token()
        base_url = "https://api-m.sandbox.paypal.com" if settings.PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        # PayPal requires exactly these headers for verification
        verification_data = {
            "auth_algo": request.headers.get("paypal-auth-algo"),
            "cert_url": request.headers.get("paypal-cert-url"),
            "transmission_id": request.headers.get("paypal-transmission-id"),
            "transmission_sig": request.headers.get("paypal-transmission-sig"),
            "transmission_time": request.headers.get("paypal-transmission-time"),
            "webhook_id": settings.PAYPAL_WEBHOOK_ID,
            "webhook_event": payload
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v1/notifications/verify-webhook-signature", 
                headers=headers, 
                json=verification_data
            )
            response.raise_for_status()
            result = response.json()
            return result.get("verification_status") == "SUCCESS"
            
    except Exception as e:
        logger.error(f"Webhook verification failed: {e}")
        return False

@router.post("/paypal")
async def paypal_webhook(request: Request):
    try:
        payload = await request.json()
        
        # 1. VERIFY THE SIGNATURE FIRST (Security Check)
        is_verified = await verify_paypal_webhook(request, payload)
        if not is_verified:
            logger.warning("🚨 ALERT: Fake or unverified PayPal Webhook received!")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

        # 2. Process the verified data
        event_type = payload.get("event_type")
        resource = payload.get("resource", {})
        custom_id = resource.get("custom_id")
        
        logger.info(f"✅ Verified PayPal Webhook Event: {event_type}")

        if not custom_id:
            return {"status": "ignored", "reason": "missing custom_id"}

        db = get_database()
        users_collection = db.get_collection("users")

        if event_type in ["BILLING.SUBSCRIPTION.ACTIVATED", "PAYMENT.SALE.COMPLETED"]:
            new_expiry_date = datetime.utcnow() + timedelta(days=30)
            await users_collection.update_one(
                {"email": custom_id},
                {"$set": {"is_premium": True, "premium_expiry": new_expiry_date}}
            )
            logger.info(f"User {custom_id} upgraded successfully.")

        elif event_type in ["BILLING.SUBSCRIPTION.CANCELLED", "BILLING.SUBSCRIPTION.EXPIRED"]:
            await users_collection.update_one(
                {"email": custom_id},
                {"$set": {"is_premium": False, "premium_expiry": None}}
            )
            logger.info(f"Premium revoked for user {custom_id}.")

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PayPal webhook: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")