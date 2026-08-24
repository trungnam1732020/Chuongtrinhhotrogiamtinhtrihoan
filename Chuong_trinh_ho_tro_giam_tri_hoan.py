import csv
from datetime import datetime
import os
import re
import time
import zoneinfo
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
import streamlit as st

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
        "auth_provider_x509_cert_url": creds_dict[
            "auth_provider_x509_cert_url"],
        "client_x509_cert_url": creds_dict["client_x509_cert_url"]}
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)


def get_worksheet():
    client = get_gsheet_client()
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_url(sheet_url)
    return sh.get_worksheet(0)

# 2. HÀM XỬ LÝ DỮ LIỆU CÁ NHÂN HÓA, CHẨN ĐOÁN & THEME

@st.cache_data(ttl=15)
def load_sheet_data():
    """Chỉ gọi API đọc Google Sheets tối đa 1 lần mỗi 15 giây"""
    try:
        worksheet = get_worksheet()
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

def normalize_id(text):
    if not text:
        return ""
    text = str(text).strip().lower()
    if "@" in text:
        text = text.split("@")[0]
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def get_user_history(user_id):
    df = load_sheet_data()
    if not df.empty and "User ID" in df.columns:
        clean_target = normalize_id(user_id)
        return df[df["User ID"].apply(normalize_id) == clean_target]
    return pd.DataFrame()

def diagnose_user(user_history):
    total_sessions = len(user_history)
    if total_sessions >= 2:
        recent = user_history.tail(4)
        fails_count = len(
            recent[
                recent["Mức Độ"]
                .astype(str)
                .str.contains("Không hiệu quả", na=False)])

        if fails_count >= 2:
            return f"🔴 **CẢNH BÁO CHẨN ĐOÁN (Phiên {total_sessions}):** Bạn đang gặp khó khăn trong việc tập trung. Khuyên dùng chu kỳ ngắn 15-20 phút."
        elif fails_count == 1:
            return f"🟡 **GHI NHẬN TIẾN BỘ (Phiên {total_sessions}):** Bạn đang có sự tập trung rất tốt! Hãy tiếp tục duy trì đà này nhé."
        else:
            return f"🟢 **CHẨN ĐOÁN (Phiên {total_sessions}):** Phong độ học tập của bạn đang duy trì rất tốt!"

    return f"💡 **CHẨN ĐOÁN ({total_sessions}/2 phiên):** Cần hoàn thành thêm phiên học để mô hình đưa ra dự đoán xu hướng."

def get_recommendation(user_history):
    total_sessions = len(user_history)
    if total_sessions < 2:
        return {
            "time": 25,
            "method": "⏱️ Pomodoro Chuẩn (25 phút)",
            "tip": "Hoàn thành thêm phiên để hệ thống phân tích nhịp độ cá nhân của bạn.",}

    recent = user_history.tail(4)
    fails_count = len(
        recent[
            recent["Mức Độ"]
            .astype(str)
            .str.contains("Không hiệu quả", na=False)
        ])

    if fails_count >= 2:
        return {
            "time": 15,
            "method": "⚡ Micro-Pomodoro (15 Phút) + Quy tắc 5 Phút",
            "tip": "Năng lượng của bạn đang thấp. Hãy chia nhỏ mục tiêu và làm từng chút một! Ngoài ra, bạn cũng có thể bật nhạc không lời trong lúc học tập.",
        }
    elif fails_count == 1:
        return {
            "time": 25,
            "method": "🎯 Pomodoro Tiêu chuẩn (25 Phút)",
            "tip": "Đà tập trung đang trở lại. Giữ nguyên nhịp độ này và loại bỏ các tác nhân gây xao nhãng. Đồng thời hãy đặt điện thoại ở chế độ Im Lặng!",
        }
    else:
        return {
            "time": 45,
            "method": "🚀 Deep Work / Flow Zone (45 Phút)",
            "tip": "Sự Tập trung của bạn đang ở đỉnh cao! Hãy đặt điện thoại của bạn cách 2m và thử thách bản thân với các bài tập khó hơn.",
        }
def apply_dynamic_theme(user_history=None):
    """Đổi màu nền ứng dụng dựa trên phong độ chẩn đoán"""
    if user_history is None or len(user_history) < 2:
        return

    recent = user_history.tail(4)
    fails_count = len(
        recent[
            recent["Mức Độ"]
            .astype(str)
            .str.contains("Không hiệu quả", na=False)
        ]
    )

    if fails_count >= 2:
        st.markdown(
            "<style>.stApp { background-color: #FFF5F5 !important; }</style>",
            unsafe_allow_html=True,
        )
    elif fails_count == 1:
        st.markdown(
            "<style>.stApp { background-color: #FFFFF0 !important; }</style>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<style>.stApp { background-color: #F0FFF4 !important; }</style>",
            unsafe_allow_html=True,
        )

# 3. SIDEBAR: NHẬN DIỆN NGƯỜI DÙNG & GÓC TẬP TRUNG

if "is_running" not in st.session_state:
    st.session_state.is_running = False

