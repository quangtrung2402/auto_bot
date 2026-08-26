import os
import io
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from vnstock.api.quote import Quote  # Import class Quote mới từ vnstock.api

# Danh sách mã cổ phiếu quan tâm
TICKERS_HOLD = ["VIC"]
TICKERS_REFER = ["FPT"]

def get_stock_prices():
    data = []
    # Gộp cả 2 danh sách, đánh dấu loại (HOLD / REFER)
    all_tickers = [(t, "HOLD") for t in TICKERS_HOLD] + [(t, "REFER") for t in TICKERS_REFER]

    # Lấy dữ liệu 5 ngày gần nhất để luôn đảm bảo có phiên hiện tại và phiên liền trước
    now_vn = datetime.now(timezone.utc) + timedelta(hours=7)
    end_date = now_vn.strftime("%Y-%m-%d")
    start_date = (now_vn - timedelta(days=5)).strftime("%Y-%m-%d")

    for ticker, group_type in all_tickers:
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

                data.append({
                    "type": group_type,
                    "row_data": [
                        ticker,
                        f"{open_p:,.0f}đ",
                        f"{high_p:,.0f}đ",
                        f"{low_p:,.0f}đ",
                        f"{close_p:,.0f}đ",
                        f"{sign}{change}%"
                    ]
                })
            else:
                data.append({"type": group_type, "row_data": [ticker, "N/A", "N/A", "N/A", "N/A", "N/A"]})
        except Exception as e:
            print(f"Lỗi khi lấy mã {ticker}: {e}")
            data.append({"type": group_type, "row_data": [ticker, "N/A", "N/A", "N/A", "N/A", "N/A"]})

    return data

def generate_table_image(data):
    """Vẽ bảng chứng khoán thành hình ảnh bằng Matplotlib"""
    headers = ["Mã", "Mở", "Cao", "Thấp", "Đóng", "+/-"]
    rows = [item["row_data"] for item in data]

    # Tạo Figure và Axis
    fig, ax = plt.subplots(figsize=(7, len(rows) * 0.45 + 0.2), dpi=200)
    ax.axis('off')

    # Lấy thời gian hiển thị trên tiêu đề
    now_vn = datetime.now(timezone.utc) + timedelta(hours=7)
    time_str = now_vn.strftime("%H:%M - %d/%m/%Y")
    title_text = f"CẬP NHẬT GIÁ CỔ PHIẾU [{time_str}]"

    # Vẽ bảng
    table = ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc='center',
        loc='center'
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)

    # Đặt tiêu đề dính sát đỉnh của bảng bằng ax.text
    # x=0.5 (căn giữa), y=1.02 (nằm sát mép trên ô Header), va='bottom' (đáy của chữ chạm sát viền ô)
    ax.text(
        0.5, 1.02, title_text,
        transform=ax.transAxes,
        fontsize=11,
        weight='bold',
        ha='center',
        va='bottom'
    )

    # Tô màu tiêu đề bảng
    for col_idx in range(len(headers)):
        cell = table[0, col_idx]
        cell.set_facecolor('#2C3E50')  # Xanh xám đậm
        cell.get_text().set_color('white')
        cell.get_text().set_weight('bold')

    # Tô màu các dòng dữ liệu (Dòng REFER có nền xanh lá nhạt)
    for row_idx, item in enumerate(data, start=1):
        # Mặc định dòng bình thường (HOLD): Trắng / Xám nhạt kẻ ô
        bg_color = '#E8F5E9' if item["type"] == "REFER" else ('#FFFFFF' if row_idx % 2 != 0 else '#F8F9FA')

        for col_idx in range(len(headers)):
            cell = table[row_idx, col_idx]
            cell.set_facecolor(bg_color)
            if item["type"] == "REFER":
                cell.get_text().set_weight('bold')  # In đậm mã REFER cho nổi bật

    # Lưu ảnh vào bộ nhớ RAM (BytesIO) thay vì đĩa cứng
    buf = io.BytesIO()
    # Lưu ảnh sát lề tối đa (pad_inches=0.05)
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05)
    buf.seek(0)
    plt.close(fig)
    
    return buf

def send_telegram_photo():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Lỗi: Chưa thiết lập TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID!")
        return

    # Lấy dữ liệu và tạo ảnh
    stock_data = get_stock_prices()
    img_buf = generate_table_image(stock_data)

    # Gửi ảnh sang Telegram bằng sendPhoto API
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    payload = {"chat_id": chat_id}
    files = {"photo": ("stock_table.png", img_buf, "image/png")}

    res = requests.post(url, data=payload, files=files)
    if res.status_code != 200:
        print(f"Lỗi gửi Telegram: {res.text}")

if __name__ == "__main__":
    send_telegram_photo()
