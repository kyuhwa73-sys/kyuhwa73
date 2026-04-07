"""
중소기업 규제영향 분석 시스템 v2 — Streamlit UI

실행: streamlit run app.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from assembly_client import AssemblyClient, AssemblyAPIError, Bill
from config import ASSEMBLY_API_KEY, DEFAULT_AGE, DEFAULT_MAX_BILLS
from sme_analyzer import SMEAnalyzer, ScreeningResult, ImpactAssessment
from report_generator import generate_html_assessment_report, generate_json_assessment_report
from main import SAMPLE_BILLS


# ─── 페이지 설정 ─────────────────────────────────────────────

st.set_page_config(
    page_title="중소기업 규제영향 분석 시스템",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────

st.markdown("""
<style>
/* 배지 */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 700;
    color: white;
    margin-right: 6px;
}
.badge-높음  { background: #e74c3c; }
.badge-중간  { background: #e67e22; }
.badge-낮음  { background: #27ae60; }

/* 권고사항 태그 */
.rec-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    color: white;
    margin-right: 6px;
}
.rec-정부     { background: #8e44ad; }
.rec-국회     { background: #2980b9; }
.rec-중소기업 { background: #27ae60; }

/* 부담 수준 */
.severity-높음 { color: #e74c3c; font-weight: 700; }
.severity-중간 { color: #e67e22; font-weight: 700; }
.severity-낮음 { color: #27ae60; font-weight: 700; }

/* 스크리닝 카드 */
.screen-card {
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 6px;
    font-size: 13px;
}
.screen-relevant { background: #fff3cd; border-left: 4px solid #e67e22; }
.screen-irrelevant { background: #f8f9fa; border-left: 4px solid #adb5bd; }
</style>
""", unsafe_allow_html=True)


# ─── 세션 상태 초기화 ─────────────────────────────────────────

def _init_state():
    defaults = {
        "screenings": [],
        "assessments": [],
        "fetched_bills": [],
        "age": DEFAULT_AGE,
        "running": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ─── 상수 ────────────────────────────────────────────────────

LEVEL_EMOJI  = {"높음": "🔴", "중간": "🟠", "낮음": "🟢"}
LEVEL_COLOR  = {"높음": "#e74c3c", "중간": "#e67e22", "낮음": "#27ae60"}
LEVEL_ORDER  = {"높음": 0, "중간": 1, "낮음": 2}
PRIORITY_ICON = {"즉시": "⚡", "단기(1년 내)": "📅", "중기(3년 내)": "📆"}


# ─── 사이드바 ─────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🏛 중소기업 규제영향\n### 분석 시스템 v2")
    st.divider()
    st.subheader("⚙️ 분석 설정")

    age_input = st.number_input(
        "국회 대수", min_value=1, max_value=22,
        value=DEFAULT_AGE, step=1,
        help="분석할 국회 대수 (현재 22대)",
    )

    # 기간 설정
    st.markdown("**📅 발의 기간**")
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input(
            "시작일",
            value=date(2024, 1, 1),
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            label_visibility="collapsed",
        )
    with col_e:
        end_date = st.date_input(
            "종료일",
            value=date.today(),
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            label_visibility="collapsed",
        )
    st.caption(f"  {start_date} ~ {end_date}")

    max_bills = st.slider(
        "최대 분석 법안 수", 1, 200,
        value=30,
        help="기간 내 수집 후 분석할 최대 법안 수",
    )

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        dry_run = st.checkbox(
            "테스트 모드",
            help="국회 API 없이 샘플 데이터 3건으로 테스트",
        )
    with col_b:
        show_irrelevant = st.checkbox(
            "미해당 표시",
            value=False,
            help="스크리닝에서 영향 없음 판정된 법안도 표시",
        )

    st.divider()

    run_btn = st.button(
        "▶  분석 시작",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.running,
    )
    if st.session_state.assessments:
        if st.button("🗑  결과 초기화", use_container_width=True):
            st.session_state.screenings = []
            st.session_state.assessments = []
            st.session_state.fetched_bills = []
            st.rerun()

    st.divider()
    st.caption(
        "**분석 방식**\n\n"
        "① AI가 법안을 읽고 중소기업 영향 여부 판단\n\n"
        "② 영향 있는 법안에 대해 규제영향평가서 자동 작성\n\n"
        "📌 Claude AI (현재 로그인 계정) 사용"
    )


# ─── 메인 헤더 ───────────────────────────────────────────────

st.title("🏛 중소기업 규제영향 분석 시스템")
st.caption(
    "국회 의원발의 법률안을 AI가 직접 검토하여 중소기업·소상공인 영향 여부를 판단하고, "
    "영향이 있는 법안에 대해 **공식 규제영향평가서**를 자동 작성합니다."
)
st.divider()


# ─── 분석 실행 ───────────────────────────────────────────────

if run_btn:
    st.session_state.running = True
    st.session_state.screenings = []
    st.session_state.assessments = []

    # 1단계: 법안 수집
    bills: list[Bill] = []

    if dry_run:
        bills = SAMPLE_BILLS[:max_bills]
        st.success(f"✅ 테스트 모드 — 샘플 법안 {len(bills)}건 준비")
    else:
        st.subheader("📥 법안 수집")
        st.caption(
            f"**{age_input}대 국회** · {start_date} ~ {end_date}  \n"
            "날짜 범위에 도달하면 자동으로 수집을 중단합니다."
        )

        fetch_prog   = st.progress(0.0, text="API 연결 중...")
        fetch_status = st.empty()   # 현재 페이지 날짜 범위
        fetch_count  = st.empty()   # 매칭 건수

        fetch_error: list[str] = []

        def on_page(page: int, total_pages: int, page_bills: list, matched: int) -> None:
            pct = min(page / max(total_pages, 1), 1.0)
            dates = [b.propose_dt for b in page_bills if b.propose_dt]
            d_min = min(dates) if dates else "—"
            d_max = max(dates) if dates else "—"
            fetch_prog.progress(
                pct,
                text=f"페이지 {page}/{total_pages}  |  {d_min} ~ {d_max}",
            )
            fetch_status.info(
                f"🔍 현재 페이지 날짜 범위: **{d_min} ~ {d_max}**  "
                f"(총 {len(page_bills)}건 / 전체 약 {total_pages}페이지)"
            )
            fetch_count.metric(
                label="기간 내 매칭 법안",
                value=f"{matched}건",
                delta=f"+{len([b for b in page_bills if start_date.strftime('%Y%m%d') <= b.propose_dt.replace('-','') <= end_date.strftime('%Y%m%d')])}건 (이번 페이지)",
            )

        try:
            client = AssemblyClient()
            bills = client.fetch_bills_in_range(
                age=age_input,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                max_bills=max_bills,
                verbose=False,
                on_page=on_page,
            )
            fetch_prog.progress(1.0, text="수집 완료!")
            fetch_status.empty()
            fetch_count.empty()
            st.success(f"✅ {len(bills)}건 수집 완료  ({start_date} ~ {end_date})")
        except AssemblyAPIError as exc:
            fetch_prog.empty()
            fetch_status.empty()
            fetch_count.empty()
            st.error(f"❌ 국회 API 오류: {exc}")
            st.session_state.running = False
            st.stop()

    if not bills:
        st.warning("⚠️ 해당 기간에 수집된 법안이 없습니다. 기간 또는 설정을 조정해 보세요.")
        st.session_state.running = False
        st.stop()

    st.session_state.fetched_bills = bills
    st.session_state.age = age_input

    # 2단계: Phase 1 스크리닝
    st.subheader(f"🤖 Phase 1 · AI 스크리닝 — {len(bills)}건")
    st.caption("Claude AI가 각 법안이 중소기업에 영향을 미치는지 직접 판단합니다.")

    prog1 = st.progress(0.0, text="스크리닝 준비 중...")
    status1 = st.empty()
    analyzer = SMEAnalyzer()
    screenings: list[ScreeningResult] = []

    for i, bill in enumerate(bills):
        prog1.progress(i / len(bills), text=f"스크리닝 {i+1}/{len(bills)}")
        status1.info(f"**[{i+1}/{len(bills)}]** {bill.bill_name}")
        sr = analyzer.screen_bill(bill, verbose=False)
        screenings.append(sr)

    prog1.progress(1.0, text="스크리닝 완료!")
    status1.empty()
    st.session_state.screenings = screenings

    relevant = [sr for sr in screenings if sr.is_sme_relevant and not sr.error]
    st.success(f"✅ 스크리닝 완료 — 영향 있음 **{len(relevant)}건** / 전체 {len(bills)}건")

    # 3단계: Phase 2 규제영향평가서
    assessments: list[ImpactAssessment] = []
    if relevant:
        st.subheader(f"📋 Phase 2 · 규제영향평가서 작성 — {len(relevant)}건")
        st.caption("영향 있는 법안에 대해 공식 규제영향평가서를 작성합니다. (법안당 약 30초)")

        prog2 = st.progress(0.0, text="평가서 작성 준비 중...")
        status2 = st.empty()

        for i, sr in enumerate(relevant):
            prog2.progress(i / len(relevant), text=f"평가서 {i+1}/{len(relevant)}")
            status2.info(f"**[{i+1}/{len(relevant)}]** {sr.bill.bill_name}")
            assessment = analyzer.assess_bill(sr.bill, sr, verbose=False)
            assessments.append(assessment)

        prog2.progress(1.0, text="평가서 작성 완료!")
        status2.empty()
        st.success(f"✅ 규제영향평가서 {len(assessments)}건 작성 완료!")
    else:
        st.info("ℹ️ 스크리닝 결과 중소기업에 영향을 미치는 법안이 없습니다.")

    st.session_state.assessments = assessments
    st.session_state.running = False


# ─── 결과 표시 ───────────────────────────────────────────────

screenings: list[ScreeningResult] = st.session_state.screenings
assessments: list[ImpactAssessment] = st.session_state.assessments

if not screenings:
    st.info(
        "👈 사이드바에서 설정 후 **▶ 분석 시작**을 클릭하세요.\n\n"
        "**분석 흐름:**  \n"
        "① 기간 내 법안 수집 → ② AI 스크리닝 (중소기업 영향 여부) "
        "→ ③ 영향 법안 규제영향평가서 자동 작성"
    )
    st.stop()


# ── 요약 메트릭 ──────────────────────────────────────────────

total = len(screenings)
relevant_cnt = sum(1 for s in screenings if s.is_sme_relevant)
errors_cnt = sum(1 for s in screenings if s.error)
assess_cnt = len(assessments)

st.subheader("📊 분석 결과 요약")
m0, m1, m2, m3, m4 = st.columns(5)
m0.metric("수집 법안", f"{total}건")
m1.metric("🟠 영향 있음", f"{relevant_cnt}건")
m2.metric("⚪ 영향 없음", f"{total - relevant_cnt - errors_cnt}건")
m3.metric("📋 평가서 작성", f"{assess_cnt}건")
m4.metric("⚠️ 오류", f"{errors_cnt}건")


# ── 차트 + 다운로드 ──────────────────────────────────────────

col_chart, col_dl = st.columns([3, 2])

with col_chart:
    # 영향 수준별 분포 (평가서 기준)
    level_counts = {"높음": 0, "중간": 0, "낮음": 0}
    for a in assessments:
        lvl = a.impact_level
        if lvl in level_counts:
            level_counts[lvl] += 1

    labels = list(level_counts.keys())
    values = list(level_counts.values())
    colors = [LEVEL_COLOR[l] for l in labels]

    fig = go.Figure(data=[go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=values, textposition="outside",
        width=0.5,
    )])
    fig.update_layout(
        title="규제영향평가서 — 영향 수준 분포",
        xaxis_title="", yaxis_title="법안 수",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, b=20, l=20, r=20), height=280,
        showlegend=False,
    )
    fig.update_yaxes(gridcolor="rgba(200,200,200,0.3)", tickformat="d")
    st.plotly_chart(fig, use_container_width=True)

with col_dl:
    if assessments:
        st.subheader("📥 보고서 다운로드")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        age_val = st.session_state.age

        # JSON
        try:
            json_data = generate_json_assessment_report(
                screenings, assessments, age=age_val
            )
            st.download_button(
                "📄 JSON 다운로드",
                data=json_data.encode("utf-8"),
                file_name=f"sme_assessment_{ts}.json",
                mime="application/json",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"JSON 생성 오류: {e}")

        # HTML
        try:
            html_data = generate_html_assessment_report(
                screenings, assessments, age=age_val
            )
            st.download_button(
                "🌐 HTML 규제영향평가서 다운로드",
                data=html_data.encode("utf-8"),
                file_name=f"sme_assessment_{ts}.html",
                mime="text/html",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"HTML 생성 오류: {e}")

        # 높음 법안 목록
        high_assessments = [a for a in assessments if a.impact_level == "높음"]
        if high_assessments:
            st.divider()
            st.markdown("**🔴 높은 규제영향 법안**")
            for a in high_assessments:
                st.markdown(f"- {a.bill.bill_name}")


# ── 스크리닝 결과 요약표 ────────────────────────────────────

st.divider()
st.subheader("🔍 Phase 1 · AI 스크리닝 결과")

screen_tab1, screen_tab2 = st.tabs([
    f"영향 있음 ({relevant_cnt}건)",
    f"전체 목록 ({total}건)",
])

with screen_tab1:
    rel_items = [s for s in screenings if s.is_sme_relevant]
    if not rel_items:
        st.info("영향 있는 법안이 없습니다.")
    else:
        for s in rel_items:
            st.markdown(
                f'<div class="screen-card screen-relevant">'
                f"<strong>{s.bill.bill_name}</strong><br>"
                f"<small>{s.bill.committee} | {s.bill.propose_dt} | 신뢰도: {s.confidence}</small><br>"
                f"{s.reason}"
                f"{'<br><em>' + s.impact_preview + '</em>' if s.impact_preview else ''}"
                f"</div>",
                unsafe_allow_html=True,
            )

with screen_tab2:
    rows = []
    for s in screenings:
        rows.append({
            "법안명": s.bill.bill_name,
            "소관위": s.bill.committee,
            "발의일": s.bill.propose_dt,
            "SME 영향": "✅ 있음" if s.is_sme_relevant else "➖ 없음",
            "신뢰도": s.confidence,
            "판단 근거": s.reason[:60] + "…" if len(s.reason) > 60 else s.reason,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── 규제영향평가서 상세 ──────────────────────────────────────

if assessments:
    st.divider()
    st.subheader("📋 Phase 2 · 규제영향평가서")

    # 영향 수준 필터
    filter_levels = st.multiselect(
        "영향 수준 필터",
        options=["높음", "중간", "낮음"],
        default=["높음", "중간", "낮음"],
        format_func=lambda x: f"{LEVEL_EMOJI.get(x, '')} {x}",
    )

    sorted_assessments = sorted(
        [a for a in assessments if a.impact_level in filter_levels],
        key=lambda a: LEVEL_ORDER.get(a.impact_level, 9),
    )

    if not sorted_assessments:
        st.info("선택한 필터에 해당하는 평가서가 없습니다.")
    else:
        for idx, a in enumerate(sorted_assessments, 1):
            emoji = LEVEL_EMOJI.get(a.impact_level, "⚪")
            proc = a.bill.proc_result or "계류 중"

            header = (
                f"{emoji} **{a.bill.bill_name}**  |  "
                f"{a.bill.committee}  |  {a.bill.propose_dt}  |  {proc}"
            )
            with st.expander(header, expanded=(idx == 1)):
                if a.error:
                    st.error(f"평가서 작성 오류: {a.error}")
                    continue

                # 배지 + 영향 요약
                st.markdown(
                    f'<span class="badge badge-{a.impact_level}">'
                    f"영향 수준: {a.impact_level}</span>",
                    unsafe_allow_html=True,
                )
                if a.impact_summary:
                    st.info(a.impact_summary)

                # 법안 기본 정보
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**법안번호** {a.bill.bill_no}")
                c2.markdown(f"**대표발의** {a.bill.rst_proposer}")
                c3.markdown(
                    f"**원문** [보기]({a.bill.detail_link})"
                    if a.bill.detail_link else "**원문** —"
                )

                tabs = st.tabs([
                    "Ⅰ. 규제 개요",
                    "Ⅱ. 필요성",
                    "Ⅲ. 영향 분석",
                    "Ⅳ. 중소기업 영향",
                    "Ⅴ. 대안·권고",
                    "Ⅵ. 종합 의견",
                ])

                # Ⅰ. 규제 개요
                with tabs[0]:
                    ov = a.regulation_overview
                    if ov:
                        st.markdown(f"**규제 유형:** {ov.get('regulation_type', '—')}")
                        st.markdown(f"**목적 및 내용:**")
                        st.write(ov.get("purpose", "—"))
                        provs = ov.get("key_provisions", [])
                        if provs:
                            st.markdown("**주요 조항:**")
                            for p in provs:
                                st.markdown(f"- {p}")
                    else:
                        st.caption("정보 없음")

                # Ⅱ. 규제 필요성
                with tabs[1]:
                    ne = a.regulation_necessity
                    if ne:
                        ne_level = ne.get("necessity_level", "—")
                        ne_color = LEVEL_COLOR.get(ne_level, "#888")
                        st.markdown(
                            f"**필요성 수준:** "
                            f'<span style="color:{ne_color}; font-weight:700">{ne_level}</span>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("**도입 배경:**")
                        st.write(ne.get("background", "—"))
                        st.markdown("**필요성 근거:**")
                        st.write(ne.get("necessity_rationale", "—"))
                    else:
                        st.caption("정보 없음")

                # Ⅲ. 규제 영향 분석
                with tabs[2]:
                    ia = a.impact_analysis
                    if ia:
                        left, right = st.columns(2)
                        with left:
                            st.markdown("**적용 대상**")
                            st.write(ia.get("affected_entities", "—"))
                            if ia.get("estimated_entity_count"):
                                st.caption(f"추정 규모: {ia['estimated_entity_count']}")
                            st.markdown("**사회적 편익**")
                            st.write(ia.get("public_benefits", "—"))
                        with right:
                            st.markdown("**비용 분석**")
                            cost_df = pd.DataFrame([
                                {"항목": "직접 순응 비용", "내용": ia.get("direct_cost", "—")},
                                {"항목": "행정 부담", "내용": ia.get("administrative_burden", "—")},
                                {"항목": "연간 지속 비용(업체당)", "내용": ia.get("annual_ongoing_cost", "—")},
                            ])
                            st.dataframe(cost_df, use_container_width=True, hide_index=True)
                        st.markdown("**비용-편익 종합**")
                        st.info(ia.get("cost_benefit_summary", "—"))
                    else:
                        st.caption("정보 없음")

                # Ⅳ. 중소기업 영향 분석
                with tabs[3]:
                    si = a.sme_impact
                    if si:
                        # 영향 받는 기업 유형
                        sme_types = si.get("affected_sme_types", [])
                        if sme_types:
                            st.markdown("**영향 받는 기업 유형**")
                            cols = st.columns(min(len(sme_types), 3))
                            for i, t in enumerate(sme_types):
                                cols[i % 3].markdown(f"- {t}")

                        # 세부 부담 항목
                        burdens = si.get("burden_details", [])
                        if burdens:
                            st.markdown("**세부 부담 항목**")
                            burden_df = pd.DataFrame([
                                {
                                    "유형": b.get("category", ""),
                                    "내용": b.get("description", ""),
                                    "심각도": b.get("severity", ""),
                                }
                                for b in burdens
                            ])
                            st.dataframe(burden_df, use_container_width=True, hide_index=True)

                        # 기회 요인 + 경감 방안
                        opp_col, mit_col = st.columns(2)
                        with opp_col:
                            opps = si.get("opportunity_factors", [])
                            if opps:
                                st.markdown("**💡 기회 요인**")
                                for o in opps:
                                    st.markdown(f"- {o}")
                        with mit_col:
                            mits = si.get("mitigation_measures", [])
                            if mits:
                                st.markdown("**🛡️ 부담 경감 방안**")
                                for m in mits:
                                    st.markdown(f"- {m}")
                    else:
                        st.caption("정보 없음")

                # Ⅴ. 대안 검토 + 권고사항
                with tabs[4]:
                    alt = a.alternatives
                    if alt:
                        st.markdown("**검토된 규제 대안**")
                        for al in alt.get("reviewed", []):
                            st.markdown(f"- {al}")
                        if alt.get("recommended"):
                            st.markdown("**권고 대안**")
                            st.success(alt["recommended"])

                    if a.recommendations:
                        st.markdown("**정책 권고사항**")
                        for rec in a.recommendations:
                            target = rec.get("target", "")
                            action = rec.get("action", "")
                            priority = rec.get("priority", "")
                            picon = PRIORITY_ICON.get(priority, "")
                            st.markdown(
                                f'<span class="rec-tag rec-{target}">{target}</span>'
                                f" {picon} **{priority}** — {action}",
                                unsafe_allow_html=True,
                            )
                            st.write("")

                # Ⅵ. 종합 의견
                with tabs[5]:
                    if a.overall_opinion:
                        st.markdown("**종합 의견**")
                        st.write(a.overall_opinion)
                    conf = a.analysis_confidence
                    conf_color = LEVEL_COLOR.get(conf, "#888")
                    st.divider()
                    st.markdown(
                        f"**분석 신뢰도:** "
                        f'<span style="color:{conf_color}; font-weight:700">{conf}</span>',
                        unsafe_allow_html=True,
                    )
                    if a.limitations:
                        st.caption(f"⚠️ 한계: {a.limitations}")

elif screenings:
    st.info("ℹ️ 스크리닝 결과 중소기업에 영향을 미치는 법안이 없어 평가서가 작성되지 않았습니다.")