with st.sidebar:
    st.header("👤 Định danh Học sinh")
    st.caption(
        "💡 **Mẹo:** Nên nhập **Họ tên + Lớp** (vd: `Đoàn Trung Nam 11N1`) hoặc 1 **Email** duy nhất."
    )
    is_running = st.session_state.get("is_running", False)
    user_id = st.text_input(
        "Nhập Họ tên / Email của bạn:",
        placeholder="Ví dụ: HS10A1_05",
        key="user_id_input",
        disabled=is_running,
    )
    if not user_id.strip():
        st.warning("⚠️ Vui lòng nhập Mã học sinh để tải lịch sử cá nhân hóa!")
    st.success(f"Xin chào, **{user_id}**!")
    st.divider()
    st.subheader("🎧 Góc Tập Trung")
    music_option = st.selectbox(
        "Chọn nhạc nền (Không quảng cáo):",
        options=[
            "Không Nhạc",
            "🌧️ Tiếng mưa nhẹ",
            "☕ Lofi Chill Study",
            "🧠 Sóng não Alpha (Tập trung)",
        ],
    )

    if music_option == "🌧️ Tiếng mưa nhẹ":
        st.audio(
            "https://cdn.pixabay.com/download/audio/2022/05/16/audio_db6591201e.mp3",
            format="audio/mp3",
        )
    elif music_option == "☕ Lofi Chill Study":
        st.audio(
            "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
            format="audio/mp3",
        )
    elif music_option == "🧠 Sóng não Alpha (Tập trung)":
        st.audio(
            "https://cdn.pixabay.com/download/audio/2021/09/06/audio_873e3a96aa.mp3",
            format="audio/mp3",
        )

# 4. GIAO DIỆN CHÍNH (TABS)

tab1, tab2 = st.tabs(
    ["⏱️ Giao Diện Hỗ Trợ Giảm Tính Trì Hoãn", "📊 Báo cáo Thống kê (KHKT)"]
)

