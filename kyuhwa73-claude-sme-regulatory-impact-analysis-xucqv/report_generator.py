"""
규제영향 분석 보고서 생성기

JSON 및 HTML 형식의 보고서를 생성합니다.
HTML 보고서는 색상 코딩된 영향 수준, 조항별 상세 분석,
통계 요약 등을 포함합니다.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from jinja2 import Environment, BaseLoader

from config import IMPACT_CATEGORIES

# AnalysisResult는 레거시 v1 함수에서만 사용 (타입 힌트용 지연 임포트)
try:
    from sme_analyzer import AnalysisResult  # type: ignore[attr-defined]
except ImportError:
    AnalysisResult = object  # type: ignore


# ─── HTML 템플릿 ──────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>중소기업 규제영향 분석 보고서</title>
<style>
  :root {
    --high: #e74c3c;
    --medium: #e67e22;
    --low: #27ae60;
    --none: #95a5a6;
    --bg: #f5f6fa;
    --card: #ffffff;
    --text: #2c3e50;
    --border: #dfe6e9;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Noto Sans KR', sans-serif; background: var(--bg);
         color: var(--text); font-size: 14px; line-height: 1.6; }
  .container { max-width: 1100px; margin: 0 auto; padding: 24px 16px; }

  /* 헤더 */
  header { background: #2c3e50; color: white; padding: 32px 16px; text-align: center; }
  header h1 { font-size: 24px; margin-bottom: 8px; }
  header .meta { opacity: 0.75; font-size: 13px; }

  /* 통계 카드 */
  .stats { display: flex; gap: 16px; flex-wrap: wrap; margin: 24px 0; }
  .stat-card { flex: 1; min-width: 150px; background: var(--card);
               border-radius: 8px; padding: 16px; text-align: center;
               box-shadow: 0 2px 6px rgba(0,0,0,.08); }
  .stat-card .num { font-size: 32px; font-weight: 700; }
  .stat-card .label { color: #7f8c8d; font-size: 12px; margin-top: 4px; }
  .stat-card.high .num { color: var(--high); }
  .stat-card.medium .num { color: var(--medium); }
  .stat-card.low .num { color: var(--low); }
  .stat-card.none .num { color: var(--none); }

  /* 법안 카드 */
  .bill-card { background: var(--card); border-radius: 10px; margin-bottom: 20px;
               box-shadow: 0 2px 8px rgba(0,0,0,.07); overflow: hidden; }
  .bill-header { padding: 16px 20px; display: flex; align-items: flex-start;
                 gap: 12px; border-bottom: 1px solid var(--border); }
  .impact-badge { padding: 4px 10px; border-radius: 16px; font-size: 11px;
                  font-weight: 700; white-space: nowrap; color: white; }
  .badge-HIGH { background: var(--high); }
  .badge-MEDIUM { background: var(--medium); }
  .badge-LOW { background: var(--low); }
  .badge-NONE { background: var(--none); }
  .bill-title { font-size: 16px; font-weight: 600; flex: 1; }
  .bill-meta { color: #7f8c8d; font-size: 12px; margin-top: 4px; }
  .bill-body { padding: 16px 20px; }

  /* 섹션 */
  .section { margin-bottom: 16px; }
  .section-title { font-size: 13px; font-weight: 700; color: #7f8c8d;
                   text-transform: uppercase; letter-spacing: .5px;
                   margin-bottom: 6px; }
  .summary-box { background: #f8f9fa; border-left: 3px solid #3498db;
                 padding: 10px 14px; border-radius: 0 6px 6px 0;
                 font-size: 14px; }

  /* 태그 목록 */
  .tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
  .tag { background: #edf2f7; border-radius: 4px; padding: 3px 8px;
         font-size: 12px; color: #4a5568; }

  /* 조항 테이블 */
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 6px; }
  th { background: #f0f3f7; padding: 8px 10px; text-align: left;
       font-weight: 600; color: #4a5568; }
  td { padding: 8px 10px; border-bottom: 1px solid #edf2f7; vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  .burden-높음 { color: var(--high); font-weight: 600; }
  .burden-중간 { color: var(--medium); font-weight: 600; }
  .burden-낮음 { color: var(--low); font-weight: 600; }

  /* 2컬럼 그리드 */
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 600px) { .two-col { grid-template-columns: 1fr; } }

  /* 비용 박스 */
  .cost-box { background: #fff8e1; border: 1px solid #ffc107;
              border-radius: 6px; padding: 10px 14px; }
  .cost-box .cost-row { display: flex; gap: 8px; margin-bottom: 4px; }
  .cost-box .cost-label { font-weight: 600; min-width: 80px; color: #7f8c8d; font-size: 12px; }

  /* 권고사항 */
  .rec-item { display: flex; gap: 8px; margin-bottom: 8px; }
  .rec-target { background: #3498db; color: white; border-radius: 4px;
                padding: 2px 8px; font-size: 11px; white-space: nowrap; height: fit-content; }
  .rec-target.정부 { background: #8e44ad; }
  .rec-target.국회 { background: #2980b9; }
  .rec-target.중소기업 { background: #27ae60; }

  /* 신뢰도 */
  .confidence { font-size: 12px; color: #7f8c8d; margin-top: 8px;
                padding: 6px 10px; background: #f8f9fa; border-radius: 4px; }
  .confidence .conf-높음 { color: var(--low); }
  .confidence .conf-중간 { color: var(--medium); }
  .confidence .conf-낮음 { color: var(--high); }

  /* 오류 카드 */
  .error-card { background: #fff5f5; border: 1px solid #feb2b2;
                padding: 12px 16px; border-radius: 6px; color: #c53030; font-size: 13px; }

  /* 링크 */
  a { color: #3498db; text-decoration: none; }
  a:hover { text-decoration: underline; }

  /* 푸터 */
  footer { text-align: center; color: #b2bec3; font-size: 12px;
           padding: 32px 0 16px; }
</style>
</head>
<body>
<header>
  <h1>중소기업 규제영향 분석 보고서</h1>
  <div class="meta">
    {{ age }}대 국회 의원발의 법률안 &nbsp;|&nbsp;
    분석 법안: {{ results|length }}건 &nbsp;|&nbsp;
    생성일시: {{ generated_at }}
  </div>
</header>

<div class="container">

  <!-- 통계 요약 -->
  <div class="stats">
    <div class="stat-card">
      <div class="num">{{ results|length }}</div>
      <div class="label">분석 법안 수</div>
    </div>
    <div class="stat-card high">
      <div class="num">{{ stats.HIGH }}</div>
      <div class="label">높음 (HIGH)</div>
    </div>
    <div class="stat-card medium">
      <div class="num">{{ stats.MEDIUM }}</div>
      <div class="label">중간 (MEDIUM)</div>
    </div>
    <div class="stat-card low">
      <div class="num">{{ stats.LOW }}</div>
      <div class="label">낮음 (LOW)</div>
    </div>
    <div class="stat-card none">
      <div class="num">{{ stats.NONE }}</div>
      <div class="label">해당없음 (NONE)</div>
    </div>
  </div>

  <!-- 법안별 분석 결과 -->
  {% for r in results %}
  <div class="bill-card">
    <div class="bill-header">
      <span class="impact-badge badge-{{ r.impact_level }}">
        {{ r.impact_level }} — {{ r.impact_label }}
      </span>
      <div style="flex:1">
        <div class="bill-title">
          {% if r.bill.detail_link %}
            <a href="{{ r.bill.detail_link }}" target="_blank">{{ r.bill.bill_name }}</a>
          {% else %}
            {{ r.bill.bill_name }}
          {% endif %}
        </div>
        <div class="bill-meta">
          {{ r.bill.bill_no }} &nbsp;|&nbsp;
          소관위: {{ r.bill.committee }} &nbsp;|&nbsp;
          발의: {{ r.bill.propose_dt }} &nbsp;|&nbsp;
          대표발의: {{ r.bill.rst_proposer }} &nbsp;|&nbsp;
          처리: {{ r.bill.proc_result or '계류 중' }}
        </div>
      </div>
    </div>

    <div class="bill-body">
      {% if r.error %}
      <div class="error-card">분석 오류: {{ r.error }}</div>
      {% else %}

      <!-- 요약 -->
      <div class="section">
        <div class="section-title">규제영향 요약</div>
        <div class="summary-box">{{ r.impact_summary }}</div>
      </div>

      <!-- 영향 기업 유형 -->
      {% if r.affected_sme_types %}
      <div class="section">
        <div class="section-title">영향 받는 중소기업 유형</div>
        <div class="tags">
          {% for t in r.affected_sme_types %}
          <span class="tag">{{ t }}</span>
          {% endfor %}
        </div>
      </div>
      {% endif %}

      <!-- 주요 조항 -->
      {% if r.key_provisions %}
      <div class="section">
        <div class="section-title">주요 규제 조항 분석</div>
        <table>
          <thead>
            <tr><th>조항 내용</th><th>중소기업 영향</th><th>부담 수준</th></tr>
          </thead>
          <tbody>
            {% for p in r.key_provisions %}
            <tr>
              <td>{{ p.provision }}</td>
              <td>{{ p.impact }}</td>
              <td class="burden-{{ p.burden_level }}">{{ p.burden_level }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% endif %}

      <!-- 준수 비용 -->
      <div class="section">
        <div class="section-title">준수 비용 추정</div>
        <div class="cost-box">
          <div class="cost-row">
            <span class="cost-label">초기 비용</span>
            <span>{{ r.compliance_cost.initial_cost }}</span>
          </div>
          <div class="cost-row">
            <span class="cost-label">연간 비용</span>
            <span>{{ r.compliance_cost.ongoing_cost }}</span>
          </div>
          {% if r.compliance_cost.cost_notes %}
          <div class="cost-row" style="margin-top:6px; font-size:12px; color:#7f8c8d;">
            <span class="cost-label">참고</span>
            <span>{{ r.compliance_cost.cost_notes }}</span>
          </div>
          {% endif %}
        </div>
      </div>

      <!-- 위험/기회 요인 -->
      <div class="two-col">
        {% if r.risk_factors %}
        <div class="section">
          <div class="section-title">위험 요인</div>
          <ul style="padding-left:16px;">
            {% for rf in r.risk_factors %}
            <li style="margin-bottom:4px; color:#c53030;">{{ rf }}</li>
            {% endfor %}
          </ul>
        </div>
        {% endif %}
        {% if r.opportunity_factors %}
        <div class="section">
          <div class="section-title">기회 요인</div>
          <ul style="padding-left:16px;">
            {% for of_ in r.opportunity_factors %}
            <li style="margin-bottom:4px; color:#27ae60;">{{ of_ }}</li>
            {% endfor %}
          </ul>
        </div>
        {% endif %}
      </div>

      <!-- 정책 권고사항 -->
      {% if r.recommendations %}
      <div class="section">
        <div class="section-title">정책 권고사항</div>
        {% for rec in r.recommendations %}
        <div class="rec-item">
          <span class="rec-target {{ rec.target }}">{{ rec.target }}</span>
          <span>{{ rec.action }}</span>
        </div>
        {% endfor %}
      </div>
      {% endif %}

      <!-- 분석 신뢰도 -->
      <div class="confidence">
        <strong>분석 신뢰도:</strong>
        <span class="conf-{{ r.analysis_confidence }}">{{ r.analysis_confidence }}</span>
        {% if r.limitations %}
        &nbsp;—&nbsp;{{ r.limitations }}
        {% endif %}
      </div>

      {% endif %}
    </div>
  </div>
  {% endfor %}

</div>
<footer>
  본 보고서는 Claude AI를 활용한 자동 분석 결과입니다.
  정책 결정 시 법안 원문 및 전문가 검토를 병행하시기 바랍니다.<br>
  생성: {{ generated_at }}
</footer>
</body>
</html>
"""


