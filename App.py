import streamlit as st
import pandas as pd

st.set_page_config(page_title="Efficiency Checker", page_icon="📊", layout="wide")

st.title("📊 Efficiency Checker Tool (v2)")
st.write("อัปโหลดไฟล์ทั้ง 4 แล้วกดปุ่มเพื่อดูพนักงานที่ยังไม่มีค่า Eff พร้อมข้อมูล Jobtitle และค่าเฉลี่ย Eff %")

# ---------------------------------------------------------
# 1. Upload files
# ---------------------------------------------------------
manpower_file = st.file_uploader("📂 Upload Manpower CSV", type=["csv"])
stylelist_file = st.file_uploader("📂 Upload Stylelist CSV", type=["csv"])
raweff_file = st.file_uploader("📂 Upload Raweff CSV", type=["csv"])
individual_eff_file = st.file_uploader("📂 Upload Individual Efficiency CSV", type=["csv"])

if manpower_file and stylelist_file and raweff_file and individual_eff_file:
    st.success("✅ Upload ครบทั้ง 4 ไฟล์แล้ว พร้อมตรวจสอบ")

    if st.button("🚀 รันตรวจสอบข้อมูล"):
        # ---------------------------------------------------------
        # 2. Load data
        # ---------------------------------------------------------
        st.write("📖 กำลังอ่านข้อมูลจากไฟล์...")
        manpower = pd.read_csv(manpower_file)
        stylelist = pd.read_csv(stylelist_file)
        raweff = pd.read_csv(raweff_file, low_memory=False)
        ind_eff = pd.read_csv(individual_eff_file, low_memory=False)

        # lowercase columns เพื่อป้องกันชื่อคอลัมน์ mismatch
        manpower.columns = manpower.columns.str.lower()
        stylelist.columns = stylelist.columns.str.lower()
        raweff.columns = raweff.columns.str.lower()
        ind_eff.columns = ind_eff.columns.str.lower()

        # ---------------------------------------------------------
        # 3. ตรวจสอบคอลัมน์ที่จำเป็น
        # ---------------------------------------------------------
        required_cols_manpower = {"id", "line", "jobtitle"}
        required_cols_stylelist = {"line", "style"}
        required_cols_raweff = {"id", "line", "eff"}
        required_cols_ind_eff = {"id", "eff %"}  # eff % เป็นคอลัมน์จาก individual_efficiency

        for name, df, required in [
            ("manpower", manpower, required_cols_manpower),
            ("stylelist", stylelist, required_cols_stylelist),
            ("raweff", raweff, required_cols_raweff),
            ("individual_efficiency", ind_eff, required_cols_ind_eff)
        ]:
            missing = required - set(df.columns)
            if missing:
                st.error(f"❌ ไฟล์ {name} ขาดคอลัมน์: {missing}")
                st.stop()

        # ---------------------------------------------------------
        # 4. Merge data
        # ---------------------------------------------------------
        st.write("⚙️ กำลังรวมข้อมูล ID, Line, Style ...")
        merged = pd.merge(manpower, stylelist, on="line", how="left")
        final_table = merged[["id", "line", "style", "jobtitle"]].copy()

        # เติม eff จาก raweff
        st.write("🔍 กำลังเติมค่า eff ...")
        final_table = pd.merge(final_table, raweff[["id", "style", "eff"]],
                               on=["id", "style"], how="left")

        # ---------------------------------------------------------
        # 5. หา missing eff
        # ---------------------------------------------------------
        missing_eff = final_table[final_table["eff"].isna()].sort_values(by=["line", "id"]).copy()

        if missing_eff.empty:
            st.success("✅ ไม่มีพนักงานที่ eff ว่าง ทุกคนมีข้อมูลครบแล้ว")
        else:
            st.warning(f"⚠️ พบพนักงานที่ไม่มี eff จำนวน {len(missing_eff)} คน")

            # ---------------------------------------------------------
            # 6. คำนวณค่าเฉลี่ย eff % จากไฟล์ individual_efficiency
            # ---------------------------------------------------------
            st.write("📊 กำลังคำนวณค่าเฉลี่ย eff % จาก individual_efficiency.csv ...")

            # แปลงค่าคอลัมน์ eff % ให้เป็นตัวเลข
            ind_eff["eff %"] = pd.to_numeric(ind_eff["eff %"], errors="coerce")

            # คำนวณค่าเฉลี่ยต่อ ID
            avg_eff_by_id = ind_eff.groupby("id", as_index=False)["eff %"].mean()
            avg_eff_by_id = avg_eff_by_id.rename(columns={"eff %": "avg_eff"})

            # รวมค่าเฉลี่ยเข้ากับ missing_eff
            missing_eff = pd.merge(missing_eff, avg_eff_by_id, on="id", how="left")

            # ---------------------------------------------------------
            # 7. แสดงผลลัพธ์
            # ---------------------------------------------------------
            st.dataframe(missing_eff, use_container_width=True)

            # ---------------------------------------------------------
            # 8. ปุ่มดาวน์โหลดผลลัพธ์
            # ---------------------------------------------------------
            csv = missing_eff.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="💾 ดาวน์โหลดไฟล์ missing_eff_with_jobtitle_avg.csv",
                data=csv,
                file_name="missing_eff_with_jobtitle_avg.csv",
                mime="text/csv"
            )

else:
    st.info("📥 กรุณาอัปโหลดไฟล์ CSV ทั้ง 4 ไฟล์ก่อนเริ่มทำงาน")
