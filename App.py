import streamlit as st
import pandas as pd

st.set_page_config(page_title="Efficiency Checker (Advanced)", page_icon="📊", layout="wide")
st.title("📊 Efficiency Checker Tool (Advanced Version)")
st.write("อัปโหลดไฟล์ทั้ง 5 แล้วกดปุ่มเพื่อดูพนักงานที่ยังไม่มีค่า Eff (ก่อนเติมข้อมูล) พร้อมผลลัพธ์หลังเติมตามเงื่อนไข")
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Efficiency Checker (Advanced)", page_icon="📊", layout="wide")
st.title("📊 Efficiency Checker Tool (Advanced Version)")
st.write("อัปโหลดไฟล์ทั้ง 5 แล้วกดปุ่มเพื่อดูพนักงานที่ยังไม่มีค่า Eff (ก่อนเติมข้อมูล) พร้อมผลลัพธ์หลังเติมตามเงื่อนไข")

# ---------------------------------------------------------
# 1️⃣ Upload files
# ---------------------------------------------------------
manpower_file = st.file_uploader("📂 Upload Manpower CSV", type=["csv"])
stylelist_file = st.file_uploader("📂 Upload Stylelist CSV", type=["csv"], key="stylelist")
raweff_file = st.file_uploader("📂 Upload Raweff CSV", type=["csv"], key="raweff")
ind_eff_file = st.file_uploader("📂 Upload Individual Efficiency CSV", type=["csv"], key="ind_eff")
master_gwc_file = st.file_uploader("📂 Upload Master GWC CSV", type=["csv"], key="master_gwc")

