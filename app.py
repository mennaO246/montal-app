import io, json
import streamlit as st
import pandas as pd
from layout import (Rules, Opening, Wall, Project, build_project, summary,
                    project_to_dict, project_from_dict, ayman_project)
from drawing import elevation_svg, iso_svg

st.set_page_config(page_title="مصمم دواليب مونتال", page_icon="🪑", layout="centered",
                   initial_sidebar_state="collapsed")
st.markdown("""<style>
html, body, .stApp {direction: rtl; text-align: right;}
h1 {font-size: 1.5rem !important;} h2, h3 {font-size: 1.2rem !important; text-align: right;}
.stButton button, .stDownloadButton button {width: 100%; min-height: 3rem; font-size: 1rem;}
input {font-size: 1.05rem !important;}
[data-testid="stMetricValue"], .stDataFrame {direction: ltr;}
.block-container {padding: 1rem 0.8rem 4rem 0.8rem;}
</style>""", unsafe_allow_html=True)

SIDES = {"يمين": "right", "يسار": "left", "لا يوجد": "none"}
SIDES_R = {v: k for k, v in SIDES.items()}
STOR = {"فوق كل العلوي": "all", "فوق الركنة فقط": "corner", "لا يوجد": "none"}
STOR_R = {v: k for k, v in STOR.items()}
KIND = {"باب": "door", "شباك": "window"}
KIND_R = {v: k for k, v in KIND.items()}


def show_svg(svg, caption=None):
    st.image(svg, width="stretch", caption=caption)


if "proj" not in st.session_state:
    st.session_state.proj = project_to_dict(ayman_project())
    st.session_state.ver = 0
P0 = st.session_state.proj
V = st.session_state.ver

st.title("🪑 مصمم دواليب مونتال")
st.caption("اكتبي المقاسات تحت، والنتيجة (جداول + رسومات) بتظهر في الآخر.")

# ------------------------------------------------------------------ project / rules
with st.expander("📂 فتح / مشروع جديد"):
    up = st.file_uploader("فتح مشروع محفوظ (ملف JSON)", type="json", key=f"up{V}")
    if up is not None:
        try:
            st.session_state.proj = project_to_dict(project_from_dict(json.load(up)))
            st.session_state.ver += 1
            st.rerun()
        except Exception:
            st.error("الملف مش مشروع صالح.")
    if st.button("↺ مثال: مشروع أيمن"):
        st.session_state.proj = project_to_dict(ayman_project()); st.session_state.ver += 1; st.rerun()
    if st.button("🆕 مشروع جديد"):
        st.session_state.proj = project_to_dict(Project("", "L", [Wall("A", 300, [], "right"), Wall("B", 200, [], "left")]))
        st.session_state.ver += 1; st.rerun()

with st.expander("⚙️ قواعد مونتال (للتعديل عند الحاجة فقط)"):
    R0 = P0["rules"]; ru = {}
    labels = dict(base_h="ارتفاع التحتاني", base_d="عمق التحتاني", base_d_appliance="عمق التحتاني (حوض/غسالة/تلاجة)",
                  up_z="بداية العلوي من الأرض", up_d="عمق العلوي", up_main="ارتفاع العلوي", up_stor="ارتفاع التخزين فوق العلوي",
                  ceiling="ارتفاع السقف", single_min="أقل عرض لدرفة", double_min="أقل عرض لدرفتين",
                  double_max="أقصى عرض لدرفتين", corner="مقاس الركنة")
    for k, lab in labels.items():
        ru[k] = st.number_input(lab, value=float(R0[k]), step=1.0, key=f"r_{k}{V}")
    rules = Rules(**ru)
    if rules.up_top > rules.ceiling:
        st.error("العلوي + التخزين أعلى من السقف!")

# ------------------------------------------------------------------ inputs
st.header("١) بيانات المشروع")
name = st.text_input("اسم العميل", value=P0["name"], key=f"name{V}")
shape = st.radio("شكل المطبخ", ["L", "مستقيم"], index=0 if P0["shape"] == "L" else 1, horizontal=True, key=f"shape{V}")
shape_key = "L" if shape == "L" else "straight"

