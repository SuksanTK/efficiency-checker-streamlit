import pandas as pd

# =========================================================
# 📌 1. กำหนดชื่อไฟล์
# =========================================================
manpower_file = "lb_uc3_in_template_manpow.csv"
stylelist_file = "lb_uc3_in_template_style_list.csv"
raweff_file = "Raw_Eff_All_Shift MCU.csv"
output_file = "missing_eff.csv"

# =========================================================
# 📌 2. อ่านไฟล์ CSV ทั้ง 3 ไฟล์
# =========================================================
print("📖 กำลังอ่านข้อมูลจากไฟล์...")
manpower = pd.read_csv(manpower_file)
stylelist = pd.read_csv(stylelist_file)
raweff = pd.read_csv(raweff_file, low_memory=False)

# =========================================================
# 📌 3. ปรับชื่อคอลัมน์ทั้งหมดให้เป็นตัวพิมพ์เล็ก
# =========================================================
manpower.columns = manpower.columns.str.lower()
stylelist.columns = stylelist.columns.str.lower()
raweff.columns = raweff.columns.str.lower()

# =========================================================
# 📌 4. ตรวจสอบว่าคอลัมน์ที่ต้องใช้มีครบไหม
# =========================================================
required_cols_manpower = {"id", "line"}
required_cols_stylelist = {"line", "style"}
required_cols_raweff = {"id", "line", "eff"}

for name, df, required in [
    ("manpower", manpower, required_cols_manpower),
    ("stylelist", stylelist, required_cols_stylelist),
    ("raweff", raweff, required_cols_raweff)
]:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"❌ ไฟล์ {name} ขาดคอลัมน์เหล่านี้: {missing}")

# =========================================================
# 📌 5. รวมข้อมูล ID, Line, Style
# =========================================================
print("\n⚙️ กำลังรวมข้อมูล ID, Line, Style ...")
merged = pd.merge(manpower, stylelist, on="line", how="left")

final_table = merged[["id", "line", "style"]].copy()

# =========================================================
# 📌 6. เติมค่า eff โดย lookup จาก raweff
# =========================================================
print("🔍 กำลังเติมค่า eff ...")
final_table = pd.merge(final_table, raweff[["id", "line", "eff"]],
                       on=["id", "line"], how="left")

# =========================================================
# 📌 7. แสดงเฉพาะพนักงานที่ไม่มี eff เท่านั้น
# =========================================================
missing_eff = final_table[final_table["eff"].isna()]

if missing_eff.empty:
    print("\n✅ ไม่มีพนักงานที่ eff ว่าง ทุกคนมีข้อมูลครบแล้ว")
else:
    print("\n⚠️ พบพนักงานที่ยังไม่มี eff:")
    print(missing_eff[["id", "line", "style"]])
    missing_eff.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"💾 บันทึกไฟล์เฉพาะพนักงานที่ไม่มี eff แล้ว: {output_file}")
