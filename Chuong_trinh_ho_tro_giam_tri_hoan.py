import streamlit as st
import time
import csv
from datetime import datetime
import pandas as pd
import os
import plotly.express as px
from google.oauth2.service_account import Credentials
import gspread
import re
import zoneinfo

# 1. CẤU HÌNH KẾT NỐI GOOGLE SHEETS

@st.cache_resource
def get_gsheet_client():
    creds_dict = st.secrets["connections"]["gsheets"]
    info = {
        "type": "service_account",
        "project_id": creds_dict["project_id"],
        "private_key_id": creds_dict["private_key_id"],
        "private_key": creds_dict["private_key"],
        "client_email": creds_dict["client_email"],
        "client_id": creds_dict["client_id"],
        "auth_uri": creds_dict["auth_uri"],
        "token_uri": creds_dict["token_uri"],
        "auth_provider_x509_cert_url": creds_dict["auth_provider_x509_cert_url"],
        "client_x509_cert_url": creds_dict["client_x509_cert_url"],
    }
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)
def get_worksheet():
    client = get_gsheet_client()
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_url(sheet_url)
    return sh.get_worksheet(0)

# 2. HÀM XỬ LÝ DỮ LIỆU CÁ NHÂN HÓA & CHẨN ĐOÁN

@st.cache_data(ttl=15)  # Cache 15 giây để chống lỗi tràn Quota 429
def load_sheet_data():
    """Chỉ gọi API đọc Google Sheets tối đa 1 lần mỗi 15 giây"""
    try:
        worksheet = get_worksheet()
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()
def normalize_id(text):
    """Chuẩn hóa chuỗi nhập vào: Xóa khoảng trắng thừa, chuyển về chữ thường,
    xử lý email lấy phần tên trước dấu @
    """
    if not text:
        return ""
    text = str(text).strip().lower()
    if "@" in text:
        text = text.split("@")[0]
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
def get_user_history(user_id):
    """Trích xuất lịch sử thông minh: Tự động nhận diện Họ tên/Email bất kể viết hoa/thường"""
    df = load_sheet_data()
    if not df.empty and "User ID" in df.columns:
        clean_target = normalize_id(user_id)
        return df[df["User ID"].apply(normalize_id) == clean_target]
    return pd.DataFrame()

def diagnose_user(user_history):
    """Mô hình chẩn đoán linh hoạt 3 cấp độ: Cảnh báo - Tiến bộ - Tốt"""
    total_sessions = len(user_history)
    if total_sessions >= 2:
        recent = user_history.tail(4)
        # Đếm số phiên 'Không hiệu quả' trong 5 phiên gần nhất
        fails_count = len(
            recent[
                recent["Mức Độ"]
                .astype(str)
                .str.contains("Không hiệu quả", na=False)
            ]
        )
        # 1. CẤP ĐỘ ĐỎ: Có từ 2 phiên xao nhãng trở lên
        if fails_count >= 2:
            return f"🔴 **CẢNH BÁO CHẨN ĐOÁN (Phiên {total_sessions}):** Bạn đang gặp khó khăn trong việc tập trung. Khuyên dùng chu kỳ ngắn 15-20 phút."

        # 2. CẤP ĐỘ VÀNG: Chỉ còn 1 phiên xao nhãng (Đang trên đà cải thiện)
        elif fails_count == 1:
            return f"🟡 **GHI NHẬN TIẾN BỘ (Phiên {total_sessions}):** Bạn đang lấy lại sự tập trung rất tốt! Hãy tiếp tục duy trì đà này nhé."

        # 3. CẤP ĐỘ XANH: 0 phiên xao nhãng (Phong độ hoàn hảo)
        else:
            return f"🟢 **CHẨN ĐOÁN (Phiên {total_sessions}):** Phong độ học tập của bạn đang duy trì rất tốt!"
    return f"💡 **CHẨN ĐOÁN ({total_sessions}/2 phiên):** Cần hoàn thành thêm phiên học để mô hình đưa ra dự đoán xu hướng."

# 3. SIDEBAR: NHẬN DIỆN NGƯỜI DÙNG (CẮT DỮ LIỆU CÁ NHÂN)
if "is_running" not in st.session_state:
    st.session_state.is_running = False
with st.sidebar:
    st.header("👤 Định danh Học sinh")
    st.caption("💡 **Mẹo:** Nên nhập **Họ tên + Lớp** (vd: `Đoàn Trung Nam 11N1`) hoặc 1 **Email** duy nhất để hệ thống theo dõi chính xác nhất.")
    is_running = st.session_state.get("is_running", False)
    user_id = st.text_input(
        "Nhập Họ tên / Email của bạn:", 
        placeholder="Ví dụ: HS10A1_05", 
        key="user_id_input", disabled=is_running)
    # Bắt buộc người dùng nhập Mã HS trước khi chạy ứng dụng
    if not user_id.strip():
        st.warning("⚠️ Vui lòng nhập Mã học sinh để tải lịch sử cá nhân hóa!")
        st.stop()
    st.success(f"Xin chào, **{user_id}**!")
    st.divider()