walls = []
for i in range(2 if shape_key == "L" else 1):
    wd = P0["walls"][i] if i < len(P0["walls"]) else dict(name="AB"[i], length=300, corner_side="none", storage="all", appliance=False, openings=[])
    with st.container(border=True):
        st.subheader(f"الحيطة {'AB'[i]}")
        length = st.number_input("الطول (سم)", min_value=30.0, value=float(wd["length"]), step=1.0, key=f"len{i}{V}")
        cs = st.selectbox("الركنة عند أي طرف؟ (وانتي واقفة قدام الحيطة)", list(SIDES),
                          index=list(SIDES).index(SIDES_R.get(wd["corner_side"], "لا يوجد")), key=f"cs{i}{V}")
        sg = st.selectbox("التخزين فوق العلوي", list(STOR),
                          index=list(STOR).index(STOR_R.get(wd["storage"], "فوق كل العلوي")), key=f"sg{i}{V}")
        ap = st.checkbox("فيه حوض / غسالة / تلاجة على الحيطة (عمق التحتاني أكبر)", value=wd.get("appliance", False), key=f"ap{i}{V}")
        n_ops = int(st.number_input("عدد الأبواب والشبابيك", min_value=0, max_value=8, value=len(wd["openings"]), step=1, key=f"nops{i}{V}"))
        ops = []
        for j in range(n_ops):
            od = wd["openings"][j] if j < len(wd["openings"]) else dict(kind="door", start=0.0, width=90.0, height=200.0, sill=0.0)
            with st.container(border=True):
                kind_lbl = st.radio(f"فتحة {j+1}", list(KIND), index=list(KIND).index(KIND_R[od["kind"]]), horizontal=True, key=f"k{i}_{j}{V}")
                a, b = st.columns(2)
                start = a.number_input("تبدأ بعد (سم من أول الحيطة)", min_value=0.0, value=float(od["start"]), step=1.0, key=f"s{i}_{j}{V}")
                width = b.number_input("العرض", min_value=1.0, value=float(od["width"]), step=1.0, key=f"w{i}_{j}{V}")
                a, b = st.columns(2)
                height = a.number_input("الارتفاع", min_value=1.0, value=float(od["height"]), step=1.0, key=f"h{i}_{j}{V}")
                if kind_lbl == "شباك":
                    sill = b.number_input("بعده عن الأرض", min_value=0.0, value=float(od.get("sill", 0.0)), step=1.0, key=f"z{i}_{j}{V}")
                else:
                    sill = 0.0
                ops.append(Opening(KIND[kind_lbl], float(start), float(width), float(height), float(sill)))
        walls.append(Wall("AB"[i], float(length), ops, SIDES[cs], STOR[sg], ap))

project = Project(name, shape_key, walls, rules)
st.session_state.proj = project_to_dict(project)

# ------------------------------------------------------------------ results
st.header("٢) النتيجة")
layouts, errors, notes = build_project(project)
for e in errors:
    st.error(e)
if errors:
    st.stop()

all_ok = all(l.checks[z]["ok"] for l in layouts for z in ("lower", "upper"))
if all_ok:
    st.success("✅ كل الحسابات مظبوطة ومفيش فراغات.")
for l in layouts:
    for w in l.warnings:
        st.warning(w)
for n in notes:
    st.info(n)


def tbl_lower(l):
    return pd.DataFrame([{"الوحدة": u.label, "العرض": u.w, "الارتفاع": u.h, "العمق": u.d if u.kind == "unit" else rules.corner,
                          "النوع": "ركنة ثابتة" if u.kind == "corner" else ("درفة" if u.doors == 1 else "درفتين")}
                         for u in l.lowers])


