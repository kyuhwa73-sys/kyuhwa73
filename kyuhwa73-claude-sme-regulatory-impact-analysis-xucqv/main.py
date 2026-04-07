"""
중소기업 규제영향 분석 시스템 — 메인 진입점

국회의안정보시스템 OpenAPI로 의원발의 법률안을 수집하고
Claude AI를 통해 중소기업 규제영향을 분석합니다.

사용법:
  python main.py                         # 기본 실행 (22대 국회, 최대 20건)
  python main.py --age 22 --max 30       # 30건 분석
  python main.py --keywords 플랫폼 전자상거래  # 추가 키워드 지정
  python main.py --format html           # HTML 보고서만 생성
  python main.py --output-dir ./reports  # 출력 디렉터리 지정
  python main.py --dry-run               # API 수집 없이 샘플 데이터로 테스트
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import click

from assembly_client import AssemblyClient, AssemblyAPIError, Bill
from config import (
    ASSEMBLY_API_KEY,
    DEFAULT_AGE,
    DEFAULT_MAX_BILLS,
)
from sme_analyzer import SMEAnalyzer
from report_generator import (
    generate_json_report,
    generate_html_report,
    print_summary,
)


# ─── 샘플 데이터 (--dry-run 전용) ────────────────────────────

SAMPLE_BILLS: list[Bill] = [
    Bill(
        bill_id="PRC_S2Z2D1R2P3X1U1Y2W3O3Q0L1R1L1",
        bill_no="2200001",
        bill_name="중소기업 디지털 전환 지원에 관한 법률안",
        committee="중소벤처기업위원회",
        propose_dt="2024-03-15",
        proc_result="",
        age="22",
        detail_link="",
        proposer="홍길동의원 등 10인",
        rst_proposer="홍길동",
        co_proposer="김철수 외 9인",
        committee_id="9700178",
    ),
    Bill(
        bill_id="PRC_T3A3E2S3Q4Y2Z2A3X4P4R2S2M2",
        bill_no="2200002",
        bill_name="소상공인 보호 및 지원에 관한 법률 일부개정법률안",
        committee="중소벤처기업위원회",
        propose_dt="2024-04-01",
        proc_result="",
        age="22",
        detail_link="",
        proposer="박영희의원 등 15인",
        rst_proposer="박영희",
        co_proposer="이영수 외 14인",
        committee_id="9700178",
    ),
    Bill(
        bill_id="PRC_U4B4F3T4R5Z3A3B4Y5Q5S3T3N3",
        bill_no="2200003",
        bill_name="플랫폼 공정경쟁 및 중소 입점업체 보호에 관한 법률안",
        committee="정무위원회",
        propose_dt="2024-05-10",
        proc_result="",
        age="22",
        detail_link="",
        proposer="이민준의원 등 20인",
        rst_proposer="이민준",
        co_proposer="최지원 외 19인",
        committee_id="9700043",
    ),
]


# ─── CLI ─────────────────────────────────────────────────────

@click.command()
@click.option(
    "--age", "-a",
    default=DEFAULT_AGE,
    show_default=True,
    help="국회 대수 (예: 22)",
    type=int,
)
@click.option(
    "--max", "-m", "max_bills",
    default=DEFAULT_MAX_BILLS,
    show_default=True,
    help="분석할 최대 법안 수",
    type=int,
)
@click.option(
    "--keywords", "-k",
    multiple=True,
    help="추가 SME 관련 키워드 (반복 사용 가능, 예: --keywords 플랫폼 --keywords 전자상거래)",
)
@click.option(
    "--format", "-f", "output_format",
    type=click.Choice(["all", "json", "html"], case_sensitive=False),
    default="all",
    show_default=True,
    help="출력 형식",
)
@click.option(
    "--output-dir", "-o",
    default="./output",
    show_default=True,
    help="보고서 출력 디렉터리",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="국회 API 대신 샘플 데이터로 테스트 실행",
)
@click.option(
    "--no-filter",
    is_flag=True,
    default=False,
    help="SME 키워드 필터 없이 전체 법안 분석",
)
def main(
    age: int,
    max_bills: int,
    keywords: tuple[str, ...],
    output_format: str,
    output_dir: str,
    dry_run: bool,
    no_filter: bool,
) -> None:
    """
    \b
    국회의안정보시스템 의원발의 법률안 수집 및
    중소기업 규제영향 분석 시스템

    환경변수:
      ASSEMBLY_API_KEY   국회 OpenAPI 인증키 (필수)

    Claude 분석은 현재 로그인된 Claude Code 계정을 사용합니다.
    """
    click.echo("=" * 60)
    click.echo("중소기업 규제영향 분석 시스템")
    click.echo("=" * 60)

    # ── 사전 검증 ─────────────────────────────────────────────
    if not dry_run and not ASSEMBLY_API_KEY:
        click.secho(
            "[오류] ASSEMBLY_API_KEY가 설정되지 않았습니다.\n"
            "  .env 파일에 ASSEMBLY_API_KEY=<인증키>를 추가하거나\n"
            "  환경변수로 설정하십시오.\n"
            "  (--dry-run 옵션으로 샘플 데이터 테스트 가능)",
            fg="red",
        )
        sys.exit(1)

    # ── 출력 디렉터리 생성 ─────────────────────────────────────
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── 법안 수집 ─────────────────────────────────────────────
    extra_kws = list(keywords)

    if dry_run:
        click.echo("\n[모드] --dry-run: 샘플 데이터 사용")
        bills = SAMPLE_BILLS[:max_bills]
    else:
        click.echo(f"\n[1단계] {age}대 국회 의원발의 법률안 수집")
        client = AssemblyClient()
        try:
            if no_filter:
                bills = client.fetch_all_bills(
                    age=age, max_bills=max_bills, verbose=True
                )
            else:
                bills = client.fetch_sme_related_bills(
                    age=age,
                    max_bills=max_bills,
                    extra_keywords=extra_kws,
                    verbose=True,
                )
        except AssemblyAPIError as exc:
            click.secho(f"[오류] 국회 API 수집 실패: {exc}", fg="red")
            sys.exit(1)

    if not bills:
        click.secho("[경고] 분석할 법안이 없습니다.", fg="yellow")
        sys.exit(0)

    click.echo(f"\n  ✓ 분석 대상 법안: {len(bills)}건")

    # ── Claude 분석 ───────────────────────────────────────────
    click.echo("\n[2단계] Claude (현재 계정) 규제영향 분석")
    click.echo("  (법안 당 약 15~30초 소요)\n")

    analyzer = SMEAnalyzer()
    results = analyzer.analyze_bills(bills, verbose=True)

    # ── 보고서 생성 ───────────────────────────────────────────
    click.echo(f"\n[3단계] 보고서 생성 ({output_format})")

    json_path = os.path.join(output_dir, f"sme_impact_{timestamp}.json")
    html_path = os.path.join(output_dir, f"sme_impact_{timestamp}.html")

    if output_format in ("all", "json"):
        generate_json_report(results, age=age, output_path=json_path)
        click.echo(f"  ✓ JSON: {json_path}")

    if output_format in ("all", "html"):
        generate_html_report(results, age=age, output_path=html_path)
        click.echo(f"  ✓ HTML: {html_path}")

    # ── 콘솔 요약 ─────────────────────────────────────────────
    print_summary(results)


if __name__ == "__main__":
    main()
