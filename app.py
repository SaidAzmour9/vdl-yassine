from flask import Flask, request, jsonify
import requests
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


VDL_API_URL = "https://api.vdlfulfilment.net/orders/create"
VDL_API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5N2E2YjgwZi0yMDExLTQ0YjItYThiOC1lNDE3MmQxNmJhNGIiLCJqdGkiOiJlZTI1NzY0MjYwNGU2OWViYWUyODhiN2I5NWZiNWQ2ZDIxM2FjZjQ4ODRmN2JhM2UwYTI0ZjJlYmRiOGQ5NDEyMTg4MTJlMDM2YzU1ZGI3MyIsImlhdCI6MTc2MDg4MjI2MC44OTEwMTIsIm5iZiI6MTc2MDg4MjI2MC44OTEwMTQsImV4cCI6MTc5MjQxODI2MC44ODY0MDgsInN1YiI6IjQ0MCIsInNjb3BlcyI6W119.Fdab58De13leXfNuSe32VapXbasjfA6ARZT8VuR5elGvzjR_mktKJH4pS5lKHKNdCnRCsCw_iJfo4jdspUl5MDNJJ6sMY8e8tIxOO3XPohbS0waJho_XP87emA7K9p0sktdvHHbjmHFT6UJE5Yw27aN0qMVPF_oLpffy9ZE56veR2Tm-EyrfZ0nIXGVwyU23ZzyxtYcaGlbbKukrXokMNuH4FYVWZNUB0ij4ryYA7HXQ57oQLcinFWBRAD8uuwctjhl1cYeC4hICWTjSF8Qz0WjgCjBP9hC-XzodM3ZTmIRpDN_X-m8_yTzTinxm_BaZglsOu_CElimkIbQV6E7EyZHPOw6jtsyxzU4aNUlgkEK-2puKbCbHKyzZMLJFQgQNYNj0LjTgeGxT56_aD0xfzk8VSssKKDVWkT6fbr2lodV5CgH7IrJiyZqmVOPbjBJ7Avm9cmlnm9p-hl3MLvEqJ6NTGPTh6eUaMsF_70KDEinqkWUvP_exfDz61i-XXvmD4mAVe_GsZ9fWTISxlwfNyuFFDm7X0T2XchILHA4I3tKy2HCJw3WBzDY_kt8khfweKB9fWXJryAMP6o4Iwtob5yyZGSnx3CWF9dRUq0ifdQpObTF0kSrEhgX78h8i0pvBMdkzb_7_FGDdbBfDeBFrlsDvfyo0LY8QbWbXGhJbD-c"
ALLOWED_STORE_ID = "store_q5OT-JqZ-QqPxkV0V7UZU"

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = "contactazmour@gmail.com"
SMTP_PASSWORD = "wmyd jqro naha crso"
EMAIL_FROM = "contactazmour@gmail.com"
EMAIL_TO = "azmour2016maroc@gmail.com"
def send_error_email(error_message, order_data=None):
    """Send error notification email"""
    if not all([SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        print("⚠️ Email configuration incomplete, skipping email notification")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = f"VDL Webhook Error - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        body = f"""
VDL Webhook Error Report

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Error: {error_message}

Order Data:
{order_data if order_data else 'No order data available'}

Please check the webhook logs for more details.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_FROM, EMAIL_TO, text)
        server.quit()
        
        print("📧 Error email sent successfully")
        
    except Exception as email_error:
        print(f"❌ Failed to send error email: {str(email_error)}")

@app.route("/ping", methods=["GET"])
def ping():
    return "App is alive and running", 200

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    try:
        data = request.get_json()
        

        # Branch 1: Handle payloads wrapped in a `node` object (e.g., Lightfunnels-style)
        if isinstance(data, dict) and "node" in data and isinstance(data.get("node"), dict):
            node = data.get("node", {})

            # Filter by store_id
            store_id = node.get("store_id")
            if store_id != ALLOWED_STORE_ID:
                print("ℹ️ Ignored order due to store_id filter:", store_id, flush=True)
                return jsonify({"message": "Ignored: store_id not allowed"}), 200

            # Extract customer/shipping details
            lf_shipping = node.get("shipping_address", {})
            customer = node.get("customer", {})

            # Build address string
            lf_address_parts = [
                lf_shipping.get("line1", ""),
                lf_shipping.get("city", ""),
                lf_shipping.get("state", ""),
                lf_shipping.get("country", "")
            ]
            lf_full_address = ", ".join([part for part in lf_address_parts if part])

            # Build products list
            lf_items = node.get("items", []) or []
            products = [
                {
                    "name": (item.get("title") or "Unknown").strip(),
                    "code": item.get("sku", ""),
                    "amount": item.get("price", 0),
                    "quantity": item.get("quantity", 1) or 1
                }
                for item in lf_items
            ]

            # Compose payload for VDL
            payload = {
                "customer_name": (customer.get("full_name") or (
                    f"{lf_shipping.get('first_name', '')} {lf_shipping.get('last_name', '')}".strip()
                ) or "").strip(),
                "customer_phone_number": lf_shipping.get("phone") or node.get("phone") or "N/A",
                "prodcts": products,
                "comment": (node.get("notes") or f"Order {node.get('name', '')}").strip(),
                "amount_received_from_customer": node.get("paid_by_customer", 0) or 0
            }

        else:
            # Branch 2: Handle Shopify-like payloads (existing behavior)
            # No store_id in typical Shopify payloads -> ignore per filter requirement
            print("ℹ️ Ignored Shopify-like payload: store_id missing" , flush=True)
            return jsonify({"message": "Ignored: store_id missing"}), 200

        print("📤 Sending to VDL:", payload)

        vdl_headers = {
            "Authorization": f"Bearer {VDL_API_TOKEN}",
            "Content-Type": "application/json"
        }

        vdl_response = requests.post(VDL_API_URL, headers=vdl_headers, json=payload)

        if vdl_response.status_code not in [200, 201]:
            error_msg = f"VDL API returned status {vdl_response.status_code}: {vdl_response.text}"
            print("❌ Failed to send to VDL:", error_msg, flush=True)
            send_error_email(error_msg, data)
            return jsonify({"error": "Failed to forward to VDL"}), 500

        print("✅ Successfully sent to VDL", flush=True)
        return jsonify({"message": "Success"}), 200

    except Exception as e:
        error_msg = f"Exception in webhook handler: {str(e)}"
        print("🔥 Exception:", error_msg, flush=True)
        send_error_email(error_msg, data)
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
