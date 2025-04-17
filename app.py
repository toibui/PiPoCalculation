import streamlit as st
import pandas as pd
import requests
import io 

# --- Cấu hình trang ---
st.set_page_config(page_title="Kiểm tra số lượng", layout="centered")
st.title("🧪 Check tương thích các xét nghiệm")

# --- Đọc dữ liệu từ Google Sheets ---
sheet_id = "1YkX9a0ThpJ8DLzVnsT78-NuQb-ucZbfRSJFb7JugV7Q"  # <-- Thay bằng ID thực tế
sheet_name = "Database"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

@st.cache_data
def load_data():
    response = requests.get(url)
    if response.status_code == 200:
        return pd.read_csv(io.StringIO(response.content.decode('utf-8')))
    else:
        st.error("Không thể tải dữ liệu từ Google Sheets.")
        return pd.DataFrame()

df = load_data()

# Kiểm tra dữ liệu
if not df.empty:
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# Kiểm tra cột cần thiết
required_cols = {"TestName", "TestPerDay", "GroupTest"}
if not required_cols.issubset(df.columns):
    st.error(f"⚠️ Thiếu cột trong dữ liệu: {required_cols - set(df.columns)}")
    st.stop()

# --- Giao diện người dùng ---
col1, col2 = st.columns(2)
nhom_list = ['Tất cả'] + sorted(df['GroupTest'].dropna().unique().tolist())

with col1:
    selected_nhom = st.selectbox("📂 Chọn nhóm xét nghiệm:", nhom_list)
with col2:
    search_name = st.text_input("🔤 Nhập tên test (có thể gõ một phần):", "")

so_luong_check = st.number_input(
    "🔢 Số test trên tháng (* Chỉ số test)(23 ngày, cal+qc (10%)):", 
    min_value=0, 
    step=1
)

# --- Lọc dữ liệu ---
filtered_df = df[df['TestPerDay'].notna()].copy()

if selected_nhom != "Tất cả":
    filtered_df = filtered_df[filtered_df['GroupTest'] == selected_nhom]
    if "Material#" in filtered_df.columns:
        filtered_df.drop(columns="Material#", inplace=True)

if search_name:
    filtered_df = filtered_df[filtered_df['TestName'].str.contains(search_name, case=False)]

# --- Hàm tô màu theo trạng thái ---
def highlight_status(row):
    if row['Trạng thái'] == "✅ Đạt":
        return ['background-color: #d4edda'] * len(row)
    else:
        return ['background-color: #f8d7da'] * len(row)

# --- Xử lý và hiển thị kết quả kiểm tra ---
if not filtered_df.empty:
    for col in ['Đóng gói', 'OBS [days]', 'reaction time [min.]', 'sample volume [µl]']:
        if col in filtered_df.columns:
            filtered_df[col] = filtered_df[col].astype(str)
    filtered_df['TestPerDay'] = filtered_df['TestPerDay'].astype(float)

    filtered_df['Trạng thái'] = filtered_df['TestPerDay'].apply(
        lambda x: "✅ Đạt" if (so_luong_check * 1.1 / 23) >= x else "❌ Không đạt"
    )

    st.subheader("📋 Kết quả kiểm tra:")
    styled_df = filtered_df.style.apply(highlight_status, axis=1)
    st.dataframe(styled_df, use_container_width=True)

else:
    st.warning("Không tìm thấy xét nghiệm phù hợp với điều kiện lọc.")

# --- Check theo file tải lên ---
st.title("🧪 Check tương thích các xét nghiệm theo file")
st.subheader("📁 Tải lên file Excel (.xlsx)")
uploaded_file = st.file_uploader("Chọn file Excel", type=["xlsx"])

if uploaded_file is not None:
    try:
        excel_file = pd.read_excel(uploaded_file)
        filtered2_df = df[df['TestPerDay'].notna()].copy()
        if "Material#" in filtered2_df.columns:
            filtered2_df.drop(columns="Material#", inplace=True)

        merge_df = filtered2_df.merge(excel_file, how='left', on='TestName')
        merge_df = merge_df[merge_df['Số lượng'].notna()]

        merge_df['Trạng thái'] = merge_df.apply(
            lambda x: "✅ Đạt" if (x['Số lượng'] * 1.1 / 23) >= x['TestPerDay'] else "❌ Không đạt", axis=1
        )

        st.subheader("📋 Kết quả kiểm tra từ file:")
        styled_df1 = merge_df.style.apply(highlight_status, axis=1)
        st.dataframe(styled_df1, use_container_width=True)

        # Tạo file xuất kết quả
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            merge_df.to_excel(writer, index=False, sheet_name='Kết quả')
        excel_data = output.getvalue()

        st.download_button(
            label="📥 Tải kết quả xuống (.xlsx)",
            data=excel_data,
            file_name="FileCheck.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"❌ Đã xảy ra lỗi khi xử lý file: {e}")
