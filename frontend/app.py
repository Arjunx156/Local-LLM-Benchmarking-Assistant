"""
frontend/app.py — Streamlit dashboard for Local LLM Benchmarking Assistant.
Run: streamlit run frontend/app.py
"""
import os, json, time
import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
PALETTE = ["#6366f1","#f59e0b","#10b981","#ef4444","#3b82f6","#8b5cf6","#ec4899"]
BG, SURFACE = "#0f172a", "#1e293b"

st.set_page_config(page_title="LLM Bench", page_icon="🚀", layout="wide")
st.markdown(f"""<style>
[data-testid="stAppViewContainer"]{{background:{BG};}}
[data-testid="stSidebar"]{{background:{SURFACE};}}
section[data-testid="stSidebar"] *{{color:#f8fafc!important;}}
.main .block-container{{padding:1.5rem 2rem;}}
h1,h2,h3,h4,h5,h6{{color:#f8fafc!important;}}
p,li,label{{color:#cbd5e1;}}
.stTabs [data-baseweb="tab-list"]{{background:{SURFACE};border-radius:12px;padding:4px;}}
.stTabs [data-baseweb="tab"]{{color:#94a3b8;border-radius:8px;}}
.stTabs [aria-selected="true"]{{background:#6366f1!important;color:#fff!important;}}
.stMetric{{background:{SURFACE};border-radius:12px;padding:1rem;border:1px solid #334155;}}
.stDataFrame{{border-radius:8px;}}
div[data-testid="metric-container"]{{background:{SURFACE};border-radius:10px;padding:.8rem;border:1px solid #334155;}}
.stButton>button{{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:8px;padding:.5rem 1.5rem;font-weight:600;transition:all .2s;}}
.stButton>button:hover{{transform:translateY(-1px);box-shadow:0 4px 15px rgba(99,102,241,.4);}}
.stSelectbox>div>div{{background:{SURFACE};border-color:#334155;color:#f8fafc;}}
.stMultiSelect>div>div{{background:{SURFACE};border-color:#334155;}}
.stTextInput>div>input{{background:{SURFACE};border-color:#334155;color:#f8fafc;}}
.stSlider>div{{color:#f8fafc;}}
.status-card{{background:{SURFACE};border-radius:12px;padding:1rem 1.5rem;border-left:4px solid #6366f1;margin:.5rem 0;}}
.score-high{{color:#10b981;font-weight:700;}}
.score-mid{{color:#f59e0b;font-weight:700;}}
.score-low{{color:#ef4444;font-weight:700;}}
</style>""", unsafe_allow_html=True)

def api(method, path, **kw):
    try:
        r = getattr(httpx, method)(f"{BACKEND}{path}", timeout=30, **kw)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def chart_layout(title):
    return dict(
        title=dict(text=title, font=dict(color="#f8fafc", size=14)),
        paper_bgcolor=SURFACE, plot_bgcolor=BG,
        font=dict(color="#f8fafc"),
        xaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
        yaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
        margin=dict(l=60,r=30,t=50,b=60), legend=dict(bgcolor="rgba(0,0,0,0)"),
    )

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚀 LLM Bench")
    st.markdown("---")
    sys_data, _ = api("get", "/system")
    if sys_data:
        ollama_ok = sys_data.get("ollama_running", False)
        st.markdown(f"**Ollama:** {'🟢 Running' if ollama_ok else '🔴 Offline'}")
        st.markdown(f"**Models:** {sys_data.get('installed_model_count',0)} installed")
        st.markdown(f"**RAM:** {sys_data.get('ram_available_gb',0):.1f} GB free / {sys_data.get('ram_total_gb',0):.1f} GB total")
        st.markdown(f"**OS:** {sys_data.get('os','?')}")
    st.markdown("---")
    if not sys_data or not sys_data.get("ollama_running"):
        st.error("⚠️ Ollama not detected.\n\nRun: `ollama serve`\nThen: `ollama pull tinyllama`")