# 4. GIAO DIỆN CHÍNH (TABS)

tab1, tab2 = st.tabs(["⏱️ Giao Diện Hỗ Trợ Giảm Tính Trì Hoãn", "📊 Báo cáo Thống kê (KHKT)"])

with tab1:
    query_params = st.query_params
    is_test_mode = query_params.get("test") == "true"
    
    if "show_feedback" not in st.session_state:
        st.session_state.show_feedback = False
    if "risk_score" not in st.session_state:
        st.session_state.risk_score = None  
    if "pomo_running" not in st.session_state:
        st.session_state.pomo_running = False
        
    is_disabled = st.session_state.pomo_running

    def countdown_timer(seconds):
        st.session_state.pomo_running = True
        st.session_state.is_running = True
        if "time_left" not in st.session_state:
            st.session_state.time_left = seconds
        
        timer_placeholder = st.empty()
        mins, secs = divmod(st.session_state.time_left, 60)
        st.header(f"⏱️ {mins:02d}:{secs:02d}")
        
        if st.session_state.pomo_running and st.session_state.time_left > 0:
            time.sleep(1)
            st.session_state.time_left -= 1
            st.rerun()
        elif st.session_state.time_left == 0:
            timer_placeholder.success("🎉 Bạn đã hoàn thành xuất sắc một phiên Pomodoro! Hãy nghỉ ngơi ít phút.")
            st.session_state.pomo_running = False
            st.session_state.is_running = False
            st.session_state.show_feedback = True

    st.title("🎯 Trợ Lý Dự Đoán & Cảnh Báo Trì Hoãn Học Tập")

    # --- LẤY DỮ LIỆU VÀ HIỂN THỊ CHẨN ĐOÁN LỊCH SỬ ---
    user_history = get_user_history(user_id)
    st.info(diagnose_user(user_history))

    task_name = st.text_input("Tên bài tập/nhiệm vụ:", "Bài tập Toán", disabled=is_disabled)
    difficulty = st.slider("Độ khó cảm nhận (1: Rất dễ - 5: Rất khó):", 1, 5, 3, disabled=is_disabled)
    stress_level = st.slider("Mức độ mệt mỏi/stress hôm nay (1: Tỉnh táo - 5: Kiệt sức):", 1, 5, 3, disabled=is_disabled)
    delay_count = st.number_input("Số lần bạn đã dời deadline bài này:", 0, 10, 0, disabled=is_disabled)

    if st.button("Phân tích nguy cơ trì hoãn", disabled=is_disabled):
        risk_score = (difficulty * 0.35 + stress_level * 0.35 + min(delay_count * 2, 5) * 0.30) / 5 * 100
        st.session_state.risk_score = risk_score

    if st.session_state.risk_score is not None:
        risk_score = st.session_state.risk_score
        st.divider() 
        st.subheader(f"📊 Nguy cơ trì hoãn: {risk_score:.1f}%")
        
        if risk_score >= 70:
            st.error("🚨 NGUY CƠ TRÌ HOÃN RẤT CAO!")
            st.write("💡 **Giải pháp điều chỉnh:** Nhiệm vụ quá tải so với năng lượng hiện tại.")
            st.info("👉 **Hành động ngay:** Đừng làm cả bài. Hãy xử lý từng câu từ dễ đến khó và làm trong 5 phút!")
        elif risk_score >= 40:
            st.warning("⚠️ NGUY CƠ TRÌ HOÃN TRUNG BÌNH.")
            st.write("💡 **Giải pháp điều chỉnh:** Dùng kỹ thuật Pomodoro chia nhỏ thời gian.")
            
            if is_test_mode:
                st.warning("⚠️ Đang ở chế độ TEST (Thử nghiệm 10 giây)")
                countdown_timer(10)
            else:
                mode = st.radio("Chọn Chế Độ Tập Trung:", ("25 phút (Pomodoro chuẩn)", "45 phút (1 Tiết học)"), index=None, key="pomodoro_mode_radio")
                if mode == "25 phút (Pomodoro chuẩn)":
                    countdown_timer(1500)
                elif mode == "45 phút (1 Tiết học)":
                    countdown_timer(2700)
                else:
                    if "time_left" in st.session_state:
                        del st.session_state["time_left"]
                    st.info("👈 Chọn một chế độ bên trên để bắt đầu.")
        else:
            st.success("✅ NGUY CƠ THẤP! Bạn đang có trạng thái tốt, hãy bắt đầu ngay.")
            st.write("**Gợi Ý:** Hãy ưu tiên bài quan trọng nhất khi còn tỉnh táo!")
            
            if is_test_mode:
                st.warning("⚠️ Đang ở chế độ TEST (Thử nghiệm 10 giây)")
                countdown_timer(10)
            else:
                mode = st.radio("Chọn Chế Độ Tập Trung:", ("25 phút (Pomodoro chuẩn)", "45 phút (1 Tiết học)"), index=None, key="pomodoro_mode_radio_low")
                if mode == "25 phút (Pomodoro chuẩn)":
                    countdown_timer(1500)
                elif mode == "45 phút (1 Tiết học)":
                    countdown_timer(2700)

    # --- FORM BÁO CÁO CÓ TÍNH NĂNG GỢI Ý ĐÃ TỰ ĐỘNG DỰ ĐOÁN LÝ DO QUÁ KHỨ ---
    if st.session_state.get("show_feedback", False):
        st.markdown("---")
        st.subheader("📝 Đánh giá hiệu quả phiên học")
        
        # Dự đoán lý do xao nhãng học sinh hay gặp nhất trong quá khứ
        suggested_reason = ""
        if not user_history.empty and "Lý Do" in user_history.columns:
            frequent_reasons = user_history["Lý Do"].mode()
            if not frequent_reasons.empty and frequent_reasons[0] != "Không có":
                suggested_reason = frequent_reasons[0]

        with st.form(key="feedback_form"):
            danh_gia = st.radio(
                "Bạn cảm thấy như thế nào về phiên học vừa rồi?",
                ["😄 Rất hiệu quả", "Khá ổn", "😞 Không hiệu quả"]
            )
            
            danh_sach_ly_do = st.text_input(
                "Lý do xao nhãng (Mô hình gợi ý từ lịch sử của bạn):", 
                value=suggested_reason,
                placeholder="Ví dụ: Bị thông báo điện thoại làm phiền, mệt mỏi..."
            )
            
            submit_button = st.form_submit_button(label="Gửi đánh giá")
            
            if submit_button:
                final_reason = danh_sach_ly_do.strip() if danh_sach_ly_do.strip() != "" else "Không có"
                now_vn = datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh"))
                thoi_gian = now_vn.strftime("%Y-%m-%d %H:%M:%S")
                
                try:
                    worksheet = get_worksheet()
                    if worksheet:
                        # Ghi dữ liệu theo thứ tự: [User ID, Thời Gian, Mức Độ, Lý Do]
                        worksheet.append_row([user_id, thoi_gian, danh_gia, final_reason])
                        st.session_state.risk_score = None
                        st.success("🎉 Đã lưu phản hồi thành công và cập nhật mô hình cá nhân hóa!")
                        st.session_state.show_feedback = False
                        if "time_left" in st.session_state:
                            del st.session_state["time_left"]
                        time.sleep(1)
                        st.cache_data.clear()
                        st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu lên Google Sheets: {e}")


