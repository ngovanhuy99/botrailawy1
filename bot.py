import json
import os
import time
import threading
import requests
from datetime import datetime
import pytz

# ====== CẤU HÌNH ======
BOT_TOKEN = "8357910547:AAHNeg3UdcWnEQvp0U6LCjwsZ668hWOTLlQ"
ADMIN_ID = 7071414779
DATA_FILE = "data.json"
API_URL = "apisunbantung-production.up.railway.app" 
QR_IMAGE = ""

# ====== HÀM QUẢN LÝ DỮ LIỆU ======
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"keys": {}, "active_users": [], "admins": [ADMIN_ID], "last_prediction": None}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ====== HÀM TELEGRAM ======
def send_telegram(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )
    except Exception as e:
        print("Lỗi gửi Telegram:", e)

def send_photo(chat_id, photo_path, caption=None):
    try:
        with open(photo_path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": f}
            )
    except Exception as e:
        print("Lỗi gửi ảnh Telegram:", e)

# ====== VÒNG LẶP LẤY API ======
def api_loop():
    last_session = None
    tz = pytz.timezone("Asia/Ho_Chi_Minh")

    while True:
        try:
            data = load_data()
            res = requests.get(API_URL, timeout=5)
            if res.status_code != 200:
                print("Lỗi API, status code:", res.status_code)
                time.sleep(5)
                continue
            res_json = res.json()

            session_id = str(res_json.get("next_session", ""))
            history = res_json.get("history", [])
            prediction = res_json.get("prediction", "").strip()
            datvi = res_json.get("datvi", "").strip()

            if session_id and session_id != last_session:
                now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                history_display = history[-5:]
                history_str = " | ".join(history_display)
                last_result = None
                if data.get("last_prediction") is not None and len(history) > 0:
                    last_result = "✅ ĐÚNG" if history[-1] == data["last_prediction"] else "❌ SAI"

                msg = (
                    f"ÂNWIN: Phiên kế tiếp: {session_id}\n"
                    f"📊 Lịch sử gần nhất: {history_str}\n"
                    f"📌 Phiên trước: {last_result if last_result else 'Chưa xác định'}\n"
                    f"🎯 Dự đoán phiên sau: {prediction}\n"
                    f"🎯 Dự đoán vị: {datvi}\n"
                    f"🇻🇳 Thời gian dự đoán: {now}"
                )

                if data["active_users"]:
                    for user in data["active_users"]:
                        send_telegram(user, msg)
                        time.sleep(0.1)

                data["last_prediction"] = prediction
                save_data(data)
                last_session = session_id

        except Exception as e:
            print("Lỗi API:", e)
        time.sleep(3)

