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

from sme_analyzer import AnalysisResult
from config import IMPACT_CATEGORIES


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
