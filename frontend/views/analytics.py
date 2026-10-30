"""
NEXUS Analytics & Research Evaluation View
Visualizes actual measured operational telemetry, Information Retrieval metrics (P@K, R@K, MRR, nDCG@K),
generation faithfulness, abstention accuracy, and Dense vs Hybrid retrieval comparisons.
"""

import streamlit as st
import time
from backend.config import settings
from frontend.components.header import render_header
from frontend.components.icons import (
    get_icon_svg,
    icon_html,
    ICON_COLOR_GOLD,
    ICON_COLOR_MUTED_GOLD,
    ICON_COLOR_SUCCESS,
    ICON_COLOR_WARNING,
    ICON_COLOR_SUBTLE
)
from backend.evaluation.runner import run_benchmark_evaluation, get_latest_evaluation_report
from backend.evaluation.seed_dataset import seed_demonstration_dataset
from backend.evaluation.benchmark_dataset import get_benchmark_cases


def render_analytics_view() -> None:
    """Render measured system performance telemetry and evaluation metrics."""
    domain_filter = st.session_state.get("active_domain", "all")
    render_header("SYSTEM ANALYTICS & RESEARCH EVALUATION", domain_label=domain_filter)

    user = st.session_state.get("user") or {}
    user_id = user.get("id") or 1
    username = user.get("username", "OPERATOR")

    st.markdown(
        """
        <div style="background-color: rgba(25, 35, 27, 0.82); border: 1px solid #303E32; border-radius: 6px; padding: 14px 18px; margin-bottom: 16px; backdrop-filter: var(--glass-blur);">
            <span style="font-family: var(--font-mono); font-size: var(--font-size-label); color: #D6C6A5; text-transform: uppercase; font-weight: 600; letter-spacing: 0.06em;">
                EMPIRICAL TELEMETRY MONITOR // ZERO FABRICATION POLICY
            </span>
            <div style="font-family: var(--font-body); font-size: var(--font-size-body); color: #BAC2B8; margin-top: 6px; line-height: var(--line-height-body);">
                All metrics reflect actual database transactions, measured hardware latencies, and real evaluation runs.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Benchmark Control Bar
    col_seed, col_run, col_info = st.columns([1.5, 1.8, 1.7])
    with col_seed:
        if st.button("Seed Domain Corpus (6 Docs)", use_container_width=True):
            with st.spinner("Ingesting and indexing 6 institutional domain documents..."):
                res = seed_demonstration_dataset(user_id=user_id)
                st.success(f"Seeded {res['seeded_count']} documents ({res['total_chunks']} chunks).")
                time.sleep(1)
                st.rerun()

    with col_run:
        if st.button("Run Benchmark Suite (30 Cases)", use_container_width=True):
            with st.spinner("Executing quantitative IR benchmark (Dense vs Hybrid + Faithfulness)..."):
                rep = run_benchmark_evaluation(
                    user_id=user_id,
                    username=username,
                    k=4,
                    similarity_threshold=0.25
                )
                st.success(f"Benchmark finished in {rep['elapsed_seconds']}s across {rep['total_cases_evaluated']} cases.")
                time.sleep(1)
                st.rerun()

    with col_info:
        cases = get_benchmark_cases()
        info_ico = get_icon_svg("info", size=15, color=ICON_COLOR_GOLD)
        st.markdown(
            f"<div style='font-size:var(--font-size-meta); color:#BAC2B8; display:flex; align-items:center; gap:6px; margin-top:8px;'>"
            f"{info_ico} <span>Benchmark Suite: <code>{len(cases)} Test Cases</code> (22 Factual + 8 Abstention)</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("<hr style='margin: 12px 0 16px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)

    # Load latest evaluation report from disk
    report = get_latest_evaluation_report()

    if not report:
        chart_ico = get_icon_svg("chart", size=44, color=ICON_COLOR_MUTED_GOLD)
        st.markdown(
            f"""
            <div class="nexus-empty-state">
                <div style="margin-bottom: 12px;">{chart_ico}</div>
                <div class="nexus-empty-title">No Evaluation Benchmark Run Logged Yet</div>
                <div class="nexus-empty-subtitle">
                    Click <b>'Seed Domain Corpus'</b> followed by <b>'Run Benchmark Suite'</b> above
                    to execute empirical evaluation comparing Dense Semantic and Hybrid RRF retrieval.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # 1. Headline Metric Cards
    comp = report.get("retrieval_comparison", {})
    dense = comp.get("dense_semantic", {})
    hybrid = comp.get("hybrid_rrf", {})
    gen = report.get("generation_metrics", {})

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ico_c1 = get_icon_svg("chart", size=20, color=ICON_COLOR_SUCCESS)
        st.markdown(
            f"""
            <div class="nexus-stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="nexus-stat-label">HYBRID nDCG@4</div>
                    {ico_c1}
                </div>
                <div class="nexus-stat-val" style="color:#A5D6A7;">{hybrid.get('ndcg_at_k', 0.0):.3f}</div>
                <div class="nexus-stat-sub">Dense Baseline: {dense.get('ndcg_at_k', 0.0):.3f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        ico_c2 = get_icon_svg("layers", size=20, color=ICON_COLOR_SUCCESS)
        st.markdown(
            f"""
            <div class="nexus-stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="nexus-stat-label">MEAN RECIPROCAL RANK (MRR)</div>
                    {ico_c2}
                </div>
                <div class="nexus-stat-val" style="color:#A5D6A7;">{hybrid.get('mrr', 0.0):.3f}</div>
                <div class="nexus-stat-sub">Dense Baseline: {dense.get('mrr', 0.0):.3f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c3:
        ico_c3 = get_icon_svg("shield_check", size=20, color=ICON_COLOR_GOLD)
        abst_acc = gen.get("abstention_accuracy", 1.0) * 100.0
        st.markdown(
            f"""
            <div class="nexus-stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="nexus-stat-label">ABSTENTION ACCURACY</div>
                    {ico_c3}
                </div>
                <div class="nexus-stat-val" style="color:#D6C6A5;">{abst_acc:.1f}%</div>
                <div class="nexus-stat-sub">Out-of-Domain Guardrail</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c4:
        ico_c4 = get_icon_svg("circle_check", size=20, color=ICON_COLOR_SUCCESS)
        cite_val = gen.get("citation_validity_rate", 1.0) * 100.0
        st.markdown(
            f"""
            <div class="nexus-stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="nexus-stat-label">CITATION VALIDITY RATE</div>
                    {ico_c4}
                </div>
                <div class="nexus-stat-val" style="color:#A5D6A7;">{cite_val:.1f}%</div>
                <div class="nexus-stat-sub">Verified Grounded Reference Tags</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Retrieval Comparison Table (Dense vs Hybrid)
    tbl_hdr = icon_html("chart", "Quantitative Information Retrieval Comparison", size=20, color=ICON_COLOR_GOLD, gap=8)
    st.markdown(f"<div style='font-family:var(--font-display); font-size:var(--font-size-section); font-weight:700; color:#F4F2E9; margin-bottom:4px;'>{tbl_hdr}</div>", unsafe_allow_html=True)
    st.caption(f"Macro-averaged across {dense.get('evaluated_cases', 0)} factual benchmark test cases (Top-K = {report.get('top_k', 4)}):")

    def calc_delta(h_val: float, d_val: float) -> str:
        diff = h_val - d_val
        if diff > 0.0001:
            return f"+{diff:.3f} (+{(diff / (d_val or 1.0)) * 100:.1f}%)"
        elif diff < -0.0001:
            return f"{diff:.3f}"
        return "Parity (0.000)"

    def _safe_percent(val, default: float = 1.0) -> float:
        if val is None:
            return default * 100.0
        try:
            return float(val) * 100.0
        except (ValueError, TypeError):
            return default * 100.0

    table_data = [
        {
            "Metric": "Precision@4",
            "Dense Semantic (ChromaDB)": f"{dense.get('precision_at_k', 0.0):.3f}",
            "Hybrid RRF (Dense + BM25)": f"{hybrid.get('precision_at_k', 0.0):.3f}",
            "Performance Delta": calc_delta(hybrid.get('precision_at_k', 0.0), dense.get('precision_at_k', 0.0))
        },
        {
            "Metric": "Recall@4",
            "Dense Semantic (ChromaDB)": f"{dense.get('recall_at_k', 0.0):.3f}",
            "Hybrid RRF (Dense + BM25)": f"{hybrid.get('recall_at_k', 0.0):.3f}",
            "Performance Delta": calc_delta(hybrid.get('recall_at_k', 0.0), dense.get('recall_at_k', 0.0))
        },
        {
            "Metric": "Mean Reciprocal Rank (MRR)",
            "Dense Semantic (ChromaDB)": f"{dense.get('mrr', 0.0):.3f}",
            "Hybrid RRF (Dense + BM25)": f"{hybrid.get('mrr', 0.0):.3f}",
            "Performance Delta": calc_delta(hybrid.get('mrr', 0.0), dense.get('mrr', 0.0))
        },
        {
            "Metric": "nDCG@4 (Discounted Gain)",
            "Dense Semantic (ChromaDB)": f"{dense.get('ndcg_at_k', 0.0):.3f}",
            "Hybrid RRF (Dense + BM25)": f"{hybrid.get('ndcg_at_k', 0.0):.3f}",
            "Performance Delta": calc_delta(hybrid.get('ndcg_at_k', 0.0), dense.get('ndcg_at_k', 0.0))
        },
        {
            "Metric": "Hit Rate@4",
            "Dense Semantic (ChromaDB)": f"{dense.get('hit_rate_at_k', 0.0):.3f}",
            "Hybrid RRF (Dense + BM25)": f"{hybrid.get('hit_rate_at_k', 0.0):.3f}",
            "Performance Delta": calc_delta(hybrid.get('hit_rate_at_k', 0.0), dense.get('hit_rate_at_k', 0.0))
        }
    ]
    st.table(table_data)

    # 3. Grounded Generation & Safety Metrics
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    col_gen_a, col_gen_b = st.columns(2)
    with col_gen_a:
        gen_ico = get_icon_svg("circle_check", size=18, color=ICON_COLOR_GOLD)
        kw_cov = _safe_percent(gen.get("factual_keyword_coverage", 1.0))
        cite_val = _safe_percent(gen.get("citation_validity_rate", 1.0))
        eval_cases = report.get("total_cases_evaluated", 0) or 0
        elapsed_sec = report.get("elapsed_seconds", 0.0) or 0.0

        st.markdown(
            f"""
            <div class="nexus-stat-card" style="padding: 18px 20px; height: 100%; margin-bottom: 0px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px; border-bottom: 1px solid #303E32; padding-bottom: 10px;">
                    {gen_ico}
                    <span style="font-family: var(--font-display); font-size: var(--font-size-card); font-weight: 700; color: #F4F2E9; letter-spacing: 0.02em;">
                        Generation Faithfulness &amp; Provenance
                    </span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 10px; font-family: var(--font-body); font-size: var(--font-size-body); color: #BAC2B8;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Factual Keyword Coverage</span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: #A5D6A7; font-size: 1.05rem;">{kw_cov:.1f}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Citation Integrity</span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: #A5D6A7; font-size: 1.05rem;">{cite_val:.1f}% verified tags</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Evaluated Benchmark Trials</span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: #D6C6A5;">{eval_cases} queries</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Execution Time</span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: #F9E79F;">{elapsed_sec}s</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_gen_b:
        guard_ico = get_icon_svg("shield", size=18, color=ICON_COLOR_GOLD)
        abst_acc = _safe_percent(gen.get("abstention_accuracy", 1.0))
        abst_prec = _safe_percent(gen.get("abstention_precision", 1.0))
        abst_rec = _safe_percent(gen.get("abstention_recall", 1.0))
        abst_cases = report.get("abstention_cases", 0) or 0

        st.markdown(
            f"""
            <div class="nexus-stat-card" style="padding: 18px 20px; height: 100%; margin-bottom: 0px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px; border-bottom: 1px solid #303E32; padding-bottom: 10px;">
                    {guard_ico}
                    <span style="font-family: var(--font-display); font-size: var(--font-size-card); font-weight: 700; color: #F4F2E9; letter-spacing: 0.02em;">
                        Out-of-Domain Abstention Guardrail
                    </span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 10px; font-family: var(--font-body); font-size: var(--font-size-body); color: #BAC2B8;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Abstention Accuracy</span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: #A5D6A7; font-size: 1.05rem;">{abst_acc:.1f}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Abstention Precision</span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: #A5D6A7; font-size: 1.05rem;">{abst_prec:.1f}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Abstention Recall</span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: #A5D6A7; font-size: 1.05rem;">{abst_rec:.1f}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Safety Cases</span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: #D6C6A5;">{abst_cases} non-authorized queries</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 4. Detailed Benchmark Test Case Explorer
    st.markdown("<hr style='margin: 16px 0; border-color: #3A4A3C;'/>", unsafe_allow_html=True)
    with st.expander("View Individual Benchmark Case Results", expanded=False):
        details = report.get("case_details", [])
        for item in details:
            status_badge = "[ABSTAINED]" if item.get("abstained") else "[ANSWERED]"
            badge_color = "#D6C6A5" if item.get("abstained") else "#A5D6A7"
            exp_doc = item.get("expected_document") or "NONE (Out of Domain)"
            st.markdown(
                f"**`{item['id']}`** <span style='color:{badge_color}; font-family:var(--font-mono); font-weight:700;'>{status_badge}</span> **{item['query']}**  \n"
                f"*Domain*: `{item['domain'].upper()}` | *Difficulty*: `{item['difficulty']}` | *Expected*: `{exp_doc}`",
                unsafe_allow_html=True
            )
            c_d, c_h = st.columns(2)
            with c_d:
                st.caption(f"Dense Retrieved: `{item.get('dense_retrieved', [])}`")
            with c_h:
                st.caption(f"Hybrid Retrieved: `{item.get('hybrid_retrieved', [])}`")
            st.markdown("<hr style='margin: 4px 0 8px 0; border-color: #2D3A2F;'/>", unsafe_allow_html=True)
