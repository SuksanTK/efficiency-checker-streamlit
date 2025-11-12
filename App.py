import streamlit as st
import pandas as pd

st.set_page_config(page_title="Efficiency Checker (Advanced)", page_icon="📊", layout="wide")
st.title("📊 Efficiency Checker Tool (Advanced Version)")
st.write("อัปโหลดไฟล์ทั้ง 5 แล้วกดปุ่มเพื่อดูพนักงานที่ยังไม่มีค่า Eff พร้อมเติมข้อมูล GWC และ Jobtitle")

# ---------------------------------------------------------
# 1️⃣ Upload files
# ---------------------------------------------------------
manpower_file = st.file_uploader("📂 Upload Manpower CSV", type=["csv"])
stylelist_file = st.file_uploader("📂 Upload Stylelist CSV", type=["csv"])
raweff_file = st.file_uploader("📂 Upload Raweff CSV", type=["csv"])
ind_eff_file = st.file_uploader("📂 Upload Individual Efficiency CSV", type=["csv"])
master_gwc_file = st.file_uploader("📂 Upload Master GWC CSV", type=["csv"])

if all([manpower_file, stylelist_file, raweff_file, ind_eff_file, master_gwc_file]):
    st.success("✅ Upload ครบทั้ง 5 ไฟล์แล้ว พร้อมตรวจสอบ")

    if st.button("🚀 รันตรวจสอบข้อมูล"):
        # ---------------------------------------------------------
        # 2️⃣ Load data
        # ---------------------------------------------------------
        st.write("📖 กำลังอ่านข้อมูลจากไฟล์...")
        manpower = pd.read_csv(manpower_file)
        stylelist = pd.read_csv(stylelist_file)
        raweff = pd.read_csv(raweff_file, low_memory=False)
        ind_eff = pd.read_csv(ind_eff_file, low_memory=False)
        master_gwc = pd.read_csv(master_gwc_file)

        # แปลงชื่อคอลัมน์เป็นตัวพิมพ์เล็ก
        for df in [manpower, stylelist, raweff, ind_eff, master_gwc]:
            df.columns = df.columns.str.lower().str.strip()

        # ---------------------------------------------------------
        # 3️⃣ ตรวจสอบคอลัมน์ที่จำเป็น
        # ---------------------------------------------------------
        required_cols = {
            "manpower": {"id", "line", "jobtitle"},
            "stylelist": {"line", "style"},
            "raweff": {"id", "style", "eff", "jobtitle", "gwc"},
            "individual_efficiency": {"id", "eff %"},
            "master_gwc": {"style", "gwc"},
        }

        for name, req in required_cols.items():
            df = eval(name.replace("individual_efficiency", "ind_eff").replace("master_gwc", "master_gwc"))
            missing = req - set(df.columns)
            if missing:
                st.error(f"❌ ไฟล์ {name} ขาดคอลัมน์: {missing}")
                st.stop()

        # ---------------------------------------------------------
        # 4️⃣ รวมข้อมูลพื้นฐาน
        # ---------------------------------------------------------
        merged = pd.merge(manpower, stylelist, on="line", how="left")
        final_table = merged[["id", "line", "style", "jobtitle"]].copy()

        # เติมค่า GWC จาก Master GWC
        final_table = pd.merge(final_table, master_gwc[["style", "gwc"]], on="style", how="left")

        # เติมค่า eff จาก raweff (เชื่อมด้วย id + style)
        final_table = pd.merge(final_table, raweff[["id", "style", "eff"]], on=["id", "style"], how="left")

        # ---------------------------------------------------------
        # 5️⃣ เติม jobtitle ตามเงื่อนไข
        # ---------------------------------------------------------
        st.write("🧩 กำลังเติมค่า jobtitle ...")

        # step 1: lookup จาก raweff โดยใช้ id+gwc
        raweff["id_gwc_key"] = raweff["id"].astype(str) + "_" + raweff["gwc"].astype(str)
        final_table["id_gwc_key"] = final_table["id"].astype(str) + "_" + final_table["gwc"].astype(str)

        raweff_lookup = raweff[["id_gwc_key", "jobtitle"]].drop_duplicates()
        final_table = pd.merge(final_table, raweff_lookup, on="id_gwc_key", how="left", suffixes=("", "_from_raweff"))

        # ถ้า jobtitle เดิมว่าง → ใช้จาก raweff
        final_table["jobtitle"] = final_table["jobtitle"].fillna(final_table["jobtitle_from_raweff"])
        final_table = final_table.drop(columns=["jobtitle_from_raweff"])

        # step 2: ถ้ายังว่าง → ใช้จาก manpower โดย id
        mp_lookup = manpower[["id", "jobtitle"]].drop_duplicates()
        final_table = pd.merge(final_table, mp_lookup, on="id", how="left", suffixes=("", "_from_mp"))
        final_table["jobtitle"] = final_table["jobtitle"].fillna(final_table["jobtitle_from_mp"])
        final_table = final_table.drop(columns=["jobtitle_from_mp"])

        # ---------------------------------------------------------
        # 6️⃣ เติมค่า eff ที่หายไป
        # ---------------------------------------------------------
        st.write("⚙️ กำลังเติมค่า eff ที่หายไป ...")

        # step 1: เติมจาก raweff โดยใช้ id+gwc+jobtitle
        raweff["id_gwc_jobtitle_key"] = (
            raweff["id"].astype(str) + "_" + raweff["gwc"].astype(str) + "_" + raweff["jobtitle"].astype(str)
        )
        final_table["id_gwc_jobtitle_key"] = (
            final_table["id"].astype(str) + "_" + final_table["gwc"].astype(str) + "_" + final_table["jobtitle"].astype(str)
        )

        avg_eff_by_combo = raweff.groupby("id_gwc_jobtitle_key", as_index=False)["eff"].mean()
        final_table = pd.merge(final_table, avg_eff_by_combo, on="id_gwc_jobtitle_key", how="left", suffixes=("", "_avg_from_raweff"))
        final_table["eff"] = final_table["eff"].fillna(final_table["eff_avg_from_raweff"])
        final_table = final_table.drop(columns=["eff_avg_from_raweff"])

        # step 2: ถ้ายังว่าง → เติมจาก individual_efficiency โดย id
        ind_eff["eff %"] = pd.to_numeric(ind_eff["eff %"], errors="coerce")
        avg_ind_eff = ind_eff.groupby("id", as_index=False)["eff %"].mean().rename(columns={"eff %": "avg_eff"})
        final_table = pd.merge(final_table, avg_ind_eff, on="id", how="left")
        final_table["eff"] = final_table["eff"].fillna(final_table["avg_eff"])
        final_table = final_table.drop(columns=["avg_eff"])

        # ---------------------------------------------------------
        # 7️⃣ แสดงผลเฉพาะพนักงานที่ eff ยังว่าง
        # ---------------------------------------------------------
        missing_eff = final_table[final_table["eff"].isna()].sort_values(by=["line", "id"])

        if missing_eff.empty:
            st.success("✅ ไม่มีพนักงานที่ eff ว่าง ทุกคนมีข้อมูลครบแล้ว")
        else:
            st.warning(f"⚠️ พบพนักงานที่ไม่มี eff จำนวน {len(missing_eff)} คน")
            st.dataframe(missing_eff, use_container_width=True)

            csv = missing_eff.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="💾 ดาวน์โหลดไฟล์ missing_eff_with_gwc_jobtitle.csv",
                data=csv,
                file_name="missing_eff_with_gwc_jobtitle.csv",
                mime="text/csv"
            )

else:
    st.info("📥 กรุณาอัปโหลดไฟล์ CSV ทั้ง 5 ไฟล์ก่อนเริ่มทำงาน")
