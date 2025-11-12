import streamlit as st
import pandas as pd

st.title("🧩 Efficiency Checker & Filler")

# ---------------------------------------------------------
# 1. Upload CSV Files
# ---------------------------------------------------------
st.header("📂 Upload CSV Files")
manpower_file = st.file_uploader("Upload manpower file", type=["csv"])
stylelist_file = st.file_uploader("Upload stylelist file", type=["csv"])
raweff_file = st.file_uploader("Upload raweff file", type=["csv"])
mastergwc_file = st.file_uploader("Upload Master_GWC file", type=["csv"])
individual_eff_file = st.file_uploader("Upload individual_efficiency file", type=["csv"])

if manpower_file and stylelist_file and raweff_file and mastergwc_file and individual_eff_file:
    # ---------------------------------------------------------
    # 2. Load all CSV files and convert column names to lowercase
    # ---------------------------------------------------------
    
    # ฟังก์ชันช่วยในการโหลดและแปลงชื่อคอลัมน์เป็นตัวพิมพ์เล็ก
    @st.cache_data
    def load_and_clean_csv(file):
        df = pd.read_csv(file)
        # แปลงชื่อคอลัมน์เป็นตัวพิมพ์เล็กทั้งหมด
        df.columns = df.columns.str.lower()
        return df

    manpower = load_and_clean_csv(manpower_file)
    stylelist = load_and_clean_csv(stylelist_file)
    raweff = load_and_clean_csv(raweff_file)
    master_gwc = load_and_clean_csv(mastergwc_file)
    individual_eff = load_and_clean_csv(individual_eff_file)

    st.success("✅ ทุกไฟล์โหลดและแปลงชื่อคอลัมน์เป็นตัวพิมพ์เล็กสำเร็จแล้ว!")

    # ---------------------------------------------------------
    # 3. Merge เพื่อหา missing eff ก่อน
    # ---------------------------------------------------------
    st.write("⚙️ กำลังรวมข้อมูล id, line, style ...")
    
    # ใช้คอลัมน์ชื่อเล็ก: 'line'
    merged = pd.merge(manpower, stylelist, on="line", how="left")
    final_table = merged[["id", "line", "style"]].copy()

    st.write("🔍 กำลังเติมค่า eff จาก raweff ...")
    # ใช้คอลัมน์ชื่อเล็ก: 'id', 'style', 'eff'
    final_table = pd.merge(final_table, raweff[["id", "style", "eff"]], on=["id", "style"], how="left")

    # หาเฉพาะข้อมูลที่ eff ว่าง
    missing_eff = final_table[final_table["eff"].isna()].sort_values(by=["line", "id"]).copy()

    st.write(f"📊 พบข้อมูลที่ไม่มี eff จำนวน: {len(missing_eff)} แถว")

    # ---------------------------------------------------------
    # 4. เติม gwc และ jobtitle
    # ---------------------------------------------------------
    st.write("🧠 เติมคอลัมน์ gwc และ jobtitle ...")

    # เติม gwc จาก master_gwc โดยใช้ style เป็นตัวเชื่อม
    # ใช้คอลัมน์ชื่อเล็ก: 'style', 'gwc'
    missing_eff = pd.merge(missing_eff, master_gwc[["style", "gwc"]], on="style", how="left")

    # เติม jobtitle จาก raweff โดยใช้ id, gwc เป็นตัวเชื่อม
    # ใช้คอลัมน์ชื่อเล็ก: 'id', 'gwc', 'jobtitle'
    missing_eff = pd.merge(
        missing_eff,
        raweff[["id", "gwc", "jobtitle"]],
        on=["id", "gwc"],
        how="left",
        suffixes=("", "_from_raweff")
    )

    # หาก jobtitle ยังว่าง เติมจาก manpower โดยใช้ id
    # ใช้คอลัมน์ชื่อเล็ก: 'id', 'jobtitle'
    missing_eff["jobtitle"] = missing_eff["jobtitle"].fillna(
        missing_eff.merge(manpower[["id", "jobtitle"]], on="id", how="left")["jobtitle_y"]
    )

    # ---------------------------------------------------------
    # 5. เติมค่า eff ตามลำดับเงื่อนไข
    # ---------------------------------------------------------
    st.write("⚙️ เติมค่า eff ตามลำดับเงื่อนไข ...")

    # step 1: เติมจาก raweff โดยใช้ id, gwc, jobtitle
    # ใช้คอลัมน์ชื่อเล็ก: 'id', 'gwc', 'jobtitle', 'eff'
    eff_fill = raweff.groupby(["id", "gwc", "jobtitle"], dropna=False)["eff"].mean().reset_index()
    missing_eff = pd.merge(
        missing_eff,
        eff_fill,
        on=["id", "gwc", "jobtitle"],
        how="left",
        suffixes=("", "_from_raweff")
    )

    # step 2: ถ้ายังไม่มีค่า eff ให้เติมจาก individual_eff โดยใช้ id เป็นตัวเชื่อม
    # ใช้คอลัมน์ชื่อเล็ก: 'id', 'eff %'
    missing_eff["eff"] = missing_eff["eff"].fillna(
        missing_eff.merge(
            individual_eff[["id", "eff %"]].rename(columns={"eff %": "eff_from_individual"}),
            on="id",
            how="left"
        )["eff_from_individual"]
    )

    # ---------------------------------------------------------
    # 6. แสดงผลลัพธ์ทั้งหมด
    # ---------------------------------------------------------
    st.write("✅ ตารางผลลัพธ์ (ข้อมูลที่ไม่มี eff และได้รับการเติมข้อมูลแล้ว)")
    st.dataframe(missing_eff)

    # ปุ่มดาวน์โหลด
    csv = missing_eff.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="💾 Download Result CSV",
        data=csv,
        file_name="filled_efficiency.csv",
        mime="text/csv"
    )

else:
    st.info("📥 กรุณาอัปโหลดไฟล์ทั้งหมดก่อนเริ่มทำงาน")