# ====== XỬ LÝ TIN NHẮN TELEGRAM ======
def handle_telegram_updates():
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            res = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params=params
            ).json()
            updates = res.get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                if "message" not in update:
                    continue
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "").strip()
                data = load_data()

                # === start/help ===
                if text.startswith("/start"):
                    caption = (
                        "📌 Mua key để sử dụng tool:\n"
                        "- 1 ngày: 35k\n"
                        "- 1 tuần: 90k\n"
                        "- 1 tháng: 250k\n"
                        "- 2 tháng: 350k\n"
                        "- Vĩnh viễn: 550k\n\n"
                        "💳 Chuyển khoản theo QR ở trên\n"
                        "📩 Liên hệ: @NguyenTung2029"
                    )
                    send_photo(chat_id, QR_IMAGE, caption)

                elif text.startswith("/help"):
                    help_text = (
                        "📖 Danh sách lệnh:\n"
                        "/start - Xem thông tin mua tool + QR\n"
                        "/help - Xem hướng dẫn\n"
                        "/key <key> - Nhập key để kích hoạt\n"
                        "/chaybot - Bật nhận dự đoán\n"
                        "/tatbot - Tắt nhận dự đoán\n"
                        "/addadmin <user_id> - Thêm admin mới\n"
                        "/xoaadmin <user_id> - Xóa admin\n"
                        "/dsadmin - Xem danh sách admin (chỉ admin chính)\n\n"
                        "🔐 Lệnh admin:\n"
                        "/taokey <key> <số_lượt> <số_ngày> - Tạo key\n"
                        "/xoakey <key> - Xóa key\n"
                        "/dskey - Xem danh sách key"
                    )
                    send_telegram(chat_id, help_text)

                # === Admin lệnh quản lý ===
                elif text.startswith("/addadmin"):
                    if chat_id in data.get("admins", [ADMIN_ID]):
                        try:
                            new_admin_id = int(text.split()[1])
                            if new_admin_id not in data["admins"]:
                                data["admins"].append(new_admin_id)
                                save_data(data)
                                send_telegram(chat_id, f"✅ Đã thêm admin mới: {new_admin_id}")
                                send_telegram(new_admin_id, "✅ Bạn đã được thêm làm admin.")
                            else:
                                send_telegram(chat_id, "⚠️ Người này đã là admin.")
                        except:
                            send_telegram(chat_id, "❌ Sai cú pháp. /addadmin <user_id>")
                    else:
                        send_telegram(chat_id, "❌ Bạn không có quyền.")

                elif text.startswith("/xoaadmin"):
                    if chat_id in data.get("admins", [ADMIN_ID]):
                        try:
                            remove_id = int(text.split()[1])
                            if remove_id == ADMIN_ID:
                                send_telegram(chat_id, "❌ Không thể xóa admin chính.")
                            elif remove_id in data["admins"]:
                                data["admins"].remove(remove_id)
                                save_data(data)
                                send_telegram(chat_id, f"✅ Đã xóa admin: {remove_id}")
                                send_telegram(remove_id, "⚠️ Bạn đã bị xóa quyền admin.")
                            else:
                                send_telegram(chat_id, "❌ Không tìm thấy admin này.")
                        except:
                            send_telegram(chat_id, "❌ Sai cú pháp. /xoaadmin <user_id>")
                    else:
                        send_telegram(chat_id, "❌ Bạn không có quyền.")

                elif text.startswith("/dsadmin"):
                    if chat_id == ADMIN_ID:
                        admins_list = data.get("admins", [ADMIN_ID])
                        msg = "📂 Danh sách admin:\n" + "\n".join([str(a) for a in admins_list])
                        send_telegram(chat_id, msg)
                    else:
                        send_telegram(chat_id, "❌ Bạn không có quyền.")

                elif text.startswith("/taokey"):
                    if chat_id in data.get("admins", [ADMIN_ID]):
                        try:
                            parts = text.split()
                            key = parts[1]
                            uses = int(parts[2]) if len(parts) > 2 else -1
                            days = int(parts[3]) if len(parts) > 3 else -1
                            expiry = time.time() + days*86400 if days > 0 else -1
                            data["keys"][key] = {"uses": uses, "expiry": expiry}
                            save_data(data)
                            exp_str = "vĩnh viễn" if expiry == -1 else datetime.fromtimestamp(expiry).strftime("%d/%m/%Y %H:%M")
                            send_telegram(chat_id, f"✅ Đã tạo key: {key}\n🔹 Số lượt: {uses if uses!=-1 else 'không giới hạn'}\n🔹 Hết hạn: {exp_str}")

                            if chat_id != ADMIN_ID:
                                send_telegram(ADMIN_ID, f"📢 Admin phụ {chat_id} vừa tạo key: {key}\n🔹 Số lượt: {uses if uses!=-1 else 'không giới hạn'}\n🔹 Hết hạn: {exp_str}")
                        except:
                            send_telegram(chat_id, "❌ Sai cú pháp. /taokey <key> <số_lượt> <số_ngày>")
                    else:
                        send_telegram(chat_id, "❌ Bạn không có quyền.")

                elif text.startswith("/xoakey"):
                    if chat_id in data.get("admins", [ADMIN_ID]):
                        try:
                            key = text.split()[1]
                            if key in data["keys"]:
                                del data["keys"][key]
                                save_data(data)
                                send_telegram(chat_id, f"✅ Đã xóa key: {key}")
                            else:
                                send_telegram(chat_id, "❌ Không tìm thấy key.")
                        except:
                            send_telegram(chat_id, "❌ Sai cú pháp. /xoakey <key>")
                    else:
                        send_telegram(chat_id, "❌ Bạn không có quyền.")

                elif text.startswith("/dskey"):
                    if chat_id in data.get("admins", [ADMIN_ID]):
                        if not data["keys"]:
                            send_telegram(chat_id, "📂 Không có key nào.")
                        else:
                            msg = "📂 Danh sách key:\n"
                            for k, v in data["keys"].items():
                                exp_str = "vĩnh viễn" if v["expiry"] == -1 else datetime.fromtimestamp(v["expiry"]).strftime("%d/%m/%Y %H:%M")
                                uses_str = "không giới hạn" if v["uses"] == -1 else str(v["uses"])
                                msg += f"- {k}: {uses_str} lượt, hết hạn {exp_str}\n"
                            send_telegram(chat_id, msg)
                    else:
                        send_telegram(chat_id, "❌ Bạn không có quyền.")

                # === Nhập key ===
                elif text.startswith("/key"):
                    try:
                        key = text.split()[1]
                        if key in data["keys"]:
                            key_info = data["keys"][key]
                            if (key_info["expiry"] == -1 or time.time() <= key_info["expiry"]) and \
                               (key_info["uses"] == -1 or key_info["uses"] > 0):
                                send_telegram(chat_id, "✅ Key hợp lệ. Gõ /chaybot để bắt đầu nhận dự đoán.")
                                if key_info["uses"] > 0:
                                    key_info["uses"] -= 1
                                save_data(data)
                                send_telegram(ADMIN_ID, f"📢 User {chat_id} vừa nhập key thành công: {key}")
                            else:
                                send_telegram(chat_id, "❌ Key không hợp lệ hoặc đã hết hạn.")
                        else:
                            send_telegram(chat_id, "❌ Key không tồn tại.")
                    except:
                        send_telegram(chat_id, "❌ Sai cú pháp. /key <key>")

                # === Bật/tắt tool với thông báo admin ===
                elif text.startswith("/chaybot"):
                    if chat_id not in data["active_users"]:
                        data["active_users"].append(chat_id)
                        save_data(data)
                        send_telegram(chat_id, "✅ Bạn đã bật tool nhận dự đoán.")
                        send_telegram(ADMIN_ID, f"📢 User {chat_id} đã bật tool nhận dự đoán.")
                    else:
                        send_telegram(chat_id, "⚠️ Tool đã bật rồi.")

                elif text.startswith("/tatbot"):
                    if chat_id in data["active_users"]:
                        data["active_users"].remove(chat_id)
                        save_data(data)
                        send_telegram(chat_id, "⏸️ Bạn đã tắt tool nhận dự đoán.")
                        send_telegram(ADMIN_ID, f"📢 User {chat_id} đã tắt tool nhận dự đoán.")
                    else:
                        send_telegram(chat_id, "⚠️ Tool đã tắt rồi.")

        except Exception as e:
            print("Lỗi handle Telegram:", e)
            time.sleep(2)

# ====== MAIN ======
if __name__ == "__main__":
    print("📣 Đã chạy bot Sicbo by Khởi Ân")
    # Reset danh sách active_users khi khởi động bot
    save_data({"keys": {}, "active_users": [], "admins": [ADMIN_ID], "last_prediction": None})
    threading.Thread(target=api_loop, daemon=True).start()
    threading.Thread(target=handle_telegram_updates, daemon=True).start()
    while True:
        time.sleep(1)
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Sicbo Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ===== CHẠY BOT =====
def run_bot():
    # TODO: gọi hàm bot của bạn ở đây
    # ví dụ:
    # start_sicbo_bot()
    print("Bot đang chạy...")

if __name__ == "__main__":
    # chạy bot ở thread riêng
    t = threading.Thread(target=run_bot)
    t.start()

    # chạy flask
    run_flask()