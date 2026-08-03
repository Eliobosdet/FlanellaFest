import time
import jwt
import json
from django.conf import settings

def generate_google_wallet_link(participant):
    issuer_id = settings.GOOGLE_WALLET_ISSUER_ID
    class_id = settings.GOOGLE_WALLET_CLASS_ID
    
    with open(settings.GOOGLE_SERVICE_ACCOUNT_FILE, 'r') as f:
        service_account_info = json.load(f)

    client_email = service_account_info['client_email']
    private_key = service_account_info['private_key']

    object_id = f"{issuer_id}.{participant.unique_id}"

    event_ticket_object = {
        "id": object_id,
        "classId": class_id,
        "state": "ACTIVE",
        "ticketHolderName": f"{participant.first_name} {participant.last_name}",
        "barcode": {
            "type": "QR_CODE",
            "value": str(participant.unique_id),
            "alternateText": str(participant.unique_id)[:8]
        }
    }

    now = int(time.time())
    payload = {
        "iss": client_email,
        "aud": "google",
        "typ": "savetowallet",
        "iat": now,
        "payload": {
            "eventTicketObjects": [event_ticket_object]
        },
        "origins": []
    }

    token = jwt.encode(payload, private_key, algorithm="RS256")
    return f"https://pay.google.com/gp/v/save/{token}"