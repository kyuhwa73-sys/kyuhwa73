"""
중소기업 규제영향 분석기 v2 — AI 직접 판단 방식

Phase 1 · 스크리닝
  Claude가 법안명·소관위원회 등을 읽고
  중소기업에 대한 영향 여부를 직접 판단합니다.

Phase 2 · 규제영향평가서 작성
  스크리닝에서 '영향 있음'으로 판정된 법안에 대해
  공식 규제영향평가서 형식의 심층 보고서를 작성합니다.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

from assembly_client import Bill


# ─── 스크리닝 스키마 ──────────────────────────────────────────

SCREENING_SCHEMA = {
    "type": "object",
    "properties": {
        "is_sme_relevant": {
            "type": "boolean",
            "description": "중소기업·소상공인·스타트업·벤처기업에 직접·간접 영향 여부",
        },
        "confidence": {
            "type": "string",
            "enum": ["높음", "중간", "낮음"],
            "description": "판단 신뢰도",
        },
        "reason": {
            "type": "string",
            "description": "판단 근거 (1~2문장)",
        },
        "impact_preview": {
            "type": "string",
            "description": "영향이 있는 경우, 예상되는 주요 영향 방향 (1문장)",
        },
    },
    "required": ["is_sme_relevant", "confidence", "reason"],
}

SCREENING_SYSTEM = """당신은 대한민국 중소기업 정책 전문가입니다.
의원발의 법률안 정보(법안명, 소관위원회, 발의자 등)를 보고
해당 법안이 중소기업·소상공인·스타트업·벤처기업에 직접적 또는 간접적인 영향을 미치는지 판단합니다.

판단 기준:
1. 규제·의무·부담이 중소기업에 적용되는가?
2. 세금·비용·인허가·노동 조건에 영향을 주는가?
3. 대기업과 중소기업이 차별적으로 영향받는가?
4. 중소기업 지원·육성에 관한 내용인가?