if all([manpower_file, stylelist_file, raweff_file, ind_eff_file, master_gwc_file]):
    st.success("✅ Upload ครบทั้ง 5 ไฟล์แล้ว พร้อมตรวจสอบ")

    if st.button("🚀 รันตรวจสอบข้อมูล"):
        # ---------------------------------------------------------
        # 2️⃣ Load data
        # ---------------------------------------------------------
        st.write("📖 กำลังอ่านข้อมูลจากไฟล์...")
        try:
            manpower = pd.read_csv(manpower_file)
            stylelist = pd.read_csv(stylelist_file)
            raweff = pd.read_csv(raweff_file, low_memory=False)
            ind_eff = pd.read_csv(ind_eff_file, low_memory=False)
            master_gwc = pd.read_csv(master_gwc_file)
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
            st.stop()


        # แปลงชื่อคอลัมน์เป็นตัวพิมพ์เล็กและตัดช่องว่าง
        for df in [manpower, stylelist, raweff, ind_eff, master_gwc]:
            df.columns = df.columns.str.lower().str.strip()

        # ---------------------------------------------------------
        # ⭐ การปรับแก้: กำหนดมาตรฐานชนิดข้อมูลสำหรับคีย์การเชื่อมต่อ (id, style)
        # เพื่อให้แน่ใจว่าการ Merge ในขั้นตอนที่ 4 และ 6 ทำงานอย่างถูกต้อง
        # ---------------------------------------------------------
        
        # Standardize 'id' to string
        for df in [manpower, raweff, ind_eff]:
            if 'id' in df.columns:
                df['id'] = df['id'].astype(str).str.strip()
        
        # Standardize 'style' to string
        for df in [stylelist, raweff, master_gwc]:
            if 'style' in df.columns:
                df['style'] = df['style'].astype(str).str.strip()

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
            # Use dictionary comprehension for eval equivalent
            df_map = {"manpower": manpower, "stylelist": stylelist, "raweff": raweff, "ind_eff": ind_eff, "master_gwc": master_gwc}
            df_key = name.replace("individual_efficiency", "ind_eff").replace("master_gwc", "master_gwc")
            df = df_map[df_key]
            
            missing = req - set(df.columns)
            if missing:
                st.error(f"❌ ไฟล์ {name} ขาดคอลัมน์: {missing}")
                st.stop()

        # ---------------------------------------------------------
        # 4️⃣ รวมข้อมูลพื้นฐานและกรองหา "ไม่มี eff เดิม"
        # ---------------------------------------------------------
        st.write("🔗 กำลังรวมข้อมูลพื้นฐาน...")
        merged = pd.merge(manpower, stylelist, on="line", how="left")
        final_table = merged[["id", "line", "style", "jobtitle"]].copy()

        # 4.1 เติมค่า GWC จาก Master GWC
        final_table = pd.merge(final_table, master_gwc[["style", "gwc"]], on="style", how="left")

        # 4.2 Aggregate existing eff จาก raweff ก่อน merge 
        # เพื่อป้องกันการซ้ำซ้อนและรับประกันว่ามี eff เดิมเพียงค่าเดียว (ค่าเฉลี่ย) สำหรับแต่ละ (id, style)
        existing_eff_agg = raweff.groupby(["id", "style"], as_index=False)["eff"].mean().rename(columns={"eff": "existing_eff"})
        
        # เติมค่า eff จาก raweff (เชื่อมด้วย id + style) - ใช้ค่าเฉลี่ยหากมีหลายรายการ
        # Merge เข้ามาในคอลัมน์ใหม่ชื่อ 'existing_eff' เพื่อความชัดเจน
        final_table = pd.merge(final_table, existing_eff_agg, on=["id", "style"], how="left")

        # --- 🔍 เก็บชุดข้อมูลที่ "ไม่มี eff เดิม" ก่อนจะเติม ---
        # กรองเฉพาะแถวที่คอลัมน์ 'existing_eff' (ที่ถูก merge เข้ามา) เป็น NaN
        # และสร้างคอลัมน์ 'eff' สำหรับการเติมในขั้นตอนถัดไป
        missing_eff_initial = final_table[final_table["existing_eff"].isna()].copy()
        
        # คัดลอกค่า existing_eff มาใส่ใน eff เพื่อเริ่มกระบวนการเติมค่า
        missing_eff_initial['eff'] = missing_eff_initial['existing_eff']
        
        # ลบคอลัมน์ existing_eff ออกจากชุดข้อมูลที่ใช้ process ต่อ
        missing_eff_initial = missing_eff_initial.drop(columns=['existing_eff'])


        # ---------------------------------------------------------
        # 5️⃣ เติม jobtitle ตามเงื่อนไข (ในชุดข้อมูลที่ไม่มี eff)
        # ---------------------------------------------------------
        st.write("🧩 กำลังเติมค่า jobtitle ...")

        # step 1: lookup จาก raweff โดยใช้ id + gwc
        raweff["id_gwc_key"] = raweff["id"].astype(str) + "_" + raweff["gwc"].astype(str)
        missing_eff_initial["id_gwc_key"] = missing_eff_initial["id"].astype(str) + "_" + missing_eff_initial["gwc"].astype(str)

        raweff_lookup = raweff[["id_gwc_key", "jobtitle"]].drop_duplicates()
        missing_eff_initial = pd.merge(missing_eff_initial, raweff_lookup, on="id_gwc_key", how="left", suffixes=("", "_from_raweff"))

        missing_eff_initial["jobtitle"] = missing_eff_initial["jobtitle"].fillna(missing_eff_initial["jobtitle_from_raweff"])
        missing_eff_initial = missing_eff_initial.drop(columns=["jobtitle_from_raweff"])

        # step 2: ถ้ายังว่าง → ใช้จาก manpower โดย id
        mp_lookup = manpower[["id", "jobtitle"]].drop_duplicates()
        missing_eff_initial = pd.merge(missing_eff_initial, mp_lookup, on="id", how="left", suffixes=("", "_from_mp"))
        missing_eff_initial["jobtitle"] = missing_eff_initial["jobtitle"].fillna(missing_eff_initial["jobtitle_from_mp"])
        missing_eff_initial = missing_eff_initial.drop(columns=["jobtitle_from_mp"])

        # ---------------------------------------------------------
        # 6️⃣ เติมค่า eff ที่หายไป (ในชุดข้อมูลที่ไม่มี eff)
        # ---------------------------------------------------------
        st.write("⚙️ กำลังเติมค่า eff ที่หายไป ...")

        # step 1: เติมจาก raweff โดยใช้ค่าเฉลี่ยจาก id+gwc+jobtitle
        raweff["id_gwc_jobtitle_key"] = (
            raweff["id"].astype(str) + "_" + raweff["gwc"].astype(str) + "_" + raweff["jobtitle"].astype(str)
        )
        missing_eff_initial["id_gwc_jobtitle_key"] = (
            missing_eff_initial["id"].astype(str) + "_" + missing_eff_initial["gwc"].astype(str) + "_" + missing_eff_initial["jobtitle"].astype(str)
        )

        # คำนวณค่าเฉลี่ย eff จาก raweff
        avg_eff_by_combo = raweff.groupby("id_gwc_jobtitle_key", as_index=False)["eff"].mean().rename(columns={"eff": "eff_avg_from_raweff"})
        
        # Merge และเติมค่า
        missing_eff_initial = pd.merge(
            missing_eff_initial, avg_eff_by_combo, on="id_gwc_jobtitle_key", how="left"
        )
        missing_eff_initial["eff"] = missing_eff_initial["eff"].fillna(missing_eff_initial["eff_avg_from_raweff"])
        missing_eff_initial = missing_eff_initial.drop(columns=["eff_avg_from_raweff"])

        # step 2: ถ้ายังว่าง → เติมจาก individual_efficiency โดย id
        # Clean and convert 'eff %' to numeric first
        ind_eff["eff %"] = pd.to_numeric(ind_eff["eff %"], errors="coerce")
        avg_ind_eff = ind_eff.groupby("id", as_index=False)["eff %"].mean().rename(columns={"eff %": "avg_eff"})
        missing_eff_initial = pd.merge(missing_eff_initial, avg_ind_eff, on="id", how="left")
        missing_eff_initial["eff"] = missing_eff_initial["eff"].fillna(missing_eff_initial["avg_eff"])
        missing_eff_initial = missing_eff_initial.drop(columns=["avg_eff"])
        
        # ---------------------------------------------------------
        # 7️⃣ แสดงผล "หลังจากเติมข้อมูลแล้ว"
        # ---------------------------------------------------------
        st.success(f"✅ พบพนักงานที่ไม่มี eff เดิมทั้งหมด {len(missing_eff_initial)} แถว (หลังเติมข้อมูลแล้ว)")

        # เลือกคอลัมน์ที่ต้องการแสดงผลและเปลี่ยนชื่อคอลัมน์ให้เป็นภาษาไทยเพื่อความสวยงาม
        display_cols = missing_eff_initial[["id", "line", "style", "jobtitle", "gwc", "eff"]].copy()
        # ทำการปัดเศษค่า eff ให้เหลือ 2 ตำแหน่งทศนิยม
        display_cols['eff'] = display_cols['eff'].round(2)
        
        display_cols.columns = ["ID", "Line", "Style", "Job Title", "GWC", "Efficiency (Filled)"]
        
        st.dataframe(display_cols, use_container_width=True)

        # เตรียมไฟล์ CSV สำหรับดาวน์โหลด (ใช้ dataframe เดิมที่มีข้อมูลดิบสำหรับการส่งออก)
        csv = missing_eff_initial.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="💾 ดาวน์โหลดไฟล์ filled_eff_result.csv",
            data=csv,
            file_name="filled_eff_result.csv",
            mime="text/csv"
        )

