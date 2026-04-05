"""
중소기업 규제영향 분석기 (Claude Agent SDK 기반)

별도 API 키 없이 현재 로그인된 Claude Code 계정으로
의원발의 법률안의 중소기업 규제영향을 심층 분석합니다.

분석 항목:
  - 규제 영향 강도 (HIGH / MEDIUM / LOW / NONE)
  - 영향 받는 중소기업 유형
  - 주요 규제 조항 요약
  - 준수 비용 추정
  - 위험 요인 및 기회 요인
  - 정책 권고사항
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

from assembly_client import Bill
from config import IMPACT_CATEGORIES

# ─── 분석 결과 JSON 스키마 ────────────────────────────────────

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "impact_level": {
            "type": "string",
            "enum": ["HIGH", "MEDIUM", "LOW", "NONE"],
            "description": "중소기업에 대한 규제 영향 강도",
        },
        "impact_summary": {
            "type": "string",
            "description": "규제 영향의 핵심 요약 (2-3문장)",
        },
        "affected_sme_types": {
            "type": "array",
            "items": {"type": "string"},
            "description": "영향 받는 중소기업·소상공인 유형 목록",
        },
        "key_provisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "provision": {"type": "string", "description": "조항 내용"},
                    "impact": {"type": "string", "description": "중소기업 영향"},
                    "burden_level": {
                        "type": "string",
                        "enum": ["높음", "중간", "낮음"],
                    },
                },
                "required": ["provision", "impact", "burden_level"],
            },
            "description": "주요 규제 조항별 분석",
        },
        "compliance_cost": {
            "type": "object",
            "properties": {
                "initial_cost": {
                    "type": "string",
                    "description": "초기 이행 비용 추정 (예: 소규모 사업체 기준 약 500만원)",
                },
                "ongoing_cost": {
                    "type": "string",
                    "description": "지속적 준수 비용 추정 (연간)",
                },
                "cost_notes": {"type": "string", "description": "비용 산정 근거 및 주의사항"},
            },
            "required": ["initial_cost", "ongoing_cost", "cost_notes"],
        },
        "risk_factors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "중소기업 위험 요인",
        },
        "opportunity_factors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "중소기업 기회 요인 (규제 완화·지원 등)",
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "enum": ["정부", "국회", "중소기업"],
                        "description": "권고 대상",
                    },
                    "action": {"type": "string", "description": "권고 조치"},
                },
                "required": ["target", "action"],
            },
            "description": "정책 권고사항",
        },
        "analysis_confidence": {
            "type": "string",
            "enum": ["높음", "중간", "낮음"],
            "description": "법안 정보 불충분 시 분석 신뢰도",
        },
        "limitations": {
            "type": "string",
            "description": "분석 한계 및 주의사항 (법안 원문 미입수 시 명시)",
        },
    },
    "required": [
        "impact_level",
        "impact_summary",
        "affected_sme_types",
        "key_provisions",
        "compliance_cost",
        "risk_factors",
        "opportunity_factors",
        "recommendations",
        "analysis_confidence",
        "limitations",
    ],
}

SYSTEM_PROMPT = """당신은 중소기업 규제영향 분석 전문가입니다.
국회에서 발의된 법률안이 중소기업, 소상공인, 스타트업, 벤처기업에 미치는
규제 영향을 심층적으로 분석합니다.

분석 원칙:
1. 법안 제목, 소관위원회, 발의자, 처리현황 등 가용 정보를 최대한 활용합니다.
2. 한국 중소기업 정책 및 규제 체계(중소기업기본법, 소상공인보호법 등)에 근거합니다.
3. 실질적인 준수 비용과 행정 부담을 구체적으로 추정합니다.
4. 불확실한 부분은 명확히 표시하고 신뢰도를 평가합니다.
5. 규제 부담뿐 아니라 지원·기회 요인도 균형있게 분석합니다.