반드시 유효한 JSON만 반환하십시오."""


# ─── 규제영향평가서 스키마 ─────────────────────────────────────

ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {

        # I. 규제 개요
        "regulation_overview": {
            "type": "object",
            "properties": {
                "purpose": {"type": "string", "description": "법안의 목적 및 핵심 내용"},
                "regulation_type": {
                    "type": "string",
                    "enum": ["진입규제", "행위규제", "품질·안전규제", "사회규제", "지원·육성", "복합"],
                    "description": "규제 유형",
                },
                "key_provisions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "주요 규제 조항 (3~5개)",
                },
            },
            "required": ["purpose", "regulation_type", "key_provisions"],
        },

        # II. 규제 필요성
        "regulation_necessity": {
            "type": "object",
            "properties": {
                "background": {"type": "string", "description": "규제 도입 배경 및 현황"},
                "necessity_level": {
                    "type": "string",
                    "enum": ["높음", "중간", "낮음"],
                    "description": "규제 필요성 수준",
                },
                "necessity_rationale": {"type": "string", "description": "필요성 판단 근거"},
            },
            "required": ["background", "necessity_level", "necessity_rationale"],
        },

        # III. 규제 영향 분석
        "impact_analysis": {
            "type": "object",
            "properties": {
                "affected_entities": {
                    "type": "string",
                    "description": "적용 대상 및 영향 범위 (업종, 규모 등)",
                },
                "estimated_entity_count": {
                    "type": "string",
                    "description": "영향 받는 사업체 수 추정 (예: 약 10만개 소상공인)",
                },
                "direct_cost": {
                    "type": "string",
                    "description": "직접 순응 비용 (초기 투자, 인허가 비용 등)",
                },
                "administrative_burden": {
                    "type": "string",
                    "description": "행정 부담 (서류, 신고, 점검 등)",
                },
                "annual_ongoing_cost": {
                    "type": "string",
                    "description": "연간 지속 비용 추정 (업체당)",
                },
                "public_benefits": {
                    "type": "string",
                    "description": "규제로 인한 사회적 편익",
                },
                "cost_benefit_summary": {
                    "type": "string",
                    "description": "비용-편익 종합 평가 (1~2문장)",
                },
            },
            "required": [
                "affected_entities",
                "direct_cost",
                "administrative_burden",
                "annual_ongoing_cost",
                "public_benefits",
                "cost_benefit_summary",
            ],
        },

        # IV. 중소기업 영향 분석
        "sme_impact": {
            "type": "object",
            "properties": {
                "impact_level": {
                    "type": "string",
                    "enum": ["높음", "중간", "낮음"],
                    "description": "중소기업에 대한 전반적 영향 수준",
                },
                "impact_summary": {
                    "type": "string",
                    "description": "중소기업 영향 핵심 요약 (2~3문장)",
                },
                "affected_sme_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "영향 받는 중소기업·소상공인 유형",
                },
                "burden_details": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "부담 유형 (비용/행정/기술 등)"},
                            "description": {"type": "string", "description": "구체적 부담 내용"},
                            "severity": {"type": "string", "enum": ["높음", "중간", "낮음"]},
                        },
                        "required": ["category", "description", "severity"],
                    },
                    "description": "세부 부담 항목",
                },
                "opportunity_factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "중소기업 기회·지원 요인",
                },
                "mitigation_measures": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "중소기업 부담 경감을 위한 제안 방안",
                },
            },
            "required": [
                "impact_level",
                "impact_summary",
                "affected_sme_types",
                "burden_details",
                "mitigation_measures",
            ],
        },

        # V. 대안 검토
        "alternatives": {
            "type": "object",
            "properties": {
                "reviewed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "검토된 규제 대안 (3개 내외)",
                },
                "recommended": {
                    "type": "string",
                    "description": "권고 대안 및 사유",
                },
            },
            "required": ["reviewed", "recommended"],
        },

        # VI. 정책 권고사항
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "enum": ["정부", "국회", "중소기업"],
                    },
                    "action": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["즉시", "단기(1년 내)", "중기(3년 내)"],
                    },
                },
                "required": ["target", "action", "priority"],
            },
            "description": "정책 권고사항 (우선순위 포함)",
        },

        # VII. 종합 의견
        "overall_opinion": {
            "type": "string",
            "description": "규제 타당성 및 중소기업 영향에 대한 종합 의견 (3~5문장)",
        },

        "analysis_confidence": {
            "type": "string",
            "enum": ["높음", "중간", "낮음"],
            "description": "법안 원문 미열람 등 분석 한계를 고려한 신뢰도",
        },
        "limitations": {
            "type": "string",
            "description": "분석 한계 및 추가 검토 필요 사항",
        },
    },
    "required": [
        "regulation_overview",
        "regulation_necessity",
        "impact_analysis",
        "sme_impact",
        "alternatives",
        "recommendations",
        "overall_opinion",
        "analysis_confidence",
        "limitations",
    ],
}

ASSESSMENT_SYSTEM = """당신은 대한민국 정부의 규제영향평가 전문 심사관입니다.
의원발의 법률안에 대해 「행정규제기본법」 제7조 및 중소기업기본법에 근거한
공식 규제영향평가서를 작성합니다.

작성 원칙:
1. 법안명, 소관위원회, 발의자, 처리현황 등 가용 정보를 최대한 활용합니다.
2. 한국의 중소기업 규모 기준(중소기업기본법)과 산업 특성을 반영합니다.
3. 비용·편익 추정은 유사 규제 사례를 참조하여 구체적 수치로 제시합니다.
4. 법안 원문 미입수 시 한계를 명시하되, 가용 정보로 최대한 충실히 작성합니다.
5. 중소기업 부담과 기회 요인을 균형있게 분석합니다.