# ── Tabs ──────────────────────────────────────────────────────────────────────
t1,t2,t3,t4,t5 = st.tabs(["🖥️ Models","🚀 Benchmark","📊 Results","🔍 Details","💬 Playground"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Models
# ══════════════════════════════════════════════════════════════════════════════
with t1:
    st.markdown("### 🖥️ Installed Models")
    c1,c2 = st.columns([3,1])
    with c2:
        if st.button("🔄 Refresh"):
            st.rerun()

    models_data, err = api("get", "/models")
    if err:
        st.error(f"Cannot reach backend: {err}")
    elif models_data:
        models = models_data.get("models", [])
        if not models:
            st.info("No models installed. Pull one below.")
        else:
            rows = []
            for m in models:
                can = m.get("can_run", True)
                rows.append({
                    "Model": m["name"],
                    "Size (GB)": m["size_gb"],
                    "Params": m.get("parameter_size","?"),
                    "Quant": m.get("quantization","?"),
                    "Family": m.get("family","?"),
                    "Runnable": "✅" if can else f"❌ Need {m.get('ram_needed_gb',0)}GB",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### ⬇️ Pull a New Model")
    col_a, col_b = st.columns([3,1])
    with col_a:
        pull_name = st.text_input("Model name", placeholder="e.g. phi3, mistral, codellama")
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        do_pull = st.button("Pull Model")

    if do_pull and pull_name:
        prog_bar = st.progress(0, text="Starting download...")
        status_box = st.empty()
        try:
            with httpx.Client(timeout=600) as client:
                with client.stream("GET", f"{BACKEND}/models/pull",
                                   params={"name": pull_name}) as r:
                    for line in r.iter_lines():
                        if line.startswith("data:"):
                            try:
                                d = json.loads(line[5:])
                                pct = d.get("percent", 0)
                                prog_bar.progress(int(pct), text=f"{d.get('status','')} — {pct:.1f}%")
                                status_box.caption(d.get("status",""))
                            except Exception:
                                pass
            st.success(f"✅ {pull_name} pulled successfully!")
        except Exception as ex:
            st.error(f"Pull failed: {ex}")

    st.markdown("---")
    st.markdown("### 📊 System Info")
    if sys_data:
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("CPU Cores", f"{sys_data.get('cpu_cores_physical','?')}P / {sys_data.get('cpu_cores_logical','?')}L")
        m2.metric("RAM Total", f"{sys_data.get('ram_total_gb',0):.1f} GB")
        m3.metric("Disk Free", f"{sys_data.get('disk_free_gb',0):.0f} GB")
        m4.metric("Ollama Ver", sys_data.get("ollama_version","?"))

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Run Benchmark
# ══════════════════════════════════════════════════════════════════════════════
with t2:
    st.markdown("### 🚀 Run Benchmark")

    models_data2, _ = api("get", "/models")
    model_names = [m["name"] for m in (models_data2 or {}).get("models",[])]
    suites_data, _ = api("get", "/suites")
    suite_names = (suites_data or {}).get("suites", ["reasoning","coding","summarization","factual"])

    col1, col2 = st.columns(2)
    with col1:
        sel_models = st.multiselect("Select Models", model_names, placeholder="Choose models…")
    with col2:
        sel_suite = st.selectbox("Benchmark Suite", suite_names)

    b1,b2,b3,b4 = st.columns(4)
    run_btn    = b1.button("▶️ Start")
    pause_btn  = b2.button("⏸ Pause")
    resume_btn = b3.button("▶ Resume")
    cancel_btn = b4.button("⏹ Cancel")

    if "job_id" not in st.session_state:
        st.session_state.job_id = None
    if "job_running" not in st.session_state:
        st.session_state.job_running = False

    if run_btn:
        if not sel_models:
            st.warning("Select at least one model.")
        else:
            res, err = api("post", "/benchmark/run",
                          json={"models": sel_models, "suite": sel_suite})
            if err:
                st.error(f"Failed to start: {err}")
            else:
                st.session_state.job_id = res["job_id"]
                st.session_state.job_running = True
                st.success(f"Job started: `{res['job_id'][:8]}…`")

    job_id = st.session_state.job_id
    if job_id:
        if pause_btn:
            api("post", f"/benchmark/{job_id}/pause")
        if resume_btn:
            api("post", f"/benchmark/{job_id}/resume")
        if cancel_btn:
            api("post", f"/benchmark/{job_id}/cancel")
            st.session_state.job_running = False

    if job_id and st.session_state.job_running:
        progress_area = st.empty()
        metrics_area  = st.empty()
        with st.spinner("Benchmarking in progress…"):
            terminal = {"done","cancelled","error"}
            while True:
                poll, perr = api("get", f"/benchmark/{job_id}/poll")
                if perr or not poll:
                    time.sleep(1); continue
                status  = poll.get("status","?")
                prog    = poll.get("progress",{})
                results = poll.get("results",[])
                pct     = prog.get("overall_percent", 0) if prog else 0

                with progress_area.container():
                    st.progress(int(pct)/100, text=f"Overall: {pct:.1f}%")
                    if prog:
                        st.markdown(
                            f'<div class="status-card">'
                            f'🤖 <b>Model:</b> {prog.get("current_model","—")} &nbsp;|&nbsp; '
                            f'📝 <b>Q:</b> {prog.get("current_question_idx",0)}/{prog.get("total_questions_per_model",0)} &nbsp;|&nbsp; '
                            f'⚡ <b>{prog.get("current_tokens_per_second",0):.1f} tok/s</b> &nbsp;|&nbsp; '
                            f'Status: <b>{status}</b></div>',
                            unsafe_allow_html=True
                        )
                with metrics_area.container():
                    if results:
                        st.markdown(f"**{len(results)} questions completed so far**")

                if status in terminal:
                    st.session_state.job_running = False
                    if status == "done":
                        st.success("✅ Benchmark complete! View results in the Results tab.")
                    elif status == "error":
                        st.error(f"Job failed: {poll.get('error_message','unknown error')}")
                    else:
                        st.warning("Benchmark cancelled.")
                    break
                time.sleep(1.5)
                st.rerun()

    elif job_id:
        poll, _ = api("get", f"/benchmark/{job_id}/poll")
        if poll:
            st.info(f"Last job `{job_id[:8]}…` — status: **{poll.get('status','?')}**")
            ra,rb = st.columns(2)
            if ra.button("⬇️ Download Excel"):
                st.markdown(f"[Click to download]({BACKEND}/reports/{job_id}/excel)")
            if rb.button("⬇️ Download JSON"):
                st.markdown(f"[Click to download]({BACKEND}/reports/{job_id}/json)")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Results Dashboard
# ══════════════════════════════════════════════════════════════════════════════
with t3:
    st.markdown("### 📊 Results Dashboard")
    job_id3 = st.session_state.get("job_id")

    if not job_id3:
        st.info("Run a benchmark first (Tab 2).")
    else:
        res_data, err = api("get", f"/benchmark/{job_id3}/results")
        if err or not res_data:
            st.warning("No results yet."); st.stop()
        results_list = res_data.get("results",[])
        if not results_list:
            st.info("No results recorded yet."); st.stop()

        df = pd.DataFrame(results_list)
        models_in = df["model"].unique().tolist()

        # Summary table
        summary = df.groupby("model").agg(
            avg_score=("score","mean"),
            avg_tps=("tokens_per_second","mean"),
            avg_latency=("total_time_ms","mean"),
            avg_ttft=("ttft_ms","mean"),
            avg_ram=("peak_ram_mb","mean"),
            questions=("question_id","count"),
        ).reset_index().sort_values("avg_score", ascending=False)
        summary["avg_score"] = (summary["avg_score"]*100).round(1)
        summary.columns = ["Model","Score %","Tok/s","Latency (ms)","TTFT (ms)","RAM (MB)","Questions"]
        summary = summary.round(2)

        st.dataframe(summary, use_container_width=True, hide_index=True)
        d1,d2 = st.columns(2)
        if d1.button("⬇️ Excel Report"):
            st.markdown(f"[Download Excel]({BACKEND}/reports/{job_id3}/excel)")
        if d2.button("⬇️ JSON Report"):
            st.markdown(f"[Download JSON]({BACKEND}/reports/{job_id3}/json)")

        st.markdown("---")

        # Charts
        ca, cb = st.columns(2)
        with ca:
            # Bar: tok/s per model
            grp = df.groupby("model")["tokens_per_second"].mean().reset_index()
            fig = go.Figure(go.Bar(
                x=grp["tokens_per_second"].round(1), y=grp["model"],
                orientation="h", marker_color=PALETTE[:len(grp)],
                text=grp["tokens_per_second"].round(1), textposition="outside",
            ))
            fig.update_layout(**chart_layout("⚡ Avg Tokens / Second"))
            st.plotly_chart(fig, use_container_width=True)

        with cb:
            # Heatmap: model × category
            cats = df["category"].unique().tolist()
            z_vals, y_labels = [], []
            for m in models_in:
                row = [df[(df["model"]==m)&(df["category"]==c)]["score"].mean()*100
                       if len(df[(df["model"]==m)&(df["category"]==c)])>0 else 0 for c in cats]
                z_vals.append(row); y_labels.append(m)
            fig2 = go.Figure(go.Heatmap(
                z=z_vals, x=cats, y=y_labels,
                colorscale=[[0,"#ef4444"],[.5,"#f59e0b"],[1,"#10b981"]],
                zmin=0, zmax=100,
                text=[[f"{v:.0f}%" for v in row] for row in z_vals],
                texttemplate="%{text}",
            ))
            fig2.update_layout(**{k:v for k,v in chart_layout("🔥 Score Heatmap").items() if k not in ("xaxis","yaxis")})
            st.plotly_chart(fig2, use_container_width=True)

        cc, cd = st.columns(2)
        with cc:
            # Radar chart
            radar_cats = df["category"].unique().tolist()
            fig3 = go.Figure()
            for i,m in enumerate(models_in):
                scores = [df[(df["model"]==m)&(df["category"]==c)]["score"].mean()*100
                          if len(df[(df["model"]==m)&(df["category"]==c)])>0 else 0
                          for c in radar_cats]
                scores_c = scores + [scores[0]]
                cats_c   = radar_cats + [radar_cats[0]]
                fig3.add_trace(go.Scatterpolar(
                    r=scores_c, theta=cats_c, fill="toself",
                    name=m, line_color=PALETTE[i%len(PALETTE)],
                    fillcolor=PALETTE[i%len(PALETTE)], opacity=0.3,
                ))
            fig3.update_layout(
                polar=dict(bgcolor=BG,
                    radialaxis=dict(visible=True,range=[0,100],gridcolor="#334155",color="#f8fafc"),
                    angularaxis=dict(color="#f8fafc"),
                ),
                paper_bgcolor=SURFACE, font=dict(color="#f8fafc"),
                title=dict(text="🎯 Score Radar by Category", font=dict(color="#f8fafc")),
                legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=60,r=30,t=50,b=60),
            )
            st.plotly_chart(fig3, use_container_width=True)

        with cd:
            # Latency by difficulty
            diff_order = {"easy":1,"medium":2,"hard":3}
            df2 = df.copy(); df2["dord"] = df2["difficulty"].map(diff_order)
            fig4 = go.Figure()
            for i,m in enumerate(models_in):
                mdf = (df2[df2["model"]==m].groupby(["difficulty","dord"])["total_time_ms"]
                       .mean().reset_index().sort_values("dord"))
                fig4.add_trace(go.Scatter(
                    x=mdf["difficulty"], y=mdf["total_time_ms"].round(0),
                    name=m, mode="lines+markers",
                    line=dict(color=PALETTE[i%len(PALETTE)],width=2), marker=dict(size=8),
                ))
            fig4.update_layout(**chart_layout("⏱️ Latency (ms) vs Difficulty"))
            st.plotly_chart(fig4, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Detailed Results
# ══════════════════════════════════════════════════════════════════════════════
with t4:
    st.markdown("### 🔍 Detailed Results")
    job_id4 = st.session_state.get("job_id")
    if not job_id4:
        st.info("Run a benchmark first.")
    else:
        res_data4, _ = api("get", f"/benchmark/{job_id4}/results")
        results4 = (res_data4 or {}).get("results",[])
        if not results4:
            st.info("No results yet.")
        else:
            df4 = pd.DataFrame(results4)
            sel_model4 = st.selectbox("Select model", df4["model"].unique().tolist())
            mdf4 = df4[df4["model"]==sel_model4].copy()

            def score_badge(s):
                if s >= 0.75: return f'<span class="score-high">{s:.0%}</span>'
                if s >= 0.4:  return f'<span class="score-mid">{s:.0%}</span>'
                return f'<span class="score-low">{s:.0%}</span>'

            st.markdown(f"**{len(mdf4)} questions** | Avg score: **{mdf4['score'].mean():.1%}** | Avg {mdf4['tokens_per_second'].mean():.1f} tok/s")

            # Response time histogram
            fig_hist = go.Figure(go.Histogram(
                x=mdf4["total_time_ms"], nbinsx=20,
                marker_color="#6366f1", opacity=0.8,
            ))
            fig_hist.update_layout(**chart_layout("Response Time Distribution (ms)"))
            fig_hist.update_layout(height=250)
            st.plotly_chart(fig_hist, use_container_width=True)

            st.markdown("---")
            for _, row in mdf4.sort_values("question_id").iterrows():
                badge = score_badge(row["score"])
                with st.expander(f"**{row['question_id']}** [{row['category']} / {row['difficulty']}] — Score: {row['score']:.0%} | {row['tokens_per_second']:.1f} tok/s | {row['total_time_ms']:.0f}ms"):
                    qa, qb = st.columns(2)
                    with qa:
                        st.markdown("**📝 Prompt**")
                        st.text_area("", row["prompt"], height=100, key=f"p_{row['question_id']}_{sel_model4}", disabled=True)
                        st.markdown("**✅ Expected Answer**")
                        st.info(row["expected_answer"])
                    with qb:
                        st.markdown("**🤖 Model Response**")
                        st.text_area("", row["response_text"], height=100, key=f"r_{row['question_id']}_{sel_model4}", disabled=True)
                        st.markdown(f"**Eval method:** `{row['evaluation_method']}` | **Score:** ", unsafe_allow_html=False)
                        st.markdown(badge, unsafe_allow_html=True)
                    if row.get("error"):
                        st.error(f"Error: {row['error']}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Playground
# ══════════════════════════════════════════════════════════════════════════════
with t5:
    st.markdown("### 💬 Chat Playground")
    models_d5, _ = api("get", "/models")
    model_list5 = [m["name"] for m in (models_d5 or {}).get("models",[])]

    if not model_list5:
        st.warning("No models available. Pull models in the Models tab.")
    else:
        compare_mode = st.toggle("⚡ Compare Mode (2 models side-by-side)")

        if compare_mode:
            pc1, pc2 = st.columns(2)
            with pc1: model_a = st.selectbox("Model A", model_list5, key="ma")
            with pc2: model_b = st.selectbox("Model B", model_list5, key="mb", index=min(1,len(model_list5)-1))
        else:
            model_a = st.selectbox("Model", model_list5, key="msingle")
            model_b = None

        with st.expander("⚙️ Parameters"):
            sc1,sc2,sc3 = st.columns(3)
            temp  = sc1.slider("Temperature", 0.0, 2.0, 0.7, 0.05)
            top_p = sc2.slider("Top-P", 0.0, 1.0, 0.9, 0.05)
            maxt  = sc3.slider("Max Tokens", 128, 4096, 1024, 128)

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask anything…")

        def call_model(model, messages, temp, top_p, maxt):
            res, err = api("post", "/chat", json={
                "model": model, "messages": messages,
                "temperature": temp, "top_p": top_p, "max_tokens": maxt
            })
            if err: return f"Error: {err}", 0.0
            return res.get("response",""), res.get("tokens_per_second", 0.0)

        if user_input:
            st.session_state.chat_history.append({"role":"user","content":user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            if compare_mode:
                col_a, col_b = st.columns(2)
                msgs = st.session_state.chat_history[:]
                with col_a:
                    st.markdown(f"**{model_a}**")
                    with st.spinner("Generating…"):
                        resp_a, tps_a = call_model(model_a, msgs, temp, top_p, maxt)
                    st.markdown(resp_a)
                    st.caption(f"⚡ {tps_a:.1f} tok/s")
                with col_b:
                    st.markdown(f"**{model_b}**")
                    with st.spinner("Generating…"):
                        resp_b, tps_b = call_model(model_b, msgs, temp, top_p, maxt)
                    st.markdown(resp_b)
                    st.caption(f"⚡ {tps_b:.1f} tok/s")
                st.session_state.chat_history.append(
                    {"role":"assistant","content":f"**{model_a}:** {resp_a}\n\n**{model_b}:** {resp_b}"}
                )
            else:
                with st.chat_message("assistant"):
                    with st.spinner(f"{model_a} thinking…"):
                        reply, tps = call_model(
                            model_a,
                            st.session_state.chat_history,
                            temp, top_p, maxt
                        )
                    st.markdown(reply)
                    st.caption(f"⚡ {tps:.1f} tok/s")
                st.session_state.chat_history.append({"role":"assistant","content":reply})

        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
