import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from datetime import datetime, date
from pathlib import Path

from db import SessionLocal, init_db, Issue

st.set_page_config(page_title="RCA Tracker", page_icon="🧭", layout="wide")

# Colorful base for Dashboard + Import/Export
st.markdown("""<style>
:root, .stApp { --text-color:#0f172a; --border:#e5e7eb; }
.stApp { background: linear-gradient(135deg,#f8fafc 0%,#fdf2f8 50%,#eef2ff 100%); color:var(--text-color); }
[data-testid="stSidebar"] > div:first-child { background:#0f172a; color:#e5e7eb; }
[data-testid="stSidebar"] label { color:#e5e7eb !important; }
.kpi { border-radius:18px; padding:18px; background:#fff; border:1px solid var(--border); box-shadow:0 10px 30px rgba(2,6,23,.06); }
.kpi .value { font-size:30px; font-weight:800; margin-top:4px; }
.kpi .label { font-size:12px; color:#475569; text-transform:uppercase; letter-spacing:.06em; }
.card { background:#fff; border:1px solid var(--border); border-radius:18px; padding:16px; box-shadow:0 10px 30px rgba(2,6,23,.06); }
.filter-badge { background:#eef2ff; border:1px solid #c7d2fe; padding:6px 10px; border-radius:12px; display:inline-block; margin-right:8px; margin-bottom:6px; }
</style>
""", unsafe_allow_html=True)

# ---------- Init ----------
init_db()
session: Session = SessionLocal()

# ---------- Sidebar ----------
st.sidebar.title("🧭 RCA Tracker")
page = st.sidebar.radio("Go to", ["Dashboard", "Issue Log (Quick Add + Editor)", "Manage Issues", "Import / Export"], index=0)

with st.sidebar.expander("🔎 Filters", expanded=True):
    st.text_input("Module contains", key="flt_module")
    st.multiselect("Priority", ["Critical","High","Medium","Low"], key="flt_priority")
    st.multiselect("Status", ["Pending","Closed"], key="flt_status")
    st.date_input("From Reported Date", value=None, key="flt_from")
    st.date_input("To Reported Date", value=None, key="flt_to")
    if st.button("🧹 Clear Filters"):
        st.session_state["flt_module"] = ""
        st.session_state["flt_priority"] = []
        st.session_state["flt_status"] = []
        st.session_state["flt_from"] = None
        st.session_state["flt_to"] = None
        st.rerun()

# ---------- Helpers ----------
def fetch_filtered():
    stmt = select(Issue)
    if st.session_state.get("flt_module"):
        stmt = stmt.where(Issue.module_name.ilike(f"%{st.session_state['flt_module']}%"))
    if st.session_state.get("flt_priority"):
        stmt = stmt.where(Issue.priority.in_(st.session_state["flt_priority"]))
    if st.session_state.get("flt_status"):
        stmt = stmt.where(Issue.status.in_(st.session_state["flt_status"]))
    if st.session_state.get("flt_from"):
        stmt = stmt.where(Issue.reported_date >= datetime.combine(st.session_state["flt_from"], datetime.min.time()))
    if st.session_state.get("flt_to"):
        stmt = stmt.where(Issue.reported_date <= datetime.combine(st.session_state["flt_to"], datetime.max.time()))
    stmt = stmt.order_by(Issue.reported_date.desc().nulls_last(), Issue.created_at.desc())
    return session.execute(stmt).scalars().all()

def to_df(items):
    return pd.DataFrame([{
        "ID": i.id,
        "Ticket / Bug ID": i.ticket_id,
        "Module Name": i.module_name,
        "Reported Date": i.reported_date,
        "Reported By": i.reported_by,
        "Priority": i.priority,
        "Requirement Gap / Bug Description": i.description,
        "Steps to Reproduce": i.steps_to_reproduce,
        "Impacted Functionality": i.impacted_functionality,
        "Root Cause Identified": i.root_cause_identified,
        "Root Cause Analysis Notes": i.rca_notes,
        "Short-term Fix": i.short_term_fix,
        "Long-term Preventive Action": i.long_term_preventive_action,
        "Responsible Person": i.responsible_person,
        "Target Completion Date": i.target_completion_date,
        "Verified By": i.verified_by,
        "Verification Date": i.verification_date,
        "Status (Closed / Pending)": i.status,
    } for i in items])

