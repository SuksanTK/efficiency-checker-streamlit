import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 0. PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="Efficiency Checker", page_icon="📊", layout="wide")
st.title("📊 Efficiency Checker & Auto-Filler Tool")

# ---------------------------------------------------------
# 1. UPLOAD CSV FILES
# ---------------------------------------------------------
st.header("📂 Upload Required CSV Files")
manpower_file = st.file_uploader("Upload manpower file", type=["csv"])
stylelist_file = st.file_uploader("Upload stylelist file", type=["csv"])
raweff_file = st.file_uploader("Upload raweff file", type=["csv"])
mastergwc_file = st.file_uploader("Upload Master_GWC file", type=["csv"])
individual_eff_file = st.file_uploader("Upload individual_efficiency file", type=["csv"])

# ---------------------------------------------------------
# 2. PROCESS FILES
# ---------------------------------------------------------
if all([manpower_file, stylelist_file, raweff_file, mastergwc_file, individual_eff_file]):

    st.info("📖 Reading and preparing files...")
    manpower = pd.read_csv(manpower_file)
    stylelist = pd.read_csv(stylelist_file)
    raweff = pd.read_csv(raweff_file, low_memory=False)
    master_gwc = pd.read_csv(mastergwc_file)
    individual_eff = pd.read_csv(individual_eff_file)

    # Convert column names to lowercase
    for df in [manpower, stylelist, raweff, master_gwc, individual_eff]:
        df.columns = df.columns.str.lower()

    st.success("✅ Files loaded successfully!")

    # ---------------------------------------------------------
    # Helper function to find column names automatically
    # ---------------------------------------------------------
    def find_col(df, possible_names):
        for name in possible_names:
            if name in df.columns:
                return name
        return None

    # Detect main columns
    id_col = find_col(manpower, ["id", "emp_id", "employee_id"])
    line_col_man = find_col(manpower, ["line", "line_no", "line number"])
    line_col_style = find_col(stylelist, ["line", "line_no", "line number"])
    style_col = find_col(stylelist, ["style", "style_code", "style no", "style number"])

    if not id_col or not line_col_man or not line_col_style or not style_col:
        st.error("❌ Missing one of these columns: id / line / style.")
        st.stop()

    # ---------------------------------------------------------
    # 3. Merge Step 1: combine ID + Line + Style
    # ---------------------------------------------------------
    st.write("⚙️ Combining manpower and stylelist ...")
    merged = pd.merge(
        manpower, stylelist,
        left_on=line_col_man,
        right_on=line_col_style,
        how="left"
    )

    final_table = merged[[id_col, line_col_man, style_col]].copy()
    final_table.columns = ["id", "line", "style"]

    # ---------------------------------------------------------
    # 4. Merge eff from raweff
    # ---------------------------------------------------------
    eff_col = find_col(raweff, ["eff", "efficiency", "eff %"])
    if not eff_col:
        st.error("❌ Could not find 'eff' column in raweff file.")
        st.stop()

    st.write("🔍 Filling eff from raweff ...")
    final_table = pd.merge(final_table, raweff[["id", "style", eff_col]],
                           on=["id", "style"], how="left")
    final_table.rename(columns={eff_col: "eff"}, inplace=True)

    # ---------------------------------------------------------
    # 5. Filter only missing eff
    # ---------------------------------------------------------
    missing_eff = final_table[final_table["eff"].isna()].sort_values(by=["line", "id"]).copy()
    st.write(f"📊 Found {len(missing_eff)} rows with missing eff")

    # ---------------------------------------------------------
    # 6. Fill GWC and Jobtitle
    # ---------------------------------------------------------
    st.write("🧠 Filling GWC and Jobtitle ...")

    # 6.1 Fill GWC
    gwc_col = find_col(master_gwc, ["gwc", "gwc_code", "group"])
    if gwc_col:
        missing_eff = pd.merge(missing_eff, master_gwc[["style", gwc_col]], on="style", how="left")
        missing_eff.rename(columns={gwc_col: "gwc"}, inplace=True)
    else:
        st.warning("⚠️ No GWC column found in Master_GWC file.")

    # 6.2 Fill Jobtitle
    jobtitle_col_raw = find_col(raweff, ["jobtitle", "job_title", "title"])
    jobtitle_col_man = find_col(manpower, ["jobtitle", "job_title", "title"])

    if jobtitle_col_raw:
        missing_eff = pd.merge(
            missing_eff,
            raweff[["id", "gwc", jobtitle_col_raw]],
            on=["id", "gwc"],
            how="left",
            suffixes=("", "_raw")
        )
        missing_eff["jobtitle"] = missing_eff[jobtitle_col_raw].fillna(missing_eff[jobtitle_col_raw + "_raw"])
    else:
        missing_eff["jobtitle"] = None

    # ถ้ายังไม่มีค่า jobtitle ให้เติมจาก manpower
    if jobtitle_col_man:
        missing_eff = pd.merge(
            missing_eff,
            manpower[["id", jobtitle_col_man]],
            on="id",
            how="left",
            suffixes=("", "_man")
        )
        missing_eff["jobtitle"] = missing_eff["jobtitle"].fillna(missing_eff[jobtitle_col_man + "_man"])

    # ---------------------------------------------------------
    # 7. Fill missing eff using averages
    # ---------------------------------------------------------
    st.write("⚙️ Filling missing eff from averages ...")

    eff_fill = raweff.groupby(["id", "gwc", "jobtitle"], dropna=False)["eff"].mean().reset_index()
    missing_eff = pd.merge(
        missing_eff,
        eff_fill,
        on=["id", "gwc", "jobtitle"],
        how="left",
        suffixes=("", "_avg")
    )

    missing_eff["eff"] = missing_eff["eff"].fillna(missing_eff["eff_avg"])

    # Fill from individual_eff if still missing
    eff_ind_col = find_col(individual_eff, ["eff %", "eff", "efficiency"])
    if eff_ind_col:
        missing_eff = pd.merge(
            missing_eff,
            individual_eff[["id", eff_ind_col]].rename(columns={eff_ind_col: "eff_from_individual"}),
            on="id",
            how="left"
        )
        missing_eff["eff"] = missing_eff["eff"].fillna(missing_eff["eff_from_individual"])

    # ---------------------------------------------------------
    # 8. Combine with original (to show full dataset)
    # ---------------------------------------------------------
    filled_all = pd.merge(
        final_table,
        missing_eff[["id", "line", "style", "gwc", "jobtitle", "eff"]],
        on=["id", "line", "style"],
        how="left",
        suffixes=("", "_new")
    )

    # ใช้ค่าที่เติมใหม่ ถ้ามี
    filled_all["eff"] = filled_all["eff"].fillna(filled_all["eff_new"])
    filled_all.drop(columns=["eff_new"], inplace=True)

    # ---------------------------------------------------------
    # 9. Display Final Result
    # ---------------------------------------------------------
    st.success("✅ Final dataset ready!")
    st.dataframe(filled_all, width='stretch')

    csv = filled_all.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("💾 Download Filled Efficiency CSV", csv, "filled_efficiency.csv", "text/csv")

else:
    st.info("📥 Please upload all 5 CSV files before running the process.")
