"""
설정 및 상수 정의
- 국회 OpenAPI 엔드포인트
- 중소기업 관련 키워드
- Claude 분석 설정
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── API 설정 ────────────────────────────────────────────────
ASSEMBLY_API_KEY = os.getenv("ASSEMBLY_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 국회 OpenAPI 기본 URL
ASSEMBLY_BASE_URL = "https://open.assembly.go.kr/portal/openapi"

# 의원발의 법률안 서비스 코드
BILL_SERVICE_CODE = "nzmimeepazxkubdpn"

# 현재 국회 대수 (22대)
DEFAULT_AGE = 22

# 페이지당 최대 결과 수
PAGE_SIZE = 100

# Claude 모델
CLAUDE_MODEL = "claude-opus-4-6"

# ─── 중소기업 관련 키워드 ─────────────────────────────────────
# 이 키워드가 법률안 제목·소관위원회에 포함될 경우 SME 관련 법안으로 1차 필터링
SME_KEYWORDS = [
    # 중소기업 직접 관련
    "중소기업", "중소기업기본", "중소벤처", "소상공인", "소기업",
    "벤처기업", "스타트업", "창업", "자영업", "소규모",
    # 규제·부담 관련
    "규제", "부담금", "과징금", "과태료", "인허가", "허가",
    "등록", "신고", "자격", "면허", "감독", "검사",
    # 노동·고용 관련 (중소기업 비용 영향)
    "최저임금", "근로시간", "고용", "산재", "사회보험",
    # 세금·재정 관련
    "세금", "세액", "부가가치세", "법인세", "소득세",
    "공제", "감면", "지원금", "보조금",
    # 거래·계약 관련
    "하도급", "가맹", "대리점", "유통", "납품", "수수료",
    # 환경·안전 관련
    "환경", "안전", "위생", "소방", "건축",
    # 산업·업종 관련
    "제조업", "서비스업", "유통업", "음식점", "도소매",
    # 소관위원회
    "중소벤처기업부",
]

# SME 규제영향 분석 결과 카테고리
IMPACT_CATEGORIES = {
    "HIGH": "높음 (직접적·즉각적 영향)",
    "MEDIUM": "중간 (간접적·단기 영향)",
    "LOW": "낮음 (제한적·장기 영향)",
    "NONE": "해당없음",
}

# 분석 대상 최대 법안 수 (기본값)
DEFAULT_MAX_BILLS = 20
