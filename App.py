import streamlit as st
import pandas as pd

st.set_page_config(page_title="Efficiency Checker", page_icon="📊", layout="wide")

st.title("📊 Efficiency Checker & Auto-Filler Tool")

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
    st.info("📖 Reading all files...")
    manpower = pd.read_csv(manpower_file)
    stylelist = pd.read_csv(stylelist_file)
    raweff = pd.read_csv(raweff_file, low_memory=False)
    master_gwc = pd.read_csv(mastergwc_file)
    individual_eff = pd.read_csv(individual_eff_file)

    # lowercase
    manpower.columns = manpower.columns.str.lower()
    stylelist.columns = stylelist.columns.str.lower()
    raweff.columns = raweff.columns.str.lower()
    master_gwc.columns = master_gwc.columns.str.lower()
    individual_eff.columns = individual_eff.columns.str.lower()

    st.success("✅ Files loaded successfully!")

    # ---------------------------------------------------------
    # 2. Helper function to detect column names automatically
    # ---------------------------------------------------------
    def find_col(df, possible_names):
        for name in possible_names:
            if name in df.columns:
                return name
        return None

    id_col = find_col(manpower, ["id", "emp_id", "employee_id"])
    line_col_man = find_col(manpower, ["line", "line_no", "line number"])
    line_col_style = find_col(stylelist, ["line", "line_no", "line number"])
    style_col = find_col(stylelist, ["style", "style_code", "style no", "style number"])

    if not id_col or not line_col_man or not line_col_style or not style_col:
        st.error("❌ Missing one of these columns: id / line / style. Please check your CSV headers.")
        st.stop()

    # ---------------------------------------------------------
    # 3. Merge step 1: combine ID, Line, Style
    # ---------------------------------------------------------
    st.write("⚙️ Combining manpower and stylelist...")
    merged = pd.merge(manpower, stylelist, left_on=line_col_man, right_on=line_col_style, how="left")

    # ensure columns exist
    cols = [id_col, line_col_man, style_col]
    existing_cols = [c for c in cols if c in merged.columns]
    if len(existing_cols) < len(cols):
        st.error(f"❌ Missing columns after merge: {set(cols) - set(existing_cols)}")
        st.stop()

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
    final_table = pd.merge(final_table, raweff[["id", "style", eff_col]], on=["id", "style"], how="left")
    final_table.rename(columns={eff_col: "eff"}, inplace=True)

    # ---------------------------------------------------------
    # 5. Filter missing eff
    # ---------------------------------------------------------
    missing_eff = final_table[final_table["eff"].isna()].sort_values(by=["line", "id"]).copy()
    st.write(f"📊 Found {len(missing_eff)} rows with missing eff")

    # ---------------------------------------------------------
    # 6. Fill GWC and Jobtitle
    # ---------------------------------------------------------
    st.write("🧠 Filling GWC and Jobtitle ...")

    # 6.1 Fill GWC
    gwc_col = find_col(master_gwc, ["gwc", "gwc_code", "group"])
    if not gwc_col:
        st.error("❌ Master_GWC file missing GWC column.")
        st.stop()

    missing_eff = pd.merge(missing_eff, master_gwc[["style", gwc_col]], on="style", how="left")
    missing_eff.rename(columns={gwc_col: "gwc"}, inplace=True)

    # 6.2 Fill jobtitle (from raweff first)
    jobtitle_col = find_col(raweff, ["jobtitle", "job_title", "title"])
    if not jobtitle_col:
        st.warning("⚠️ No jobtitle column found in raweff; skipping this step.")
    else:
        missing_eff = pd.merge(
            missing_eff,
            raweff[["id", "gwc", jobtitle_col]],
            on=["id", "gwc"],
            how="left",
            suffixes=("", "_from_raweff")
        )
        # if still null, fill from manpower
        if "jobtitle" not in missing_eff.columns:
            missing_eff["jobtitle"] = missing_eff[jobtitle_col + "_from_raweff"]
        missing_eff["jobtitle"] = missing_eff["jobtitle"].fillna(
            missing_eff.merge(manpower[["id", jobtitle_col]], on="id", how="left")[jobtitle_col + "_y"]
        )

    # ---------------------------------------------------------
    # 7. Fill eff with avg from raweff or individual_eff
    # ---------------------------------------------------------
    st.write("⚙️ Filling missing eff with averages ...")

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
    # 8. Display final table
    # ---------------------------------------------------------
    st.write("✅ Final result (rows originally missing eff, now filled):")
    st.dataframe(missing_eff, use_container_width=True)

    csv = missing_eff.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("💾 Download Result CSV", csv, "filled_efficiency.csv", "text/csv")

else:
    st.info("📥 Please upload all 5 CSV files before running the process.")
