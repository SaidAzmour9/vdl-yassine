from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


VDL_API_URL = os.getenv("VDL_API_URL")
VDL_API_TOKEN = os.getenv("VDL_API_TOKEN")
ALLOWED_STORE_ID = os.getenv("ALLOWED_STORE_ID", "store_q5OT-JqZ-QqPxkV0V7UZU")

@app.route("/ping", methods=["GET"])
def ping():
    return "App is alive", 200

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
                print("ℹ️ Ignored order due to store_id filter:", store_id)
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
                "customer_location": lf_full_address,
                "customer_phone_number": lf_shipping.get("phone") or node.get("phone") or "N/A",
                "products": products,
                "comment": (node.get("notes") or f"Order {node.get('name', '')}").strip(),
                "amount_received_from_customer": node.get("paid_by_customer", 0) or 0
            }

        else:
            # Branch 2: Handle Shopify-like payloads (existing behavior)
            # No store_id in typical Shopify payloads -> ignore per filter requirement
            print("ℹ️ Ignored Shopify-like payload: store_id missing")
            return jsonify({"message": "Ignored: store_id missing"}), 200

        print("📤 Sending to VDL:", payload)

        vdl_headers = {
            "Authorization": f"Bearer {VDL_API_TOKEN}",
            "Content-Type": "application/json"
        }

        vdl_response = requests.post(VDL_API_URL, headers=vdl_headers, json=payload)

        if vdl_response.status_code not in [200, 201]:
            print("❌ Failed to send to VDL:", vdl_response.text)
            return jsonify({"error": "Failed to forward to VDL"}), 500

        print("✅ Successfully sent to VDL")
        return jsonify({"message": "Success"}), 200

    except Exception as e:
        print("🔥 Exception:", str(e))
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(debug=True)