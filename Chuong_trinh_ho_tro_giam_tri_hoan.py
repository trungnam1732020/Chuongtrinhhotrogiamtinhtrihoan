import streamlit as st
import time
import csv
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import os
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
            del st.session_state["time_left"]
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
            if st.session_state.pomo_running:
                if query_params.get("test") == "true":
                    countdown_timer(1/6)
                    st.sidebar.caption("Chế độ Demo (10s)")
                else:
                    countdown_timer(45)
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
            if submit_button:
                final_reason = danh_sach_ly_do if danh_sach_ly_do.strip() != "" else "Không có"
                # 1. Lưu vào CSV
                thoi_gian = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
                with open("feedback.csv", mode="a", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([thoi_gian, danh_gia,danh_sach_ly_do])
                st.success("Đã ghi nhận phản hồi!")
                st.success("Cảm ơn bạn đã đóng góp!")
                # 2. Dọn dẹp trạng thái & Reset giao diện
                st.session_state.show_feedback = False
                st.session_state.risk_score = None
                time.sleep(1.5)
                st.rerun()
        # (Bao gồm Slider, Đếm ngược Pomodoro, Form đánh giá Feedback...)
        st.write("Toàn bộ tính năng Pomodoro và Form đánh giá nằm ở đây.")
with tab2:
    st.header("📊 Kết quả Thực nghiệm & Đánh giá Hiệu quả")
    file_path = "feedback.csv"
    # Kiểm tra xem đã có dữ liệu chưa
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            # Đọc dữ liệu từ file CSV
            df = pd.read_csv(file_path, header=None)
            df.columns = ["Thời gian", "Đánh giá", "Lý do"]
            #Thay thế toàn bộ ô trống/rỗng thành chữ "Không có"
            df = df.fillna("Không có")
            df = df.replace("", "Không có")
            # 1. Vẽ Pie Chart
            st.subheader("1. Tỷ lệ Đánh giá Hiệu quả (Pie Chart)")
            dem = df["Đánh giá"].value_counts()
            
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.pie(dem, labels=dem.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')  # Giữ biểu đồ tròn xoe
            st.pyplot(fig)
            
            st.markdown("---")
            
            # 2. Hiển thị Bảng dữ liệu
            st.subheader("2. Dữ liệu chi tiết các lượt phản hồi")
            st.dataframe(df)
            with open("feedback.csv", "rb") as file:
                st.download_button(
                label="📥 Tải xuống dữ liệu phản hồi (.CSV)",
                data=file,
                file_name="feedback_baocao.csv",
                mime="text/csv"
    )
        except Exception as e:
            st.warning("Đã xảy ra lỗi khi đọc dữ liệu. Bạn hãy gửi thêm phản hồi mới nhé!") 