반드시 유효한 JSON만 반환하십시오. 마크다운 블록 없이 JSON 객체만 출력하십시오."""


# ─── 데이터 클래스 ────────────────────────────────────────────

@dataclass
class ScreeningResult:
    """Phase 1 스크리닝 결과"""
    bill: Bill
    is_sme_relevant: bool = False
    confidence: str = "낮음"
    reason: str = ""
    impact_preview: str = ""
    error: str = ""


@dataclass
class ImpactAssessment:
    """Phase 2 규제영향평가서"""
    bill: Bill
    screening: ScreeningResult = field(default_factory=lambda: ScreeningResult(bill=None))  # type: ignore

    # I. 규제 개요
    regulation_overview: dict[str, Any] = field(default_factory=dict)
    # II. 규제 필요성
    regulation_necessity: dict[str, Any] = field(default_factory=dict)
    # III. 규제 영향 분석
    impact_analysis: dict[str, Any] = field(default_factory=dict)
    # IV. 중소기업 영향 분석
    sme_impact: dict[str, Any] = field(default_factory=dict)
    # V. 대안 검토
    alternatives: dict[str, Any] = field(default_factory=dict)
    # VI. 정책 권고사항
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    # VII. 종합 의견
    overall_opinion: str = ""
    analysis_confidence: str = "낮음"
    limitations: str = ""

    error: str = ""

    @property
    def impact_level(self) -> str:
        return self.sme_impact.get("impact_level", "—")

    @property
    def impact_summary(self) -> str:
        return self.sme_impact.get("impact_summary", "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "bill": {
                "bill_id": self.bill.bill_id,
                "bill_no": self.bill.bill_no,
                "bill_name": self.bill.bill_name,
                "committee": self.bill.committee,
                "propose_dt": self.bill.propose_dt,
                "proc_result": self.bill.proc_result,
                "age": self.bill.age,
                "detail_link": self.bill.detail_link,
                "proposer": self.bill.proposer,
                "rst_proposer": self.bill.rst_proposer,
            },
            "screening": {
                "is_sme_relevant": self.screening.is_sme_relevant,
                "confidence": self.screening.confidence,
                "reason": self.screening.reason,
                "impact_preview": self.screening.impact_preview,
            },
            "assessment": {
                "regulation_overview": self.regulation_overview,
                "regulation_necessity": self.regulation_necessity,
                "impact_analysis": self.impact_analysis,
                "sme_impact": self.sme_impact,
                "alternatives": self.alternatives,
                "recommendations": self.recommendations,
                "overall_opinion": self.overall_opinion,
                "analysis_confidence": self.analysis_confidence,
                "limitations": self.limitations,
            },
            "error": self.error,
        }


# ─── 분석기 ──────────────────────────────────────────────────

class SMEAnalyzer:
    """
    중소기업 규제영향 분석기 v2

    Phase 1: AI 스크리닝 — 중소기업 영향 여부 직접 판단
    Phase 2: 규제영향평가서 — 영향 있는 법안에 대한 심층 평가
    """

    # ── 공통 ──────────────────────────────────────────────────

    @staticmethod
    def _run_claude(prompt: str, system: str) -> str:
        """독립 스레드 + 이벤트 루프에서 Claude Agent SDK 호출"""
        async def _call() -> str:
            result_text = ""
            async for msg in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    system_prompt=system,
                    max_turns=1,
                ),
            ):
                if isinstance(msg, ResultMessage):
                    result_text = msg.result or ""
            return result_text

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_call())
        finally:
            loop.close()

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        """Claude 응답에서 JSON 객체 추출 (```json ... ``` 블록 처리)"""
        cleaned = (raw or "").strip()
        if cleaned.startswith("```"):
            lines = [l for l in cleaned.split("\n") if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()
        return json.loads(cleaned)

    def _build_bill_info(self, bill: Bill) -> str:
        proc = bill.proc_result or "계류 중"
        co = f"\n- 공동발의자: {bill.co_proposer}" if bill.co_proposer else ""
        link = f"\n- 원문 링크: {bill.detail_link}" if bill.detail_link else ""
        return (
            f"- 법안번호: {bill.bill_no}\n"
            f"- 법안명: {bill.bill_name}\n"
            f"- 소관위원회: {bill.committee}\n"
            f"- 발의일: {bill.propose_dt}\n"
            f"- 대표발의자: {bill.rst_proposer}\n"
            f"- 처리결과: {proc}"
            f"{co}{link}"
        )

    # ── Phase 1: 스크리닝 ─────────────────────────────────────

    def _build_screening_prompt(self, bill: Bill) -> str:
        return f"""다음 의원발의 법률안이 중소기업·소상공인·스타트업·벤처기업에
영향을 미치는지 판단하십시오.

## 법안 정보
{self._build_bill_info(bill)}

## 판단 요청
위 법안의 중소기업 영향 여부를 아래 JSON 스키마에 맞게 판단하십시오.

JSON 스키마:
{json.dumps(SCREENING_SCHEMA, ensure_ascii=False, indent=2)}

반드시 유효한 JSON만 반환하십시오."""

    def screen_bill(self, bill: Bill, verbose: bool = False) -> ScreeningResult:
        """단일 법안 스크리닝 (Phase 1)"""
        result = ScreeningResult(bill=bill)
        try:
            if verbose:
                print(f"  [스크리닝] {bill.bill_name[:45]}...", end=" ", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                raw = pool.submit(
                    self._run_claude,
                    self._build_screening_prompt(bill),
                    SCREENING_SYSTEM,
                ).result(timeout=60)
            data = self._extract_json(raw)
            result.is_sme_relevant = bool(data.get("is_sme_relevant", False))
            result.confidence = data.get("confidence", "낮음")
            result.reason = data.get("reason", "")
            result.impact_preview = data.get("impact_preview", "")
            if verbose:
                mark = "✅ 영향있음" if result.is_sme_relevant else "➖ 해당없음"
                print(f"{mark} ({result.confidence})")
        except Exception as exc:
            result.error = str(exc)
            if verbose:
                print(f"⚠️ 오류: {exc}")
        return result

    # ── Phase 2: 규제영향평가서 ───────────────────────────────

    def _build_assessment_prompt(self, bill: Bill, screening: ScreeningResult) -> str:
        return f"""다음 의원발의 법률안에 대해 중소기업 규제영향평가서를 작성하십시오.