def tbl_upper(l):
    rows = []
    for u in l.uppers:
        rows.append({"الوحدة": u.label, "العرض": u.w, "الارتفاع": u.h, "العمق": u.d,
                     "النوع": "ركنة ثابتة" if u.kind == "corner" else ("درفة" if u.doors == 1 else "درفتين"),
                     "يبدأ من": u.z0})
    for u in l.storages:
        rows.append({"الوحدة": u.label, "العرض": u.w, "الارتفاع": u.h, "العمق": u.d, "النوع": "تخزين", "يبدأ من": u.z0})
    return pd.DataFrame(rows)


def tbl_check(l):
    rows = []
    for z, zn in (("lower", "التحتاني"), ("upper", "العلوي")):
        c = l.checks[z]
        rows.append({"": zn, "مجموع الوحدات": c["units"], "فتحات": c["blocked"], "فراغات": c["voids"],
                     "طول الحيطة": c["wall"], "الفرق": c["diff"], "النتيجة": "✅" if c["ok"] else "⚠️"})
    return pd.DataFrame(rows)


big = st.toggle("خط كبير في الرسومات (للموبايل)", value=True)
fs2, fs3 = (2.2, 1.9) if big else (1.0, 1.0)
st.caption("اضغطي على أي رسمة لتكبيرها بملء الشاشة. الأفضل تلفّي الموبايل أفقي للمنظور 3D.")

svgs = {}
tabs = st.tabs([f"حيطة {l.wall.name}" for l in layouts] + ["3D", "الملخص"])
for t, l in zip(tabs, layouts):
    with t:
        svg = elevation_svg(l, rules, fs=fs2); svgs[f"wall_{l.wall.name}.svg"] = elevation_svg(l, rules, fs=1.0)
        show_svg(svg)
        st.markdown("**التحتاني** (عمق الدولاب %g سم)" % l.base_d)
        st.dataframe(tbl_lower(l), hide_index=True, width="stretch")
        st.markdown("**العلوي**")
        st.dataframe(tbl_upper(l), hide_index=True, width="stretch")
        st.markdown("**التحقق الحسابي**")
        st.dataframe(tbl_check(l), hide_index=True, width="stretch")
with tabs[len(layouts)]:
    svg3 = iso_svg(layouts, rules, shape_key, fs=fs3); svgs["kitchen_3d.svg"] = iso_svg(layouts, rules, shape_key)
    show_svg(svg3)

with tabs[-1]:
    s = summary(project, layouts)
    def widths(us): return "، ".join(f"{u.w:g}" for u in us)
    st.dataframe(pd.DataFrame([
        {"البند": "التحتاني (بدون ركنة)", "العدد": sum(1 for u in s["lowers"] if u.kind == "unit"), "العروض": widths([u for u in s["lowers"] if u.kind == "unit"])},
        {"البند": "العلوي (بدون ركنة)", "العدد": sum(1 for u in s["uppers"] if u.kind == "unit"), "العروض": widths([u for u in s["uppers"] if u.kind == "unit"])},
        {"البند": "التخزين", "العدد": len(s["storages"]), "العروض": widths(s["storages"])},
        {"البند": "الركنات", "العدد": s["corners"], "العروض": f"{rules.corner:g}"},
        {"البند": "الإجمالي", "العدد": s["total"], "العروض": ""},
    ]), hide_index=True, width="stretch")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for l in layouts:
            tbl_lower(l).to_excel(xw, sheet_name=f"{l.wall.name}-تحتاني", index=False)
            tbl_upper(l).to_excel(xw, sheet_name=f"{l.wall.name}-علوي", index=False)
            tbl_check(l).to_excel(xw, sheet_name=f"{l.wall.name}-تحقق", index=False)
    fn = (name or "project").strip().replace(" ", "_")
    st.download_button("⬇️ جداول Excel", buf.getvalue(), f"{fn}_tables.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("💾 حفظ المشروع (JSON)", json.dumps(project_to_dict(project), ensure_ascii=False, indent=1),
                       f"{fn}.json", "application/json")
    html = "<!doctype html><meta charset=utf-8><body dir=rtl>" + "<hr>".join(svgs.values())
    st.download_button("🖼️ كل الرسومات (HTML)", html, f"{fn}_drawings.html", "text/html")