def parse_dt(x, default_today=False):
    if x is None or (isinstance(x, float) and pd.isna(x)) or (hasattr(x, 'strip') and x.strip() == ""):
        return datetime.combine(date.today(), datetime.min.time()) if default_today else None
    try:
        return pd.to_datetime(x).to_pydatetime()
    except Exception:
        return datetime.combine(date.today(), datetime.min.time()) if default_today else None

def get_live_df(): return to_df(fetch_filtered())

def show_filter_summary():
    active = []
    if st.session_state.get("flt_module"): active.append(f'Module: "{st.session_state["flt_module"]}"')
    if st.session_state.get("flt_priority"): active.append("Priority: " + ", ".join(st.session_state["flt_priority"]))
    if st.session_state.get("flt_status"): active.append("Status: " + ", ".join(st.session_state["flt_status"]))
    if st.session_state.get("flt_from"): active.append(f'From: {st.session_state["flt_from"]}')
    if st.session_state.get("flt_to"): active.append(f'To: {st.session_state["flt_to"]}')
    if active:
        st.write("**Active filters:**")
        for a in active: st.markdown(f'<span class="filter-badge">{a}</span>', unsafe_allow_html=True)
    else:
        st.caption("No filters applied — showing **all** issues.")

# Dark CSS injection with robust path + fallback
DARK_CSS_FALLBACK = """[data-testid="stAppViewContainer"]{background-color:#0b1220!important;color:#f8fafc!important;}
[data-testid="stAppViewContainer"] .stMarkdown,[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,[data-testid="stAppViewContainer"] h3{color:#f8fafc!important;}
[data-testid="stAppViewContainer"] .stTextInput input,[data-testid="stAppViewContainer"] .stTextArea textarea,
[data-testid="stAppViewContainer"] .stDateInput input,[data-testid="stAppViewContainer"] .stSelectbox div[role="combobox"]{
  background:#0f172a!important;color:#e5e7eb!important;border:1px solid #334155!important;border-radius:10px!important;}
[data-testid="stAppViewContainer"] [data-testid="stDataFrame"] .st-ag-theme [role="columnheader"]{
  background:#0b1220!important;color:#e5e7eb!important;border-bottom:1px solid #1f2937!important;}
[data-testid="stAppViewContainer"] [data-testid="stDataFrame"] .st-ag-theme .ag-row{
  background:#0f172a!important;color:#e5e7eb!important;border-bottom:1px solid #1f2937!important;}
[data-testid="stAppViewContainer"] .stButton>button{background:#111827!important;color:#e5e7eb!important;
  border:1px solid #374151!important;border-radius:10px!important;}
[data-testid="stAppViewContainer"] .stButton>button:hover{background:#1f2937!important;}
"""

def inject_dark():
    css_path = Path(__file__).parent / "dark_pages.css"
    try:
        css = css_path.read_text(encoding="utf-8")
    except Exception:
        css = DARK_CSS_FALLBACK
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# ---------- Dashboard (vibrant multi-color) ----------
if page == "Dashboard":
    st.title("📊 RCA Dashboard")
    show_filter_summary()
    df = get_live_df()

    if df.empty:
        st.info("No records yet. Add via **Issue Log** or **Import / Export**.")
    else:
        # Derived fields
      # Convert dates to timezone-aware then drop timezone for safe subtraction
    df["_reported"] = pd.to_datetime(df["Reported Date"], utc=True).dt.tz_convert(None)

# Today as naive midnight timestamp
    today = pd.Timestamp.today().normalize()

# Age calculation (naive - naive)
    df["_age_days"] = (today - df["_reported"].dt.normalize()).dt.days.clip(lower=0)

# Target completion date (also normalize tz)
    target = pd.to_datetime(df["Target Completion Date"], errors="coerce", utc=True).dt.tz_convert(None)