# ─── 보고서 생성 함수 ─────────────────────────────────────────

def generate_json_report(
    results: list[AnalysisResult],
    age: int,
    output_path: str,
) -> None:
    """JSON 형식 보고서 저장"""
    report: dict[str, Any] = {
        "metadata": {
            "age": age,
            "generated_at": datetime.now().isoformat(),
            "total_bills": len(results),
            "statistics": _compute_stats(results),
        },
        "results": [r.to_dict() for r in results],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def generate_html_report(
    results: list[AnalysisResult],
    age: int,
    output_path: str,
) -> None:
    """HTML 형식 보고서 저장"""
    stats = _compute_stats(results)

    # 영향 수준 높은 순 정렬 (HIGH → MEDIUM → LOW → NONE → 오류)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 3}
    sorted_results = sorted(
        results, key=lambda r: order.get(r.impact_level, 4)
    )

    env = Environment(loader=BaseLoader())
    template = env.from_string(HTML_TEMPLATE)
    html = template.render(
        results=sorted_results,
        age=age,
        stats=stats,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        IMPACT_CATEGORIES=IMPACT_CATEGORIES,
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def _compute_stats(results: list[AnalysisResult]) -> dict[str, int]:
    stats: dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    for r in results:
        level = r.impact_level if r.impact_level in stats else "NONE"
        stats[level] += 1
    return stats


# ─── v2 규제영향평가서 보고서 함수 ────────────────────────────

ASSESSMENT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>중소기업 규제영향평가서</title>
<style>
:root{--high:#e74c3c;--mid:#e67e22;--low:#27ae60;--none:#95a5a6;
      --bg:#f5f6fa;--card:#fff;--text:#2c3e50;--border:#dfe6e9;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Noto Sans KR',sans-serif;background:var(--bg);color:var(--text);
     font-size:14px;line-height:1.7;}
.container{max-width:1100px;margin:0 auto;padding:24px 16px;}
header{background:#1a252f;color:#fff;padding:32px 16px;text-align:center;}
header h1{font-size:22px;margin-bottom:6px;}
header .meta{opacity:.7;font-size:13px;}
/* 통계 */
.stats{display:flex;gap:14px;flex-wrap:wrap;margin:24px 0;}
.stat-card{flex:1;min-width:140px;background:var(--card);border-radius:8px;
           padding:14px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.07);}
.stat-card .num{font-size:28px;font-weight:700;}
.stat-card .label{color:#7f8c8d;font-size:11px;margin-top:3px;}
.stat-card.high .num{color:var(--high);}
.stat-card.mid  .num{color:var(--mid);}
.stat-card.low  .num{color:var(--low);}
/* 스크리닝 목록 */
.screen-list{margin:0 0 24px;}
.screen-item{display:flex;align-items:flex-start;gap:10px;
             padding:10px 14px;background:var(--card);border-radius:6px;
             margin-bottom:6px;box-shadow:0 1px 4px rgba(0,0,0,.05);}
.screen-item.rel{border-left:4px solid var(--mid);}
.screen-item.irr{border-left:4px solid var(--none);opacity:.7;}
.screen-mark{font-size:16px;flex-shrink:0;margin-top:1px;}
.screen-info{flex:1;}
.screen-title{font-weight:600;font-size:14px;}
.screen-meta{color:#7f8c8d;font-size:12px;margin-top:2px;}
.screen-reason{font-size:13px;margin-top:4px;}
/* 평가서 카드 */
.assessment-card{background:var(--card);border-radius:10px;margin-bottom:28px;
                 box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden;}
.card-header{padding:18px 22px;border-bottom:1px solid var(--border);}
.card-header .impact-badge{display:inline-block;padding:4px 12px;border-radius:14px;
  font-size:12px;font-weight:700;color:#fff;margin-bottom:8px;}
.badge-높음{background:var(--high);}
.badge-중간{background:var(--mid);}
.badge-낮음{background:var(--low);}
.card-header h2{font-size:17px;font-weight:700;margin-bottom:4px;}
.card-meta{color:#7f8c8d;font-size:12px;}
.card-body{padding:20px 22px;}
/* 섹션 */
.section{margin-bottom:20px;}
.section-title{font-size:13px;font-weight:700;color:#7f8c8d;
  text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px;
  padding-bottom:4px;border-bottom:1px solid var(--border);}
.summary-box{background:#eaf4fb;border-left:3px solid #3498db;
  padding:10px 14px;border-radius:0 6px 6px 0;font-size:14px;}
/* 탭 레이아웃 */
.tabs{display:flex;gap:0;border-bottom:2px solid var(--border);margin-bottom:16px;}
.tab-label{padding:8px 16px;font-size:13px;font-weight:600;color:#7f8c8d;
  cursor:default;border-bottom:2px solid transparent;margin-bottom:-2px;}
/* 테이블 */
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px;}
th{background:#f0f3f7;padding:8px 10px;text-align:left;font-weight:600;color:#4a5568;}
td{padding:8px 10px;border-bottom:1px solid #edf2f7;vertical-align:top;}
tr:last-child td{border-bottom:none;}
/* 2컬럼 */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
@media(max-width:600px){.two-col{grid-template-columns:1fr;}}
/* 태그 */
.tag{display:inline-block;background:#edf2f7;border-radius:4px;
     padding:3px 8px;font-size:12px;color:#4a5568;margin:2px;}
.rec-tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;
  font-weight:700;color:#fff;margin-right:6px;}
.rec-정부{background:#8e44ad;}.rec-국회{background:#2980b9;}.rec-중소기업{background:#27ae60;}
.priority{color:#7f8c8d;font-size:11px;}
/* 비용박스 */
.cost-box{background:#fff8e1;border:1px solid #ffc107;border-radius:6px;padding:12px 14px;}
.cost-row{display:flex;gap:8px;margin-bottom:4px;}
.cost-label{font-weight:600;min-width:110px;color:#7f8c8d;font-size:12px;}
/* 심각도 */
.sev-높음{color:var(--high);font-weight:700;}
.sev-중간{color:var(--mid);font-weight:700;}
.sev-낮음{color:var(--low);font-weight:700;}
/* 신뢰도 */
.confidence-box{background:#f8f9fa;border-radius:6px;padding:8px 12px;
  font-size:12px;color:#7f8c8d;margin-top:8px;}
/* 링크 */
a{color:#3498db;text-decoration:none;}
a:hover{text-decoration:underline;}
footer{text-align:center;color:#b2bec3;font-size:12px;padding:32px 0 16px;}
ul.item-list{padding-left:18px;}
ul.item-list li{margin-bottom:4px;}
</style>
</head>
<body>
<header>
  <h1>중소기업 규제영향평가서</h1>
  <div class="meta">
    {{ age }}대 국회 의원발의 법률안 &nbsp;|&nbsp;
    스크리닝: {{ screenings|length }}건 &nbsp;|&nbsp;
    평가서 작성: {{ assessments|length }}건 &nbsp;|&nbsp;
    생성일시: {{ generated_at }}
  </div>
</header>

<div class="container">

<!-- 통계 요약 -->
<div class="stats">
  <div class="stat-card">
    <div class="num">{{ screenings|length }}</div>
    <div class="label">스크리닝 법안</div>
  </div>
  <div class="stat-card">
    <div class="num">{{ assessments|length }}</div>
    <div class="label">평가서 작성</div>
  </div>
  <div class="stat-card high">
    <div class="num">{{ stats.높음 }}</div>
    <div class="label">높음</div>
  </div>
  <div class="stat-card mid">
    <div class="num">{{ stats.중간 }}</div>
    <div class="label">중간</div>
  </div>
  <div class="stat-card low">
    <div class="num">{{ stats.낮음 }}</div>
    <div class="label">낮음</div>
  </div>
</div>

<!-- 스크리닝 결과 목록 -->
<h2 style="font-size:16px;margin-bottom:12px;">📋 Phase 1 · AI 스크리닝 결과</h2>
<div class="screen-list">
{% for s in screenings %}
<div class="screen-item {{ 'rel' if s.is_sme_relevant else 'irr' }}">
  <span class="screen-mark">{{ '✅' if s.is_sme_relevant else '➖' }}</span>
  <div class="screen-info">
    <div class="screen-title">{{ s.bill.bill_name }}</div>
    <div class="screen-meta">
      {{ s.bill.committee }} | {{ s.bill.propose_dt }} | 신뢰도: {{ s.confidence }}
    </div>
    <div class="screen-reason">{{ s.reason }}</div>
    {% if s.impact_preview %}
    <div class="screen-reason" style="color:#e67e22;font-style:italic;">
      → {{ s.impact_preview }}
    </div>
    {% endif %}
  </div>
</div>
{% endfor %}
</div>

<!-- 규제영향평가서 -->
{% if assessments %}
<h2 style="font-size:16px;margin:28px 0 14px;">📑 Phase 2 · 규제영향평가서</h2>
{% for a in assessments %}
<div class="assessment-card">
  <div class="card-header">
    <div><span class="impact-badge badge-{{ a.impact_level }}">
      영향 수준: {{ a.impact_level }}
    </span></div>
    <h2>{% if a.bill.detail_link %}<a href="{{ a.bill.detail_link }}" target="_blank">{{ a.bill.bill_name }}</a>{% else %}{{ a.bill.bill_name }}{% endif %}</h2>
    <div class="card-meta">
      {{ a.bill.bill_no }} | 소관위: {{ a.bill.committee }} |
      발의: {{ a.bill.propose_dt }} | 대표발의: {{ a.bill.rst_proposer }} |
      처리: {{ a.bill.proc_result or '계류 중' }}
    </div>
  </div>
  <div class="card-body">
    {% if a.error %}
    <div style="color:#c53030;background:#fff5f5;padding:10px;border-radius:6px;">오류: {{ a.error }}</div>
    {% else %}

    <!-- 영향 요약 -->
    {% if a.sme_impact.impact_summary %}
    <div class="section">
      <div class="summary-box">{{ a.sme_impact.impact_summary }}</div>
    </div>
    {% endif %}

    <div class="tabs">
      <span class="tab-label">Ⅰ. 규제 개요</span>
      <span class="tab-label">Ⅱ. 필요성</span>
      <span class="tab-label">Ⅲ. 영향 분석</span>
      <span class="tab-label">Ⅳ. 중소기업 영향</span>
      <span class="tab-label">Ⅴ. 대안·권고</span>
      <span class="tab-label">Ⅵ. 종합 의견</span>
    </div>

    <!-- Ⅰ. 규제 개요 -->
    <div class="section">
      <div class="section-title">Ⅰ. 규제 개요</div>
      <p><strong>규제 유형:</strong> {{ a.regulation_overview.regulation_type or '—' }}</p>
      <p style="margin-top:6px;"><strong>목적 및 내용:</strong> {{ a.regulation_overview.purpose or '—' }}</p>
      {% if a.regulation_overview.key_provisions %}
      <p style="margin-top:8px;"><strong>주요 조항:</strong></p>
      <ul class="item-list">
        {% for p in a.regulation_overview.key_provisions %}
        <li>{{ p }}</li>
        {% endfor %}
      </ul>
      {% endif %}
    </div>

    <!-- Ⅱ. 규제 필요성 -->
    <div class="section">
      <div class="section-title">Ⅱ. 규제 필요성</div>
      <p><strong>필요성 수준:</strong>
        <span class="sev-{{ a.regulation_necessity.necessity_level or '중간' }}">
          {{ a.regulation_necessity.necessity_level or '—' }}
        </span>
      </p>
      <p style="margin-top:6px;"><strong>도입 배경:</strong> {{ a.regulation_necessity.background or '—' }}</p>
      <p style="margin-top:6px;"><strong>필요성 근거:</strong> {{ a.regulation_necessity.necessity_rationale or '—' }}</p>
    </div>

    <!-- Ⅲ. 규제 영향 분석 -->
    <div class="section">
      <div class="section-title">Ⅲ. 규제 영향 분석</div>
      <div class="two-col">
        <div>
          <p><strong>적용 대상</strong></p>
          <p>{{ a.impact_analysis.affected_entities or '—' }}</p>
          {% if a.impact_analysis.estimated_entity_count %}
          <p style="color:#7f8c8d;font-size:12px;margin-top:4px;">추정 규모: {{ a.impact_analysis.estimated_entity_count }}</p>
          {% endif %}
          <p style="margin-top:10px;"><strong>사회적 편익</strong></p>
          <p>{{ a.impact_analysis.public_benefits or '—' }}</p>
        </div>
        <div>
          <div class="cost-box">
            <div class="cost-row"><span class="cost-label">직접 순응 비용</span><span>{{ a.impact_analysis.direct_cost or '—' }}</span></div>
            <div class="cost-row"><span class="cost-label">행정 부담</span><span>{{ a.impact_analysis.administrative_burden or '—' }}</span></div>
            <div class="cost-row"><span class="cost-label">연간 지속(업체당)</span><span>{{ a.impact_analysis.annual_ongoing_cost or '—' }}</span></div>
          </div>
        </div>
      </div>
      {% if a.impact_analysis.cost_benefit_summary %}
      <div class="summary-box" style="margin-top:12px;">{{ a.impact_analysis.cost_benefit_summary }}</div>
      {% endif %}
    </div>

    <!-- Ⅳ. 중소기업 영향 분석 -->
    <div class="section">
      <div class="section-title">Ⅳ. 중소기업 영향 분석</div>
      {% if a.sme_impact.affected_sme_types %}
      <p><strong>영향 기업 유형</strong></p>
      <div style="margin:6px 0 10px;">
        {% for t in a.sme_impact.affected_sme_types %}<span class="tag">{{ t }}</span>{% endfor %}
      </div>
      {% endif %}
      {% if a.sme_impact.burden_details %}
      <p><strong>세부 부담 항목</strong></p>
      <table>
        <thead><tr><th>유형</th><th>내용</th><th>심각도</th></tr></thead>
        <tbody>
          {% for b in a.sme_impact.burden_details %}
          <tr>
            <td>{{ b.category }}</td>
            <td>{{ b.description }}</td>
            <td class="sev-{{ b.severity }}">{{ b.severity }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% endif %}
      <div class="two-col" style="margin-top:12px;">
        {% if a.sme_impact.opportunity_factors %}
        <div>
          <p><strong>💡 기회 요인</strong></p>
          <ul class="item-list" style="color:#27ae60;">
            {% for o in a.sme_impact.opportunity_factors %}<li>{{ o }}</li>{% endfor %}
          </ul>
        </div>
        {% endif %}
        {% if a.sme_impact.mitigation_measures %}
        <div>
          <p><strong>🛡️ 부담 경감 방안</strong></p>
          <ul class="item-list">
            {% for m in a.sme_impact.mitigation_measures %}<li>{{ m }}</li>{% endfor %}
          </ul>
        </div>
        {% endif %}
      </div>
    </div>

    <!-- Ⅴ. 대안 검토 + 권고사항 -->
    <div class="section">
      <div class="section-title">Ⅴ. 대안 검토 및 정책 권고사항</div>
      {% if a.alternatives.reviewed %}
      <p><strong>검토된 규제 대안</strong></p>
      <ul class="item-list" style="margin-bottom:10px;">
        {% for al in a.alternatives.reviewed %}<li>{{ al }}</li>{% endfor %}
      </ul>
      {% endif %}
      {% if a.alternatives.recommended %}
      <p><strong>권고 대안:</strong> {{ a.alternatives.recommended }}</p>
      {% endif %}
      {% if a.recommendations %}
      <p style="margin-top:12px;"><strong>정책 권고사항</strong></p>
      {% for rec in a.recommendations %}
      <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;">
        <span class="rec-tag rec-{{ rec.target }}">{{ rec.target }}</span>
        <span class="priority">{{ rec.priority }}</span>
        <span>{{ rec.action }}</span>
      </div>
      {% endfor %}
      {% endif %}
    </div>

    <!-- Ⅵ. 종합 의견 -->
    <div class="section">
      <div class="section-title">Ⅵ. 종합 의견</div>
      <p>{{ a.overall_opinion or '—' }}</p>
      <div class="confidence-box" style="margin-top:10px;">
        <strong>분석 신뢰도:</strong> {{ a.analysis_confidence }}
        {% if a.limitations %} &nbsp;|&nbsp; ⚠️ {{ a.limitations }}{% endif %}
      </div>
    </div>

    {% endif %}
  </div>
</div>
{% endfor %}
{% endif %}

</div>
<footer>
  본 보고서는 Claude AI를 활용한 중소기업 규제영향평가서입니다.
  법안 원문 미열람 분석이므로 정책 결정 시 법안 원문 및 전문가 검토를 병행하시기 바랍니다.<br>
  생성: {{ generated_at }}
</footer>
</body>
</html>
"""


def generate_json_assessment_report(
    screenings: list,
    assessments: list,
    age: int,
) -> str:
    """v2 JSON 보고서 생성 (문자열 반환)"""
    from sme_analyzer import ScreeningResult, ImpactAssessment

    stats = {"높음": 0, "중간": 0, "낮음": 0}
    for a in assessments:
        lvl = a.impact_level
        if lvl in stats:
            stats[lvl] += 1

    report = {
        "metadata": {
            "age": age,
            "generated_at": datetime.now().isoformat(),
            "total_screened": len(screenings),
            "total_assessed": len(assessments),
            "statistics": stats,
        },
        "screenings": [
            {
                "bill_no": s.bill.bill_no,
                "bill_name": s.bill.bill_name,
                "committee": s.bill.committee,
                "propose_dt": s.bill.propose_dt,
                "is_sme_relevant": s.is_sme_relevant,
                "confidence": s.confidence,
                "reason": s.reason,
                "impact_preview": s.impact_preview,
            }
            for s in screenings
        ],
        "assessments": [a.to_dict() for a in assessments],
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


def generate_html_assessment_report(
    screenings: list,
    assessments: list,
    age: int,
) -> str:
    """v2 HTML 규제영향평가서 생성 (문자열 반환)"""
    stats = {"높음": 0, "중간": 0, "낮음": 0}
    for a in assessments:
        lvl = a.impact_level
        if lvl in stats:
            stats[lvl] += 1

    order = {"높음": 0, "중간": 1, "낮음": 2}
    sorted_assessments = sorted(
        assessments,
        key=lambda a: order.get(a.impact_level, 9),
    )

    env = Environment(loader=BaseLoader())
    template = env.from_string(ASSESSMENT_HTML_TEMPLATE)
    return template.render(
        screenings=screenings,
        assessments=sorted_assessments,
        age=age,
        stats=stats,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def print_summary(results: list[AnalysisResult]) -> None:
    """콘솔 요약 출력"""
    stats = _compute_stats(results)
    total = len(results)
    errors = sum(1 for r in results if r.error)

    print("\n" + "=" * 60)
    print("중소기업 규제영향 분석 결과 요약")
    print("=" * 60)
    print(f"  분석 법안:   {total}건")
    print(f"  HIGH  (높음): {stats['HIGH']}건")
    print(f"  MEDIUM(중간): {stats['MEDIUM']}건")
    print(f"  LOW   (낮음): {stats['LOW']}건")
    print(f"  NONE(해당없음): {stats['NONE']}건")
    if errors:
        print(f"  오류:        {errors}건")
    print("=" * 60)

    # HIGH 법안 목록 출력
    high_bills = [r for r in results if r.impact_level == "HIGH"]
    if high_bills:
        print("\n[주의] 높은 규제영향 법안:")
        for r in high_bills:
            print(f"  ▶ {r.bill.bill_name}")
            if r.impact_summary:
                print(f"    {r.impact_summary[:80]}...")
