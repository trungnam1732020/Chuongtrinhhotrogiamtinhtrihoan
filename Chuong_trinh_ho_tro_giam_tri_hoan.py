import streamlit as st
import time
import csv
from datetime import datetime
import pandas as pd
import os
import plotly.express as px
from google.oauth2.service_account import Credentials
import gspread

# Cấu hình kết nối Google Sheets qua Service Account từ secrets
@st.cache_resource
def get_gsheet_client():
    # 1. Trích xuất chính xác dict chứa thông tin service_account từ [connections.gsheets]
    creds_dict = st.secrets["connections"]["gsheets"]
    
    # 2. Tạo dictionary đúng chuẩn cho Google OAuth2
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
        "https://www.googleapis.com/auth/drive"]
    
    creds = Credentials.from_service_account_info(info, scopes=scope)
    client = gspread.authorize(creds)
    return client
def get_worksheet():
    client = get_gsheet_client()
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    # 1. Mở file Google Sheet bằng URL
    sh = client.open_by_url(sheet_url)
    # 2. Lấy trang tính đầu tiên (Index 0)
    worksheet = sh.get_worksheet(0)
    return worksheet
tab1, tab2 = st.tabs(["⏱️ Giao Diện Hỗ Trợ Giảm Tính Trì Hoãn", "📊 Báo cáo Thống kê (KHKT)"])
with tab1:
    # Đọc tham số từ URL
    query_params = st.query_params
    is_test_mode = query_params.get("test") == "true"
    if "show_feedback" not in st.session_state:
        st.session_state.show_feedback = False
    if "risk_score" not in st.session_state:
        st.session_state.risk_score = None  
    if "pomo_running" not in st.session_state:
        st.session_state.pomo_running = False
    is_disabled=st.session_state.pomo_running
    def countdown_timer(seconds):
        st.session_state.pomo_running = True
        disabled=st.session_state.pomo_running
        if "time_left" not in st.session_state:
            st.session_state.time_left = seconds
        timer_placeholder = st.empty()
    # 2. Tạo nút bấm hoặc giao diện hiển thị
        mins, secs = divmod(st.session_state.time_left, 60)
    # Hiển thị đồng hồ dạng 00:00
        st.header(f"⏱️ {mins:02d}:{secs:02d}")
    # 3. Vòng lặp đếm ngược
        if st.session_state.pomo_running and st.session_state.time_left > 0:
            time.sleep(1)
            st.session_state.time_left -= 1
            st.rerun()
        elif st.session_state.time_left == 0:
            timer_placeholder.success("🎉 Bạn đã hoàn thành xuất sắc một phiên Pomodoro! Hãy nghỉ ngơi ít phút.")
            st.session_state.pomo_running = False
            st.session_state.show_feedback = True
    st.title("🎯 Trợ Lý Dự Đoán & Cảnh Báo Trì Hoãn Học Tập")
    task_name = st.text_input("Tên bài tập/nhiệm vụ:", "Bài tập Toán",disabled=is_disabled)
    difficulty = st.slider("Độ khó cảm nhận (1: Rất dễ - 5: Rất khó):", 1, 5, 3,disabled=is_disabled)
    stress_level = st.slider("Mức độ mệt mỏi/stress hôm nay (1: Tỉnh táo - 5: Kiệt sức):", 1, 5, 3,disabled=is_disabled)
    delay_count = st.number_input("Số lần bạn đã dời deadline bài này:", 0, 10, 0,disabled=is_disabled)
    if st.button("Phân tích nguy cơ trì hoãn",disabled=is_disabled):
        is_disabled=st.session_state.pomo_running
        risk_score = (difficulty * 0.35 + stress_level * 0.35 + min(delay_count * 2, 5) * 0.30) / 5 * 100
        st.session_state.risk_score = risk_score
    if st.session_state.risk_score is not None:
        risk_score = st.session_state.risk_score
        st.divider() 
        st.subheader(f"📊 Nguy cơ trì hoãn: {risk_score:.1f}%")
        if risk_score >= 70:
            st.error("🚨 NGUY CƠ TRÌ HOÃN RẤT CAO!")
            st.write("💡 **Giải pháp điều chỉnh:** Nhiệm vụ quá tải so với năng lượng hiện tại.")
            st.info("👉 **Hành động ngay:** Đừng làm cả bài. Hãy xử lí từng câu từ dễ đến khó và làm trong 5 phút!")
        elif risk_score >= 40:
            st.warning("⚠️ NGUY CƠ TRÌ HOÃN TRUNG BÌNH.")
            st.write("💡 **Giải pháp điều chỉnh:** Dùng kỹ thuật Pomodoro.")
            st.write("Phương pháp Pomodoro là một kỹ thuật quản lý thời gian được phát triển bởi Francesco Cirillo vào cuối những năm 1980."
                     "Phương pháp này giúp con người làm việc hoặc học tập hiệu quả hơn thông qua việc chia nhỏ thời gian làm việc thành các chu kỳ ngắn xen kẽ với thời gian nghỉ ngắn.")
            if is_test_mode:
                st.warning("⚠️ Đang ở chế độ TEST (Thử nghiệm 10 giây)")
                countdown_timer(10)
            else:
                mode = st.radio("Chọn Chế Độ Tập Trung:", ("25 phút (Pomodoro chuẩn)", "45 phút (1 Tiết học)"),
                index=None,key="pomodoro_mode_radio",)  # Để trống, không chọn sẵn
                if mode == "25 phút (Pomodoro chuẩn)":
                    countdown_timer(1500)
                elif mode == "45 phút (1 Tiết học)":
                    countdown_timer(2700)
                else:
        # Nếu chưa chọn chế độ, xóa time_left cũ để lần sau chọn lại từ đầu
                    if "time_left" in st.session_state:
                        del st.session_state["time_left"]
                    st.info("👈 Chọn một chế độ bên trên để bắt đầu.")
        else:
            st.success("✅ NGUY CƠ THẤP! Bạn đang có trạng thái tốt, hãy bắt đầu ngay.")
            st.write("**Gợi Ý:** Hãy ưu tiên bài quan trọng nhất khi còn tỉnh táo!")
            st.write("Phương pháp Pomodoro là một kỹ thuật quản lý thời gian được phát triển bởi Francesco Cirillo vào cuối những năm 1980."
                     "Phương pháp này giúp con người làm việc hoặc học tập hiệu quả hơn thông qua việc chia nhỏ thời gian làm việc thành các chu kỳ ngắn xen kẽ với thời gian nghỉ ngắn.")
            st.button("Bắt đầu Pomodoro 45 phút",disabled=is_disabled)
            if is_test_mode:
                st.warning("⚠️ Đang ở chế độ TEST (Thử nghiệm 10 giây)")
                countdown_timer(10)
            else:
                mode = st.radio("Chọn Chế Độ Tập Trung:", ("25 phút (Pomodoro chuẩn)", "45 phút (1 Tiết học)"),
                index=None,key="pomodoro_mode_radio",)  # Để trống, không chọn sẵn
                if mode == "25 phút (Pomodoro chuẩn)":
                    countdown_timer(1500)
                elif mode == "45 phút (1 Tiết học)":
                    countdown_timer(2700)
                else:
                    # Nếu chưa chọn chế độ, xóa time_left cũ để lần sau chọn lại từ đầu
                    if "time_left" in st.session_state:
                        del st.session_state["time_left"]
                    st.info("👈 Chọn một chế độ bên trên để bắt đầu.")
    if st.session_state.get("show_feedback", False):
        st.markdown("---")
        st.subheader("📝 Đánh giá hiệu quả phiên học")
        with st.form(key="feedback_form"):
            danh_gia = st.radio(
    "Bạn cảm thấy như thế nào về phiên học vừa rồi?",
    [ "😄 Rất hiệu quả", "Khá ổn", "😞 Không hiệu quả" ])
            danh_sach_ly_do = st.text_input(
            "Lý do xao nhãng (Nếu có):", 
            placeholder="Ví dụ: Bị thông báo điện thoại làm phiền, mệt mỏi...")
            submit_button = st.form_submit_button(label="Gửi đánh giá")
            if "submit_button" in locals() and submit_button:
                final_reason = (danh_sach_ly_do if danh_sach_ly_do.strip() != "" else "Không có")
                thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                try:
                    worksheet = get_worksheet()
                    
                    # Đảm bảo worksheet không bị None trước khi ghi
                    if worksheet:
                        worksheet.append_row([thoi_gian, danh_gia, final_reason])
                        st.session_state.risk_score = None
                        st.success("🎉 Đã lưu phản hồi thành công lên Google Sheets!")
                        st.session_state.show_feedback = False
                        if "time_left" in st.session_state:
                            del st.session_state["time_left"]
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Không thể kết nối tới Trang tính (Worksheet). Hãy kiểm tra lại URL Sheet.")
                except Exception as e:
                    st.error(f"Lỗi khi lưu lên Google Sheets: {e}")