# 5. TAB BÁO CÁO THỐNG KÊ

with tab2:
    st.header("📊 Kết quả Thực nghiệm & Đánh giá Hiệu quả")
    try:
        # Sử dụng hàm đã được cache chống lỗi 429
        df = load_sheet_data()

        if not df.empty:
            column_map = {col: col.strip().title() for col in df.columns}
            df.rename(columns=column_map, inplace=True)
            muc_do_col = [c for c in df.columns if "Mức" in c]

            if muc_do_col:
                target_col = muc_do_col[0]

                # 1. Biểu đồ tròn
                fig = px.pie(
                    df,
                    names=target_col,
                    title="Tỉ lệ đánh giá toàn hệ thống",
                    color=target_col,
                    color_discrete_map={
                        "😄 Rất hiệu quả": "#2ecc71",
                        "Khá ổn": "#f1c40f",
                        "😞 Không hiệu quả": "#e74c3c",
                    },
                )
                st.plotly_chart(fig, use_container_width=True)

                # 2. Bảng lý do chi tiết
                st.subheader("📝 Danh sách lý do xao nhãng")
                st.dataframe(
                    df.iloc[::-1], hide_index=True, use_container_width=True
                )

                # 3. Nút Tải CSV
                csv_data = "\ufeff" + df.to_csv(
                    index=False, encoding="utf-8-sig"
                )
                st.download_button(
                    label="📥 Tải báo cáo CSV",
                    data=csv_data,
                    file_name="baocao_pomodoro.csv",
                    mime="text/csv",
                )
        else:
            st.info("Chưa có dữ liệu phản hồi nào trên Google Sheets.")

    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ Google Sheets: {e}")