# SLA breach condition
    df["_sla_breach"] = (
    df["Status (Closed / Pending)"].eq("Pending")
    & target.notna()
    & (target.dt.normalize() < today)
    )


        # KPIs
        total = len(df)
        pending = int((df["Status (Closed / Pending)"] == "Pending").sum())
        closed = int((df["Status (Closed / Pending)"] == "Closed").sum())
        crit = int((df["Priority"] == "Critical").sum())
        breaches = int(df["_sla_breach"].sum())
        avg_age = int(df["_age_days"].mean()) if total else 0

        # Vibrant toggle + CSS
        vibrant = st.toggle("🌈 Vibrant mode", value=True)
        st.markdown("""        <style>
        .kpi { border-radius:18px; padding:18px; background:#fff; border:1px solid #e5e7eb; box-shadow:0 10px 30px rgba(2,6,23,.06); }
        .kpi .value { font-size:30px; font-weight:800; margin-top:4px; }
        .kpi .label { font-size:12px; color:#475569; text-transform:uppercase; letter-spacing:.06em; }

        .kpi-v1 { background:linear-gradient(135deg,#cffafe,#e0e7ff); }
        .kpi-v2 { background:linear-gradient(135deg,#fde68a,#fca5a5); }
        .kpi-v3 { background:linear-gradient(135deg,#bbf7d0,#86efac); }
        .kpi-v4 { background:linear-gradient(135deg,#fecaca,#fda4af); }
        .kpi-v5 { background:linear-gradient(135deg,#fef08a,#fcd34d); }
        .kpi-v6 { background:linear-gradient(135deg,#e9d5ff,#c4b5fd); }

        .vibrant .kpi { position:relative; overflow:hidden; }
        .vibrant .kpi:after {
          content:""; position:absolute; inset:-2px;
          background:conic-gradient(from var(--angle), #f472b6, #60a5fa, #22d3ee, #a78bfa, #f472b6);
          filter:blur(14px); z-index:-1; animation:spin 6s linear infinite;
        }
        @property --angle { syntax: "<angle>"; initial-value: 0deg; inherits: false; }
        @keyframes spin { to { --angle: 360deg; } }
        </style>
        """, unsafe_allow_html=True)

        # KPI row
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1: st.markdown(f'<div class="kpi {"kpi-v1" if vibrant else ""}"><div class="label">Total</div><div class="value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi {"kpi-v2" if vibrant else ""}"><div class="label">Pending</div><div class="value">{pending}</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="kpi {"kpi-v3" if vibrant else ""}"><div class="label">Closed</div><div class="value">{closed}</div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="kpi {"kpi-v4" if vibrant else ""}"><div class="label">Critical</div><div class="value">{crit}</div></div>', unsafe_allow_html=True)
        with c5: st.markdown(f'<div class="kpi {"kpi-v5" if vibrant else ""}"><div class="label">SLA Breaches</div><div class="value">{breaches}</div></div>', unsafe_allow_html=True)
        with c6: st.markdown(f'<div class="kpi {"kpi-v6" if vibrant else ""}"><div class="label">Avg Age (days)</div><div class="value">{avg_age}</div></div>', unsafe_allow_html=True)

        # Palettes
        pie_colors = ["#ef4444","#f59e0b","#10b981","#3b82f6","#a855f7","#14b8a6"]
        bar_colors = ["#60a5fa","#34d399","#fbbf24","#f472b6","#a78bfa","#22d3ee","#f87171"]
        status_colors = {"Pending":"#f97316","Closed":"#22c55e"}

        # Row 1
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            t = df.copy()
            t["Reported"] = pd.to_datetime(t["Reported Date"]).dt.date
            t = t.groupby("Reported").size().reset_index(name="Count")
            fig = px.area(t, x="Reported", y="Count")
            fig.update_traces(line=dict(width=3))
            fig.update_layout(title="Issues Over Time", margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig, use_container_width=True)
        with r1c2:
            p = df.groupby("Priority").size().reset_index(name="Count").sort_values("Count", ascending=False)
            fig = px.pie(p, names="Priority", values="Count", hole=0.45, color="Priority",
                         color_discrete_sequence=pie_colors)
            fig.update_layout(title="Priority Mix", margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig, use_container_width=True)

        # Row 2
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            m = df.groupby("Module Name").size().reset_index(name="Count").sort_values("Count", ascending=False).head(12)
            fig = px.bar(m, x="Module Name", y="Count", color="Count",
                         color_continuous_scale=["#93c5fd","#a7f3d0","#fde68a","#fca5a5","#c7d2fe"]
                        )
            fig.update_traces(marker=dict(line=dict(width=0)))
            fig.update_layout(title="Top Modules by Issue Count", margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig, use_container_width=True)
        with r2c2:
            sp = df.pivot_table(index="Priority", columns="Status (Closed / Pending)", values="ID", aggfunc="count", fill_value=0)
            sp = sp.reindex(["Critical","High","Medium","Low"], axis=0).fillna(0)
            sp = sp.rename_axis(None, axis=1).reset_index().melt(id_vars="Priority", var_name="Status", value_name="Count")
            fig = px.bar(sp, x="Priority", y="Count", color="Status",
                         barmode="group", color_discrete_map=status_colors)
            fig.update_layout(title="Status × Priority", margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig, use_container_width=True)

        # Row 3
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            bins = [-0.1, 7, 14, 30, 60, 90, 9999]
            labels = ["0–7d","8–14d","15–30d","31–60d","61–90d",">90d"]
            aging = pd.cut(df["_age_days"], bins=bins, labels=labels)
            ag = aging.value_counts().reindex(labels, fill_value=0).reset_index()
            ag.columns = ["Bucket","Count"]
            fig = px.bar(ag, x="Bucket", y="Count", color="Bucket",
                         color_discrete_sequence=bar_colors)
            fig.update_layout(title="Issue Aging (days)", margin=dict(l=0,r=0,t=40,b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with r3c2:
            tm = df[["Module Name","Priority"]].copy()
            tm["Count"] = 1
            fig = px.treemap(tm, path=["Module Name","Priority"], values="Count",
                             color="Priority", color_discrete_sequence=pie_colors)
            fig.update_layout(title="Treemap: Module vs Priority", margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig, use_container_width=True)

# ---------- Issue Log (Dark) ----------
elif page == "Issue Log (Quick Add + Editor)":
    inject_dark()
    st.title("📝 Issue Log — Dark Mode")
    with st.form("quick_add_form"):
        q1,q2,q3,q4 = st.columns(4)
        with q1: ticket_id = st.text_input("Ticket / Bug ID *")
        with q2: module_name = st.text_input("Module Name *")
        with q3: reported_by = st.text_input("Reported By *")
        with q4: priority = st.selectbox("Priority *", ["Critical","High","Medium","Low"], index=2)
        reported_date = st.date_input("Reported Date *", value=date.today())
        description = st.text_area("Requirement Gap / Bug Description *", height=100)
        steps = st.text_area("Steps to Reproduce", height=80)
        impacted = st.text_area("Impacted Functionality", height=80)
        rc_ident = st.text_input("Root Cause Identified")
        rca_notes = st.text_area("Root Cause Analysis Notes", height=80)
        stf = st.text_area("Short-term Fix", height=80)
        lpa = st.text_area("Long-term Preventive Action", height=80)
        resp = st.text_input("Responsible Person")
        tcd = st.date_input("Target Completion Date", value=None)
        ver_by = st.text_input("Verified By")
        ver_dt = st.date_input("Verification Date", value=None)
        status = st.selectbox("Status (Closed / Pending) *", ["Pending","Closed"], index=0)
        qa_submit = st.form_submit_button("➕ Add Ticket to DB")
    if qa_submit:
        try:
            obj = Issue(ticket_id=ticket_id.strip(), module_name=module_name.strip(),
                        reported_date=datetime.combine(reported_date, datetime.min.time()),
                        reported_by=reported_by.strip(), priority=priority, description=description.strip(),
                        steps_to_reproduce=(steps.strip() if steps else None), impacted_functionality=(impacted.strip() if impacted else None),
                        root_cause_identified=(rc_ident.strip() if rc_ident else None), rca_notes=(rca_notes.strip() if rca_notes else None),
                        short_term_fix=(stf.strip() if stf else None), long_term_preventive_action=(lpa.strip() if lpa else None),
                        responsible_person=(resp.strip() if resp else None), target_completion_date=(datetime.combine(tcd, datetime.min.time()) if tcd else None),
                        verified_by=(ver_by.strip() if ver_by else None), verification_date=(datetime.combine(ver_dt, datetime.min.time()) if ver_dt else None),
                        status=status)
            session.add(obj); session.commit(); st.success("Ticket added to DB ✅")
        except Exception as e:
            st.error(f"Failed to save: {e}"); st.exception(e)

    st.divider()
    cols = ["Ticket / Bug ID","Module Name","Reported Date","Reported By","Priority",
            "Requirement Gap / Bug Description","Steps to Reproduce","Impacted Functionality",
            "Root Cause Identified","Root Cause Analysis Notes","Short-term Fix","Long-term Preventive Action",
            "Responsible Person","Target Completion Date","Verified By","Verification Date","Status (Closed / Pending)"]
    if "editor_df" not in st.session_state:
        st.session_state.editor_df = pd.DataFrame([{c: "" for c in cols} for _ in range(5)])
    upl = st.file_uploader("Upload Excel/CSV into editor (not DB yet)", type=["xlsx","xls","csv"], key="upl_editor")
    if upl is not None:
        try:
            data = pd.read_csv(upl) if upl.name.lower().endswith(".csv") else pd.read_excel(upl)
            missing = [c for c in cols if c not in data.columns]
            if missing: st.error(f"Missing columns in file: {missing}")
            else: st.session_state.editor_df = data.copy(); st.success(f"Loaded {len(data)} rows into editor.")
        except Exception as e:
            st.error(f"Failed to load file: {e}")
    with st.form("editor_form", clear_on_submit=False):
        add_empty = st.form_submit_button("➕ Add Empty Row")
        if add_empty: st.session_state.editor_df.loc[len(st.session_state.editor_df)] = {c: "" for c in cols}
        edited = st.data_editor(st.session_state.editor_df, num_rows="dynamic", use_container_width=True, key="editor_table",
                                column_config={"Priority": st.column_config.SelectboxColumn(options=["Critical","High","Medium","Low"], default="Medium"),
                                               "Status (Closed / Pending)": st.column_config.SelectboxColumn(options=["Pending","Closed"], default="Pending")})
        save_btn = st.form_submit_button("💾 Save All Editor Rows to DB (Append)")
    if save_btn:
        try:
            added, skipped = 0, 0
            for _, r in edited.iterrows():
                ticket, module, desc, rep_by = r.get("Ticket / Bug ID"), r.get("Module Name"), r.get("Requirement Gap / Bug Description"), r.get("Reported By")
                rep_dt = parse_dt(r.get("Reported Date"), default_today=True)
                pri = (r.get("Priority") or "Medium"); status_val = (r.get("Status (Closed / Pending)") or "Pending")
                if not ticket or not module or not desc or not rep_by: skipped += 1; continue
                obj = Issue(ticket_id=str(ticket).strip(), module_name=str(module).strip(), reported_date=rep_dt,
                            reported_by=str(rep_by).strip(), priority=str(pri).strip(), description=str(desc).strip(),
                            steps_to_reproduce=None if pd.isna(r.get("Steps to Reproduce")) else str(r.get("Steps to Reproduce")),
                            impacted_functionality=None if pd.isna(r.get("Impacted Functionality")) else str(r.get("Impacted Functionality")),
                            root_cause_identified=None if pd.isna(r.get("Root Cause Identified")) else str(r.get("Root Cause Identified")),
                            rca_notes=None if pd.isna(r.get("Root Cause Analysis Notes")) else str(r.get("Root Cause Analysis Notes")),
                            short_term_fix=None if pd.isna(r.get("Short-term Fix")) else str(r.get("Short-term Fix")),
                            long_term_preventive_action=None if pd.isna(r.get("Long-term Preventive Action")) else str(r.get("Long-term Preventive Action")),
                            responsible_person=None if pd.isna(r.get("Responsible Person")) else str(r.get("Responsible Person")),
                            target_completion_date=parse_dt(r.get("Target Completion Date")),
                            verified_by=None if pd.isna(r.get("Verified By")) else str(r.get("Verified By")),
                            verification_date=parse_dt(r.get("Verification Date")),
                            status=str(status_val).strip())
                session.add(obj); added += 1
            session.commit(); st.success(f"Saved {added} rows ✅ | Skipped: {skipped}")
        except Exception as e:
            session.rollback(); st.error(f"Bulk save failed: {e}")

# ---------- Manage Issues (Dark) ----------
elif page == "Manage Issues":
    inject_dark()
    st.title("🧰 Manage Issues — Dark Mode")
    df = get_live_df(); all_count = len(to_df(session.execute(select(Issue)).scalars().all()))
    st.caption(f"Showing {len(df)} of {all_count} total records.")
    if df.empty:
        st.info("No records match the current filters.")
    else:
        st.dataframe(df, use_container_width=True, height=420)
        ids = df["ID"].tolist(); sel = st.selectbox("Select ID to Edit", ids if ids else [None])
        if sel:
            item = session.get(Issue, int(sel))
            with st.form("edit_form"):
                e1,e2,e3,e4 = st.columns(4)
                with e1: item.ticket_id = st.text_input("Ticket / Bug ID *", value=item.ticket_id or "")
                with e2: item.module_name = st.text_input("Module Name *", value=item.module_name or "")
                with e3:
                    rd = item.reported_date.date() if item.reported_date else date.today()
                    rd_new = st.date_input("Reported Date *", value=rd)
                    item.reported_date = datetime.combine(rd_new, datetime.min.time())
                with e4: item.reported_by = st.text_input("Reported By *", value=item.reported_by or "")
                f1,f2,f3,f4 = st.columns(4)
                with f1: item.priority = st.selectbox("Priority *", ["Critical","High","Medium","Low"], index=["Critical","High","Medium","Low"].index(item.priority or "Medium"))
                with f2: item.status = st.selectbox("Status (Closed / Pending) *", ["Pending","Closed"], index=["Pending","Closed"].index(item.status or "Pending"))
                with f3: item.responsible_person = st.text_input("Responsible Person", value=item.responsible_person or "")
                with f4:
                    tcd = item.target_completion_date.date() if item.target_completion_date else None
                    tcd_new = st.date_input("Target Completion Date", value=tcd)
                    item.target_completion_date = datetime.combine(tcd_new, datetime.min.time()) if tcd_new else None
                item.description = st.text_area("Requirement Gap / Bug Description *", value=item.description or "", height=110)
                item.steps_to_reproduce = st.text_area("Steps to Reproduce", value=item.steps_to_reproduce or "", height=110)
                item.impacted_functionality = st.text_area("Impacted Functionality", value=item.impacted_functionality or "", height=100)
                g1,g2 = st.columns(2)
                with g1: item.root_cause_identified = st.text_input("Root Cause Identified", value=item.root_cause_identified or ""); item.short_term_fix = st.text_area("Short-term Fix", value=item.short_term_fix or "")
                with g2: item.rca_notes = st.text_area("Root Cause Analysis Notes", value=item.rca_notes or ""); item.long_term_preventive_action = st.text_area("Long-term Preventive Action", value=item.long_term_preventive_action or "")
                h1,h2 = st.columns(2)
                with h1: item.verified_by = st.text_input("Verified By", value=item.verified_by or "")
                with h2:
                    vd = item.verification_date.date() if item.verification_date else None
                    vd_new = st.date_input("Verification Date", value=vd)
                    item.verification_date = datetime.combine(vd_new, datetime.min.time()) if vd_new else None
                colA, colB = st.columns([1,1])
                save = colA.form_submit_button("💾 Save"); delete = colB.form_submit_button("🗑️ Delete")
            if save: session.commit(); st.success("Saved ✅"); st.rerun()
            if delete: session.delete(item); session.commit(); st.warning("Deleted"); st.rerun()

# ---------- Import / Export (Light) ----------
elif page == "Import / Export":
    st.title("📥 Import / Export")
    cols = ["Ticket / Bug ID","Module Name","Reported Date","Reported By","Priority",
            "Requirement Gap / Bug Description","Steps to Reproduce","Impacted Functionality",
            "Root Cause Identified","Root Cause Analysis Notes","Short-term Fix","Long-term Preventive Action",
            "Responsible Person","Target Completion Date","Verified By","Verification Date","Status (Closed / Pending)"]
    import io
    out_tpl = io.BytesIO()
    with pd.ExcelWriter(out_tpl, engine="openpyxl") as writer:
        pd.DataFrame(columns=cols).to_excel(writer, index=False, sheet_name="Template")
    st.download_button("📄 Download Import Template", data=out_tpl.getvalue(), file_name="rca_import_template_v4_8.xlsx")
    upl2 = st.file_uploader("Upload Excel/CSV to import into DB (Replace or Append)", type=["xlsx","xls","csv"], key="upl_backup")
    if upl2 is not None:
        data = pd.read_csv(upl2) if upl2.name.lower().endswith(".csv") else pd.read_excel(upl2)
        st.write("Preview:", data.head())
        def to_dt(x, default_today=False):
            if x is None or (isinstance(x, float) and pd.isna(x)) or (hasattr(x, 'strip') and x.strip() == ""):
                return datetime.combine(date.today(), datetime.min.time()) if default_today else None
            try: return pd.to_datetime(x).to_pydatetime()
            except Exception: return datetime.combine(date.today(), datetime.min.time()) if default_today else None
        def rows_to_objects(df_in):
            added = 0
            for _, r in df_in.iterrows():
                ticket = r.get("Ticket / Bug ID"); module = r.get("Module Name"); desc = r.get("Requirement Gap / Bug Description"); rep_by = r.get("Reported By")
                rep_dt = to_dt(r.get("Reported Date"), default_today=True)
                pri = (r.get("Priority") or "Medium"); status_val = (r.get("Status (Closed / Pending)") or "Pending")
                if pd.isna(ticket) or pd.isna(module) or pd.isna(desc) or pd.isna(rep_by): continue
                obj = Issue(ticket_id=str(ticket).strip(), module_name=str(module).strip(), reported_date=rep_dt,
                            reported_by=str(rep_by).strip(), priority=str(pri).strip(), description=str(desc).strip(),
                            steps_to_reproduce=None if pd.isna(r.get("Steps to Reproduce")) else str(r.get("Steps to Reproduce")),
                            impacted_functionality=None if pd.isna(r.get("Impacted Functionality")) else str(r.get("Impacted Functionality")),
                            root_cause_identified=None if pd.isna(r.get("Root Cause Identified")) else str(r.get("Root Cause Identified")),
                            rca_notes=None if pd.isna(r.get("Root Cause Analysis Notes")) else str(r.get("Root Cause Analysis Notes")),
                            short_term_fix=None if pd.isna(r.get("Short-term Fix")) else str(r.get("Short-term Fix")),
                            long_term_preventive_action=None if pd.isna(r.get("Long-term Preventive Action")) else str(r.get("Long-term Preventive Action")),
                            responsible_person=None if pd.isna(r.get("Responsible Person")) else str(r.get("Responsible Person")),
                            target_completion_date=to_dt(r.get("Target Completion Date")),
                            verified_by=None if pd.isna(r.get("Verified By")) else str(r.get("Verified By")),
                            verification_date=to_dt(r.get("Verification Date")),
                            status=str(status_val).strip())
                session.add(obj); added += 1
            session.commit(); return added
        col1, col2 = st.columns(2)
        if col1.button("➕ Append to DB"): added = rows_to_objects(data); st.success(f"Appended {added} rows ✅"); st.rerun()
        if col2.button("♻️ Replace DB (wipe & load)"): session.execute(text("DELETE FROM issues")); session.commit(); added = rows_to_objects(data); st.success(f"Replaced dataset with {added} rows ✅"); st.rerun()