else:
    st.info("📥 กรุณาอัปโหลดไฟล์ CSV ทั้ง 5 ไฟล์ก่อนเริ่มทำงาน")
# ---------------------------------------------------------
# 1️⃣ Upload files
# ---------------------------------------------------------
manpower_file = st.file_uploader("📂 Upload Manpower CSV", type=["csv"])
stylelist_file = st.file_uploader("📂 Upload Stylelist CSV", type=["csv"])
raweff_file = st.file_uploader("📂 Upload Raweff CSV", type=["csv"], key="raweff")
ind_eff_file = st.file_uploader("📂 Upload Individual Efficiency CSV", type=["csv"], key="ind_eff")
master_gwc_file = st.file_uploader("📂 Upload Master GWC CSV", type=["csv"], key="master_gwc")

if all([manpower_file, stylelist_file, raweff_file, ind_eff_file, master_gwc_file]):
    st.success("✅ Upload ครบทั้ง 5 ไฟล์แล้ว พร้อมตรวจสอบ")

    if st.button("🚀 รันตรวจสอบข้อมูล"):
        # ---------------------------------------------------------
        # 2️⃣ Load data
        # ---------------------------------------------------------
        st.write("📖 กำลังอ่านข้อมูลจากไฟล์...")
        try:
            manpower = pd.read_csv(manpower_file)
            stylelist = pd.read_csv(stylelist_file)
            raweff = pd.read_csv(raweff_file, low_memory=False)
            ind_eff = pd.read_csv(ind_eff_file, low_memory=False)
            master_gwc = pd.read_csv(master_gwc_file)
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
            st.stop()


        # แปลงชื่อคอลัมน์เป็นตัวพิมพ์เล็กและตัดช่องว่าง
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
            # Use dictionary comprehension for eval equivalent
            df_map = {"manpower": manpower, "stylelist": stylelist, "raweff": raweff, "ind_eff": ind_eff, "master_gwc": master_gwc}
            df_key = name.replace("individual_efficiency", "ind_eff").replace("master_gwc", "master_gwc")
            df = df_map[df_key]
            
            missing = req - set(df.columns)
            if missing:
                st.error(f"❌ ไฟล์ {name} ขาดคอลัมน์: {missing}")
                st.stop()

        # ---------------------------------------------------------
        # 4️⃣ รวมข้อมูลพื้นฐานและกรองหา "ไม่มี eff เดิม"
        # ---------------------------------------------------------
        st.write("🔗 กำลังรวมข้อมูลพื้นฐาน...")
        merged = pd.merge(manpower, stylelist, on="line", how="left")
        final_table = merged[["id", "line", "style","jobtitle"]].copy()

        # 4.1 เติมค่า GWC จาก Master GWC
        final_table = pd.merge(final_table, master_gwc[["style", "gwc"]], on="style", how="left")

        # 4.2 **แก้ไข: Aggregate existing eff จาก raweff ก่อน merge** # เพื่อป้องกันการซ้ำซ้อนและรับประกันว่ามี eff เดิมเพียงค่าเดียว (ค่าเฉลี่ย) สำหรับแต่ละ (id, style) 
        existing_eff_agg = raweff.groupby(["id", "style"], as_index=False)["eff"].mean()
        
        # เติมค่า eff จาก raweff (เชื่อมด้วย id + style) - ใช้ค่าเฉลี่ยหากมีหลายรายการ
        final_table = pd.merge(final_table, existing_eff_agg, on=["id", "style"], how="left")

        # --- 🔍 เก็บชุดข้อมูลที่ "ไม่มี eff เดิม" ก่อนจะเติม ---
        # กรองเฉพาะแถวที่คอลัมน์ 'eff' (ที่ถูก merge เข้ามา) เป็น NaN
        missing_eff_initial = final_table[final_table["eff"].isna()].copy()

        # ---------------------------------------------------------
        # 5️⃣ เติม jobtitle ตามเงื่อนไข (ในชุดข้อมูลที่ไม่มี eff)
        # ---------------------------------------------------------
        st.write("🧩 กำลังเติมค่า jobtitle ...")

        # step 1: lookup จาก raweff โดยใช้ id + gwc
        raweff["id_gwc_key"] = raweff["id"].astype(str) + "_" + raweff["gwc"].astype(str)
        missing_eff_initial["id_gwc_key"] = missing_eff_initial["id"].astype(str) + "_" + missing_eff_initial["gwc"].astype(str)

        raweff_lookup = raweff[["id_gwc_key", "jobtitle"]].drop_duplicates()
        missing_eff_initial = pd.merge(missing_eff_initial, raweff_lookup, on="id_gwc_key", how="left", suffixes=("", "_from_raweff"))

        missing_eff_initial["jobtitle"] = missing_eff_initial["jobtitle"].fillna(missing_eff_initial["jobtitle_from_raweff"])
        missing_eff_initial = missing_eff_initial.drop(columns=["jobtitle_from_raweff"])

        # step 2: ถ้ายังว่าง → ใช้จาก manpower โดย id
        mp_lookup = manpower[["id", "jobtitle"]].drop_duplicates()
        missing_eff_initial = pd.merge(missing_eff_initial, mp_lookup, on="id", how="left", suffixes=("", "_from_mp"))
        missing_eff_initial["jobtitle"] = missing_eff_initial["jobtitle"].fillna(missing_eff_initial["jobtitle_from_mp"])
        missing_eff_initial = missing_eff_initial.drop(columns=["jobtitle_from_mp"])

        # ---------------------------------------------------------
        # 6️⃣ เติมค่า eff ที่หายไป (ในชุดข้อมูลที่ไม่มี eff)
        # ---------------------------------------------------------
        st.write("⚙️ กำลังเติมค่า eff ที่หายไป ...")

        # step 1: เติมจาก raweff โดยใช้ค่าเฉลี่ยจาก id+gwc+jobtitle
        raweff["id_gwc_jobtitle_key"] = (
            raweff["id"].astype(str) + "_" + raweff["gwc"].astype(str) + "_" + raweff["jobtitle"].astype(str)
        )
        missing_eff_initial["id_gwc_jobtitle_key"] = (
            missing_eff_initial["id"].astype(str) + "_" + missing_eff_initial["gwc"].astype(str) + "_" + missing_eff_initial["jobtitle"].astype(str)
        )

        # คำนวณค่าเฉลี่ย eff จาก raweff
        avg_eff_by_combo = raweff.groupby("id_gwc_jobtitle_key", as_index=False)["eff"].mean().rename(columns={"eff": "eff_avg_from_raweff"})
        
        # Merge และเติมค่า
        missing_eff_initial = pd.merge(
            missing_eff_initial, avg_eff_by_combo, on="id_gwc_jobtitle_key", how="left"
        )
        missing_eff_initial["eff"] = missing_eff_initial["eff"].fillna(missing_eff_initial["eff_avg_from_raweff"])
        missing_eff_initial = missing_eff_initial.drop(columns=["eff_avg_from_raweff"])

        # step 2: ถ้ายังว่าง → เติมจาก individual_efficiency โดย id
        # Clean and convert 'eff %' to numeric first
        ind_eff["eff %"] = pd.to_numeric(ind_eff["eff %"], errors="coerce")
        avg_ind_eff = ind_eff.groupby("id", as_index=False)["eff %"].mean().rename(columns={"eff %": "avg_eff"})
        missing_eff_initial = pd.merge(missing_eff_initial, avg_ind_eff, on="id", how="left")
        missing_eff_initial["eff"] = missing_eff_initial["eff"].fillna(missing_eff_initial["avg_eff"])
        missing_eff_initial = missing_eff_initial.drop(columns=["avg_eff"])
        
        # ---------------------------------------------------------
        # 7️⃣ แสดงผล "หลังจากเติมข้อมูลแล้ว"
        # ---------------------------------------------------------
        st.success(f"✅ พบพนักงานที่ไม่มี eff เดิมทั้งหมด {len(missing_eff_initial)} แถว (หลังเติมข้อมูลแล้ว)")

        # เลือกคอลัมน์ที่ต้องการแสดงผลและเปลี่ยนชื่อคอลัมน์ให้เป็นภาษาไทยเพื่อความสวยงาม
        display_cols = missing_eff_initial[["id", "line", "style", "jobtitle", "gwc", "eff", "id_gwc_key", "id_gwc_jobtitle_key"]].copy()
        # ทำการปัดเศษค่า eff ให้เหลือ 2 ตำแหน่งทศนิยม
        display_cols['eff'] = display_cols['eff'].round(2)
        
        display_cols.columns = ["ID", "Line", "Style", "Job Title", "GWC", "Efficiency (Filled)", "ID_GWC_Key", "ID_GWC_JobTitle_Key"]
        
        st.dataframe(display_cols, use_container_width=True)

        # เตรียมไฟล์ CSV สำหรับดาวน์โหลด (ใช้ dataframe เดิมที่มีข้อมูลดิบสำหรับการส่งออก)
        csv = missing_eff_initial.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="💾 ดาวน์โหลดไฟล์ filled_eff_result.csv",
            data=csv,
            file_name="filled_eff_result.csv",
            mime="text/csv"
        )

else:
    st.info("📥 กรุณาอัปโหลดไฟล์ CSV ทั้ง 5 ไฟล์ก่อนเริ่มทำงาน")