with tab1:
    if not user_id.strip():
        st.warning(
            "⚠️ Vui lòng nhập **Họ tên / Mã học sinh** ở thanh bên trái (Sidebar) để tải dữ liệu cá nhân hóa và bắt đầu học!"
        )
    else:
        # 💡 Lấy dữ liệu cá nhân hóa TRƯỚC khi đổi Theme và Chẩn đoán
        user_history = get_user_history(user_id)
        # 🎨 Áp dụng màu nền tự động
        apply_dynamic_theme(user_history)
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
                timer_placeholder.success(
                    "🎉 Bạn đã hoàn thành xuất sắc một phiên Pomodoro! Hãy nghỉ ngơi ít phút."
                )
                st.session_state.pomo_running = False
                st.session_state.is_running = False
                st.session_state.show_feedback = True

        st.title("🎯 Trợ Lý Dự Đoán & Cảnh Báo Trì Hoãn Học Tập")

        # --- HIỂN THỊ CHẨN ĐOÁN LỊCH SỬ ---
        st.info(diagnose_user(user_history))
        rec = get_recommendation(user_history)
        with st.expander("💡 **PHƯƠNG PHÁP HỌC TẬP TỐI ƯU CHO BẠN**", expanded=True):
            st.markdown(f"👉 **Phương pháp:** {rec['method']}")
            st.markdown(f"💬 **Lời khuyên:** *{rec['tip']}*")
            st.info(f"🎯 **Thời gian khuyên dùng:** {rec['time']} phút/phiên")

        st.divider()

        task_name = st.text_input(
            "Tên bài tập/nhiệm vụ:", "Bài tập Toán", disabled=is_disabled
        )
        difficulty = st.slider(
            "Độ khó cảm nhận (1: Rất dễ - 5: Rất khó):",
            1,
            5,
            3,
            disabled=is_disabled,
        )
        stress_level = st.slider(
            "Mức độ mệt mỏi/stress hôm nay (1: Tỉnh táo - 5: Kiệt sức):",
            1,
            5,
            3,
            disabled=is_disabled,
        )
        delay_count = st.number_input(
            "Số lần bạn đã dời deadline bài này:", 0, 10, 0, disabled=is_disabled
        )

        if st.button("Phân tích nguy cơ trì hoãn", disabled=is_disabled):
            risk_score = (
                (
                    difficulty * 0.35
                    + stress_level * 0.35
                    + min(delay_count * 2, 5) * 0.30
                )
                / 5
                * 100
            )
            st.session_state.risk_score = risk_score

        if st.session_state.risk_score is not None:
            risk_score = st.session_state.risk_score
            st.divider()
            st.subheader(f"📊 Nguy cơ trì hoãn: {risk_score:.1f}%")

            if risk_score >= 70:
                st.error("🚨 NGUY CƠ TRÌ HOÃN RẤT CAO!")
                st.write(
                    "💡 **Giải pháp điều chỉnh:** Nhiệm vụ quá tải so với năng lượng hiện tại."
                )
                st.info(
                    "👉 **Hành động ngay:** Đừng làm cả bài. Hãy xử lý câu dễ nhất và làm nó trong 5 phút! Sau đó đi đến các câu tiếp theo"
                )
            elif risk_score >= 40:
                st.warning("⚠️ NGUY CƠ TRÌ HOÃN TRUNG BÌNH.")
                st.write(
                    "💡 **Giải pháp điều chỉnh:** Dùng kỹ thuật Pomodoro chia nhỏ thời gian."
                )

                if is_test_mode:
                    st.warning("⚠️ Đang ở chế độ TEST (Thử nghiệm 10 giây)")
                    countdown_timer(10)
                else:
                    mode = st.radio(
                        "Chọn Chế Độ Tập Trung:",
                        (
                            "15 phút (Micro-Pomodoro)",
                            "25 phút (Pomodoro chuẩn)",
                            "45 phút (1 Tiết học)",
                        ),
                        index=None,
                        key="pomodoro_mode_radio",
                    )
                    if mode == "15 phút (Micro-Pomodoro)":
                        countdown_timer(900)
                    elif mode == "25 phút (Pomodoro chuẩn)":
                        countdown_timer(1500)
                    elif mode == "45 phút (1 Tiết học)":
                        countdown_timer(2700)
                    else:
                        if "time_left" in st.session_state:
                            del st.session_state["time_left"]
                        st.info("👈 Chọn một chế độ bên trên để bắt đầu.")
            else:
                st.success(
                    "✅ NGUY CƠ THẤP! Bạn đang có trạng thái tốt, hãy bắt đầu ngay."
                )
                st.write(
                    "**Gợi Ý:** Hãy ưu tiên bài quan trọng nhất khi còn tỉnh táo!"
                )

                if is_test_mode:
                    st.warning("⚠️ Đang ở chế độ TEST (Thử nghiệm 10 giây)")
                    countdown_timer(10)
                else:
                    mode = st.radio(
                        "Chọn Chế Độ Tập Trung:",
                        (
                            "15 phút (Micro-Pomodoro)",
                            "25 phút (Pomodoro chuẩn)",
                            "45 phút (1 Tiết học)",
                        ),
                        index=None,
                        key="pomodoro_mode_radio",
                    )
                    if mode == "15 phút (Micro-Pomodoro)":
                        countdown_timer(900)
                    elif mode == "25 phút (Pomodoro chuẩn)":
                        countdown_timer(1500)
                    elif mode == "45 phút (1 Tiết học)":
                        countdown_timer(2700)
                    else:
                        if "time_left" in st.session_state:
                            del st.session_state["time_left"]
                        st.info("👈 Chọn một chế độ bên trên để bắt đầu.")

        # --- FORM ĐÁNH GIÁ PHIÊN HỌC ---
        if st.session_state.get("show_feedback", False):
            st.markdown("---")
            st.subheader("📝 Đánh giá hiệu quả phiên học")

            suggested_reason = ""
            if not user_history.empty and "Lý Do" in user_history.columns:
                frequent_reasons = user_history["Lý Do"].mode()
                if (
                    not frequent_reasons.empty
                    and frequent_reasons[0] != "Không có"
                ):
                    suggested_reason = frequent_reasons[0]

            with st.form(key="feedback_form"):
                danh_gia = st.radio(
                    "Bạn cảm thấy như thế nào về phiên học vừa rồi?",
                    ["😄 Rất hiệu quả", "Khá ổn", "😞 Không hiệu quả"],
                )

                danh_sach_ly_do = st.text_input(
                    "Lý do xao nhãng (Mô hình gợi ý từ lịch sử của bạn):",
                    value=suggested_reason,
                    placeholder="Ví dụ: Bị thông báo điện thoại làm phiền, mệt mỏi...",
                )

                submit_button = st.form_submit_button(label="Gửi đánh giá")

                if submit_button:
                    final_reason = (
                        danh_sach_ly_do.strip()
                        if danh_sach_ly_do.strip() != ""
                        else "Không có"
                    )
                    now_vn = datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh"))
                    thoi_gian = now_vn.strftime("%Y-%m-%d %H:%M:%S")

                    try:
                        worksheet = get_worksheet()
                        if worksheet:
                            worksheet.append_row(
                                [user_id, thoi_gian, danh_gia, final_reason]
                            )
                            st.session_state.risk_score = None
                            st.success(
                                "🎉 Đã lưu phản hồi thành công và cập nhật mô hình cá nhân hóa!"
                            )
                            st.session_state.show_feedback = False
                            st.session_state.is_running = False
                            st.session_state.pomo_running = False
                            if "time_left" in st.session_state:
                                del st.session_state["time_left"]
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu lên Google Sheets: {e}")

# 5. TAB BÁO CÁO THỐNG KÊ (KHKT)

with tab2:
    st.header("📊 Kết quả Thực nghiệm & Đánh giá Hiệu quả")
    try:
        df = load_sheet_data()

        if not df.empty:
            column_map = {col: col.strip().title() for col in df.columns}
            df.rename(columns=column_map, inplace=True)
            muc_do_col = [c for c in df.columns if "Mức" in c]

            if muc_do_col:
                target_col = muc_do_col[0]

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

                st.subheader("📝 Danh sách lý do xao nhãng")
                st.dataframe(
                    df.iloc[::-1], hide_index=True, use_container_width=True
                )

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