with tab2:
    st.header("📊 Kết quả Thực nghiệm & Đánh giá Hiệu quả")
        # ĐẢM BẢO ĐỌC LẠI FILE CSV MỖI LẦN VÀO TAB
    try:
        # Đọc dữ liệu thực tế từ Google Sheets
        worksheet = get_worksheet()
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty and "Mức độ" in df.columns:
            # 1. Biểu đồ tròn (Pie Chart)
            fig = px.pie(
                df,
                names="Mức độ",
                title="Tỉ lệ đánh giá",
                color="Mức độ",
                color_discrete_map={
                    "😄 Rất hiệu quả": "#2ecc71",
                    "Khá ổn": "#f1c40f",
                    "😞 Không hiệu quả": "#e74c3c",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

            # 2. Bảng lý do chi tiết (Đảo ngược để dòng mới nhất nằm trên)
            st.subheader("📝 Danh sách lý do xao nhãng")
            st.dataframe(
                df.iloc[::-1], hide_index=True, use_container_width=True
            )

            # 3. Nút Tải file CSV sạch
            csv_data = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 Tải báo cáo CSV",
                data=csv_data,
                file_name="baocao_pomodoro.csv",
                mime="text/csv",
            )
        else:
            st.info("Chưa có dữ liệu phản hồi nào trên Google Sheets.")

    except Exception as e:
        st.error(f"Chưa kết nối được với Google Sheets. Vui lòng kiểm tra file secrets.toml! Lỗi: {e}")