## 법안 정보
{self._build_bill_info(bill)}

## 스크리닝 결과
- 중소기업 영향: {'있음' if screening.is_sme_relevant else '없음'}
- 영향 방향: {screening.impact_preview or '미상'}
- 스크리닝 근거: {screening.reason}

## 작성 요청
아래 JSON 스키마에 따라 공식 규제영향평가서를 작성하십시오.
법안 원문을 직접 열람할 수 없으므로, 법안명과 소관위원회 등 가용 정보를 바탕으로
합리적으로 추론하여 작성하되, 한계는 limitations에 명시하십시오.

JSON 스키마:
{json.dumps(ASSESSMENT_SCHEMA, ensure_ascii=False, indent=2)}

반드시 유효한 JSON만 반환하십시오."""

    def assess_bill(
        self,
        bill: Bill,
        screening: ScreeningResult,
        verbose: bool = False,
    ) -> ImpactAssessment:
        """단일 법안 규제영향평가서 작성 (Phase 2)"""
        result = ImpactAssessment(bill=bill, screening=screening)
        try:
            if verbose:
                print(f"  [평가서] {bill.bill_name[:45]}...", end=" ", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                raw = pool.submit(
                    self._run_claude,
                    self._build_assessment_prompt(bill, screening),
                    ASSESSMENT_SYSTEM,
                ).result(timeout=120)
            data = self._extract_json(raw)
            result.regulation_overview = data.get("regulation_overview", {})
            result.regulation_necessity = data.get("regulation_necessity", {})
            result.impact_analysis = data.get("impact_analysis", {})
            result.sme_impact = data.get("sme_impact", {})
            result.alternatives = data.get("alternatives", {})
            result.recommendations = data.get("recommendations", [])
            result.overall_opinion = data.get("overall_opinion", "")
            result.analysis_confidence = data.get("analysis_confidence", "낮음")
            result.limitations = data.get("limitations", "")
            if verbose:
                lvl = result.impact_level
                print(f"완료 (영향: {lvl})")
        except Exception as exc:
            result.error = str(exc)
            if verbose:
                print(f"⚠️ 오류: {exc}")
        return result

    # ── 통합 실행 ──────────────────────────────────────────────

    def analyze_bills(
        self,
        bills: list[Bill],
        verbose: bool = True,
        on_screen: Any = None,
        on_assess: Any = None,
    ) -> tuple[list[ScreeningResult], list[ImpactAssessment]]:
        """
        전체 분석 파이프라인

        Returns
        -------
        (screenings, assessments)
            screenings  : 모든 법안의 스크리닝 결과
            assessments : SME 영향 있는 법안의 규제영향평가서
        """
        total = len(bills)
        screenings: list[ScreeningResult] = []
        assessments: list[ImpactAssessment] = []

        # Phase 1
        if verbose:
            print(f"\n[Phase 1] AI 스크리닝 — {total}건")

        for i, bill in enumerate(bills, 1):
            if verbose:
                print(f"  ({i}/{total})", end=" ")
            sr = self.screen_bill(bill, verbose=verbose)
            screenings.append(sr)
            if on_screen:
                on_screen(i, total, sr)

        relevant = [sr for sr in screenings if sr.is_sme_relevant and not sr.error]
        if verbose:
            print(f"\n  → 영향 있음: {len(relevant)}건 / 전체 {total}건")

        # Phase 2
        if verbose:
            print(f"\n[Phase 2] 규제영향평가서 작성 — {len(relevant)}건")

        for i, sr in enumerate(relevant, 1):
            if verbose:
                print(f"  ({i}/{len(relevant)})", end=" ")
            assessment = self.assess_bill(sr.bill, sr, verbose=verbose)
            assessments.append(assessment)
            if on_assess:
                on_assess(i, len(relevant), assessment)

        return screenings, assessments