반드시 유효한 JSON만 반환하십시오. 설명 텍스트나 마크다운 블록 없이 JSON 객체만 출력하십시오."""


# ─── 데이터 클래스 ────────────────────────────────────────────

@dataclass
class AnalysisResult:
    """법안별 규제영향 분석 결과"""

    bill: Bill
    impact_level: str = "NONE"
    impact_summary: str = ""
    affected_sme_types: list[str] = field(default_factory=list)
    key_provisions: list[dict[str, Any]] = field(default_factory=list)
    compliance_cost: dict[str, str] = field(default_factory=dict)
    risk_factors: list[str] = field(default_factory=list)
    opportunity_factors: list[str] = field(default_factory=list)
    recommendations: list[dict[str, str]] = field(default_factory=list)
    analysis_confidence: str = "낮음"
    limitations: str = ""
    error: str = ""

    @property
    def impact_label(self) -> str:
        return IMPACT_CATEGORIES.get(self.impact_level, self.impact_level)

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
            "analysis": {
                "impact_level": self.impact_level,
                "impact_label": self.impact_label,
                "impact_summary": self.impact_summary,
                "affected_sme_types": self.affected_sme_types,
                "key_provisions": self.key_provisions,
                "compliance_cost": self.compliance_cost,
                "risk_factors": self.risk_factors,
                "opportunity_factors": self.opportunity_factors,
                "recommendations": self.recommendations,
                "analysis_confidence": self.analysis_confidence,
                "limitations": self.limitations,
            },
            "error": self.error,
        }


# ─── 분석기 ──────────────────────────────────────────────────

class SMEAnalyzer:
    """
    중소기업 규제영향 분석기

    Claude Agent SDK를 사용해 현재 로그인된 Claude Code 계정으로
    분석을 수행합니다. 별도 API 키가 필요하지 않습니다.
    """

    def _build_prompt(self, bill: Bill) -> str:
        detail_url = (
            f"\n  원문 링크: {bill.detail_link}" if bill.detail_link else ""
        )
        co_info = f"\n  공동발의자: {bill.co_proposer}" if bill.co_proposer else ""
        proc = bill.proc_result or "계류 중"

        return f"""다음 의원발의 법률안의 중소기업 규제영향을 분석하십시오.

## 법안 정보
- 법안번호: {bill.bill_no}
- 법안명: {bill.bill_name}
- 소관위원회: {bill.committee}
- 발의일: {bill.propose_dt}
- 대표발의자: {bill.rst_proposer}
- 처리결과: {proc}{co_info}{detail_url}

## 분석 요청
위 법안이 중소기업, 소상공인, 스타트업, 벤처기업에 미치는 규제 영향을
아래 JSON 스키마에 맞게 분석하십시오.

법안 원문을 직접 확인할 수 없는 경우, 법안명·소관위원회·발의 맥락을 기반으로
합리적으로 추론하되 analysis_confidence와 limitations에 반드시 명시하십시오.

JSON 스키마:
{json.dumps(ANALYSIS_SCHEMA, ensure_ascii=False, indent=2)}

반드시 유효한 JSON만 반환하십시오. 다른 설명 텍스트는 포함하지 마십시오."""

    async def _analyze_async(self, bill: Bill) -> str:
        """비동기 방식으로 Claude Agent SDK 호출"""
        result_text = ""
        async for message in query(
            prompt=self._build_prompt(bill),
            options=ClaudeAgentOptions(
                system_prompt=SYSTEM_PROMPT,
                max_turns=1,          # 단일 응답으로 충분
            ),
        ):
            if isinstance(message, ResultMessage):
                result_text = message.result or ""
        return result_text

    def analyze_bill(self, bill: Bill, verbose: bool = False) -> AnalysisResult:
        """단일 법안 규제영향 분석"""
        result = AnalysisResult(bill=bill)

        try:
            if verbose:
                print(f"  분석 중: {bill.bill_name[:50]}...", end=" ", flush=True)

            raw_text = anyio.run(self._analyze_async, bill)

            if verbose:
                print("완료")

            # JSON 파싱 (```json ... ``` 블록 처리 포함)
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                lines = [l for l in cleaned.split("\n") if not l.strip().startswith("```")]
                cleaned = "\n".join(lines)

            analysis_data = json.loads(cleaned)
            _populate_result(result, analysis_data)

        except json.JSONDecodeError as exc:
            result.error = f"JSON 파싱 오류: {exc}\n원문: {raw_text[:200]}"
            result.limitations = "분석 응답을 파싱하는 데 실패했습니다."
        except Exception as exc:
            result.error = f"분석 오류: {exc}"

        return result

    def analyze_bills(
        self,
        bills: list[Bill],
        verbose: bool = True,
    ) -> list[AnalysisResult]:
        """다수 법안 순차 분석"""
        results: list[AnalysisResult] = []
        total = len(bills)

        for i, bill in enumerate(bills, 1):
            if verbose:
                print(f"\n[{i}/{total}] {bill.bill_name}")

            result = self.analyze_bill(bill, verbose=verbose)

            if result.error:
                if verbose:
                    print(f"  오류: {result.error}")
            else:
                if verbose:
                    print(
                        f"  규제영향: {result.impact_label}  |  "
                        f"신뢰도: {result.analysis_confidence}"
                    )

            results.append(result)

        return results


def _populate_result(result: AnalysisResult, data: dict[str, Any]) -> None:
    """파싱된 JSON으로 AnalysisResult 채우기"""
    result.impact_level = data.get("impact_level", "NONE")
    result.impact_summary = data.get("impact_summary", "")
    result.affected_sme_types = data.get("affected_sme_types", [])
    result.key_provisions = data.get("key_provisions", [])
    result.compliance_cost = data.get("compliance_cost", {})
    result.risk_factors = data.get("risk_factors", [])
    result.opportunity_factors = data.get("opportunity_factors", [])
    result.recommendations = data.get("recommendations", [])
    result.analysis_confidence = data.get("analysis_confidence", "낮음")
    result.limitations = data.get("limitations", "")
