"""
국회의안정보시스템 OpenAPI 클라이언트

국회 열린국회정보 포털(open.assembly.go.kr)의 의원발의 법률안 API를
사용해 법안 목록을 수집하고 SME 관련 법안을 필터링합니다.

API 문서: https://open.assembly.go.kr/portal/openapi
서비스코드: nzmimeepazxkubdpn (국회의원 발의법률안)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests

from config import (
    ASSEMBLY_API_KEY,
    ASSEMBLY_BASE_URL,
    BILL_SERVICE_CODE,
    DEFAULT_AGE,
    PAGE_SIZE,
    SME_KEYWORDS,
)


@dataclass
class Bill:
    """의원발의 법률안 데이터 클래스"""

    bill_id: str
    bill_no: str
    bill_name: str
    committee: str
    propose_dt: str
    proc_result: str
    age: str
    detail_link: str
    proposer: str
    rst_proposer: str
    co_proposer: str
    committee_id: str

    # 원본 JSON (디버그용)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Bill":
        return cls(
            bill_id=row.get("BILL_ID", ""),
            bill_no=row.get("BILL_NO", ""),
            bill_name=row.get("BILL_NAME", ""),
            committee=row.get("COMMITTEE", ""),
            propose_dt=row.get("PROPOSE_DT", ""),
            proc_result=row.get("PROC_RESULT", ""),
            age=row.get("AGE", ""),
            detail_link=row.get("DETAIL_LINK", ""),
            proposer=row.get("PROPOSER", ""),
            rst_proposer=row.get("RST_PROPOSER", ""),
            co_proposer=row.get("CO_PROPOSER", ""),
            committee_id=row.get("COMMITTEE_ID", ""),
            raw=row,
        )

    def is_sme_related(self, extra_keywords: list[str] | None = None) -> bool:
        """법안 제목·소관위원회에 SME 키워드 포함 여부 확인"""
        keywords = SME_KEYWORDS + (extra_keywords or [])
        search_text = f"{self.bill_name} {self.committee}".upper()
        return any(kw in search_text for kw in keywords)

    def summary(self) -> str:
        return (
            f"[{self.bill_no}] {self.bill_name}\n"
            f"  발의자: {self.rst_proposer}  |  소관위: {self.committee}\n"
            f"  발의일: {self.propose_dt}  |  처리결과: {self.proc_result or '계류중'}"
        )


class AssemblyAPIError(Exception):
    """국회 OpenAPI 호출 오류"""


class AssemblyClient:
    """
    국회 열린국회정보 OpenAPI 클라이언트

    Parameters
    ----------
    api_key : str
        인증키 (open.assembly.go.kr에서 발급)
    timeout : int
        HTTP 요청 타임아웃 (초)
    """

    def __init__(self, api_key: str = "", timeout: int = 30) -> None:
        self.api_key = api_key or ASSEMBLY_API_KEY
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # ─── 내부 메서드 ──────────────────────────────────────────

    def _get(self, service_code: str, params: dict[str, Any]) -> dict[str, Any]:
        """OpenAPI GET 요청 공통 처리"""
        url = f"{ASSEMBLY_BASE_URL}/{service_code}"
        base_params = {
            "KEY": self.api_key,
            "Type": "json",
            **params,
        }
        try:
            resp = self._session.get(url, params=base_params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise AssemblyAPIError(f"HTTP 요청 실패: {exc}") from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise AssemblyAPIError(f"JSON 파싱 실패: {exc}") from exc

        return data

    def _parse_bill_response(
        self, data: dict[str, Any]
    ) -> tuple[int, list[dict[str, Any]]]:
        """
        의원발의 법률안 API 응답 파싱

        Returns
        -------
        (total_count, rows)
        """
        outer = data.get(BILL_SERVICE_CODE)
        if not outer or not isinstance(outer, list):
            raise AssemblyAPIError(f"예상치 못한 응답 구조: {list(data.keys())}")

        # 첫 번째 요소: head (메타 정보)
        head_section = outer[0].get("head", [])
        result_info = {}
        total_count = 0
        for item in head_section:
            if "list_total_count" in item:
                total_count = int(item["list_total_count"])
            if "RESULT" in item:
                result_info = item["RESULT"]

        code = result_info.get("CODE", "")
        if code not in ("INFO-000", "INFO-200"):
            msg = result_info.get("MESSAGE", "알 수 없는 오류")
            raise AssemblyAPIError(f"API 오류 [{code}]: {msg}")

        # 두 번째 요소: row (데이터)
        rows: list[dict[str, Any]] = []
        if len(outer) > 1:
            rows = outer[1].get("row", [])

        return total_count, rows

    # ─── 공개 메서드 ──────────────────────────────────────────

    def fetch_bills(
        self,
        age: int = DEFAULT_AGE,
        page: int = 1,
        page_size: int = PAGE_SIZE,
        bill_name: str = "",
        proc_result: str = "",
    ) -> tuple[int, list[Bill]]:
        """
        의원발의 법률안 목록 조회

        Parameters
        ----------
        age : int
            국회 대수 (예: 22)
        page : int
            페이지 번호 (1부터 시작)
        page_size : int
            페이지당 결과 수 (최대 100)
        bill_name : str
            법안명 검색어 (선택)
        proc_result : str
            처리결과 필터 (선택, 예: "원안가결", "수정가결")

        Returns
        -------
        (total_count, bills)
        """
        params: dict[str, Any] = {
            "pIndex": page,
            "pSize": page_size,
            "AGE": age,
        }
        if bill_name:
            params["BILL_NAME"] = bill_name
        if proc_result:
            params["PROC_RESULT"] = proc_result

        data = self._get(BILL_SERVICE_CODE, params)
        total_count, rows = self._parse_bill_response(data)
        bills = [Bill.from_row(row) for row in rows]
        return total_count, bills

    def fetch_all_bills(
        self,
        age: int = DEFAULT_AGE,
        max_bills: int | None = None,
        delay: float = 0.3,
        verbose: bool = False,
    ) -> list[Bill]:
        """
        전체 의원발의 법률안 수집 (페이지네이션 자동 처리)

        Parameters
        ----------
        age : int
            국회 대수
        max_bills : int | None
            수집할 최대 법안 수 (None이면 전체)
        delay : float
            페이지 간 API 호출 지연 시간(초) - 서버 부하 방지
        verbose : bool
            진행 상황 출력 여부
        """
        all_bills: list[Bill] = []
        page = 1

        while True:
            if verbose:
                print(f"  페이지 {page} 조회 중...", end=" ", flush=True)

            total, bills = self.fetch_bills(age=age, page=page, page_size=PAGE_SIZE)

            if verbose:
                print(f"({len(bills)}건 수신, 전체 {total}건)")

            all_bills.extend(bills)

            if max_bills and len(all_bills) >= max_bills:
                all_bills = all_bills[:max_bills]
                break

            if len(all_bills) >= total or not bills:
                break

            page += 1
            time.sleep(delay)

        return all_bills

    def fetch_sme_related_bills(
        self,
        age: int = DEFAULT_AGE,
        max_bills: int | None = None,
        extra_keywords: list[str] | None = None,
        verbose: bool = False,
    ) -> list[Bill]:
        """
        중소기업 관련 의원발의 법률안 필터링 수집

        Parameters
        ----------
        age : int
            국회 대수
        max_bills : int | None
            반환할 최대 SME 관련 법안 수
        extra_keywords : list[str] | None
            추가 SME 키워드
        verbose : bool
            진행 상황 출력 여부
        """
        if verbose:
            print(f"\n[국회 OpenAPI] {age}대 의원발의 법률안 수집 시작...")

        # 전체 수집 후 필터링 (API가 키워드 검색을 정확히 지원하지 않으므로)
        fetch_limit = (max_bills * 10) if max_bills else None
        all_bills = self.fetch_all_bills(
            age=age, max_bills=fetch_limit, verbose=verbose
        )

        if verbose:
            print(f"  전체 {len(all_bills)}건 수집 완료. SME 관련 필터링 중...")

        sme_bills = [b for b in all_bills if b.is_sme_related(extra_keywords)]

        if verbose:
            print(f"  SME 관련 법안 {len(sme_bills)}건 발견.")

        if max_bills:
            sme_bills = sme_bills[:max_bills]

        return sme_bills
