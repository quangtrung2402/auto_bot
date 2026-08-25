import os
import requests
from tabulate import tabulate
from datetime import datetime, timezone, timedelta
from vnstock.api.quote import Quote  # Import class Quote mới từ vnstock.api

# Danh sách mã cổ phiếu quan tâm
TICKERS = ["VIC"]

def get_stock_prices():
    data = []

    # Lấy dữ liệu 5 ngày gần nhất để luôn đảm bảo có phiên hiện tại và phiên liền trước
    now_vn = datetime.now(timezone.utc) + timedelta(hours=7)
    end_date = now_vn.strftime("%Y-%m-%d")
    start_date = (now_vn - timedelta(days=5)).strftime("%Y-%m-%d")

    for ticker in TICKERS:
        try:
            # Khởi tạo Quote cho từng mã cổ phiếu (sử dụng nguồn VCI hoặc TCBS)
            q = Quote(symbol=ticker, source='VCI')

            # Lấy dữ liệu lịch sử giá
            df = q.history(start=start_date, end=end_date, interval='1D')

            if df is not None and not df.empty and len(df) >= 2:
                last_row = df.iloc[-1]
                prev_row = df.iloc[-2]

                # Lấy giá mở, cao, thấp, đóng (đơn vị: đồng)
                open_p = last_row['open'] * 1000
                high_p = last_row['high'] * 1000
                low_p = last_row['low'] * 1000
                close_p = last_row['close'] * 1000

                # Tính % tăng/giảm so với phiên trước
                prev_close = prev_row['close'] * 1000
                change = round(((close_p - prev_close) / prev_close) * 100, 2)
                sign = "+" if change > 0 else ""

                data.append([
                    ticker,
                    f"{open_p:,.0f}đ",
                    f"{high_p:,.0f}đ",
                    f"{low_p:,.0f}đ",
                    f"{close_p:,.0f}đ",
                    f"{sign}{change}%"
                ])
            else:
                data.append([ticker, "N/A", "N/A", "N/A", "N/A", "N/A"])
        except Exception as e:
            print(f"Lỗi khi lấy mã {ticker}: {e}")
            data.append([ticker, "N/A", "N/A", "N/A", "N/A", "N/A"])

    return data

def send_telegram_table():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Lỗi: Chưa thiết lập TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID!")
        return

    # Lấy thời gian hiện tại theo giờ Việt Nam (UTC+7)
    now_vn = datetime.now(timezone.utc) + timedelta(hours=7)
    # Định dạng thời gian: [HH:MM - DD/MM/YYYY] (VD: [12:34 - 31/08/2026])
    time_str = now_vn.strftime("%H:%M - %d/%m/%Y")

    table_data = get_stock_prices()
    headers = ["Mã", "Mở", "Cao", "Thấp", "Đóng", "+/-"]

    # Tạo bảng căn lề đẹp mắt bằng tabulate
    table_text = tabulate(table_data, headers=headers, tablefmt="simple")
    message = f"📊 **[{time_str}] CẬP NHẬT GIÁ CỔ PHIẾU** 📊\n```\n{table_text}\n```"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    res = requests.post(url, json=payload)
    if res.status_code != 200:
        print(f"Lỗi gửi Telegram: {res.text}")

if __name__ == "__main__":
    send_telegram_table()
