"""
자연어 질문 파서
질문에서 필터 조건을 추출하는 모듈
"""

import re
from typing import Dict, Any, Optional

class QueryParser:
    """자연어 질문을 분석하여 필터 조건 추출"""
    
    def __init__(self):
        """키워드 매핑 테이블 초기화"""
        # 팀 매핑
        self.team_keywords = {
            '인천': '인천마케팅팀',
            '남부': '남부마케팅팀',
            '강서': '강서마케팅팀',
            '수원': '수원마케팅팀'
        }
    
    def parse(self, question: str) -> Dict[str, Any]:
        """
        자연어 질문을 파싱하여 필터 조건 추출
        
        Args:
            question: 사용자 질문
            
        Returns:
            필터 조건 딕셔너리
        """
        # 소문자 변환
        question_lower = question.lower()
        
        # 기본 필터 (모든 질문에 적용되는 것만)
        filters = {
            'team': self._extract_team(question),
            'min_responses': 5,
            'store_name': self._extract_store_name(question),
            'store_code': self._extract_store_code(question),
            'dealer_code': self._extract_dealer_code(question),
            'dealer_id': self._extract_dealer_id(question),
            'period_start': None,
            'period_end': None,
            'comparison_mode': self._detect_comparison(question),
            'trend': self._detect_trend(question),
            'analysis_type': self._detect_analysis_type(question_lower)
        }
        
        # NPS 목표 및 비교 방향 추출 (NPS 언급이 있을 때만)
        nps_info = self._extract_nps_target(question_lower)
        if nps_info:
            filters['nps_target'] = nps_info['target']
            filters['nps_comparison'] = nps_info['comparison']
        else:
            filters['nps_target'] = None
            filters['nps_comparison'] = None
        
        # 시니어 비중 기준 추출 (시니어 언급이 있을 때만)
        senior_info = self._extract_senior_threshold(question_lower)
        if senior_info:
            filters['senior_threshold'] = senior_info
        else:
            filters['senior_threshold'] = None  # 시니어 언급 없으면 None
        
        # 응답수 추출
        min_resp = self._extract_min_responses(question)
        if min_resp:
            filters['min_responses'] = min_resp
        
        # 비교 기간 추출 (기간별 비교 분석용 - analysis_month 전달)
        analysis_month = filters.get('analysis_month')  # app.py에서 설정된 값
        comparison_periods = self._extract_comparison_periods(question, analysis_month)
        if comparison_periods:
            filters['comparison_periods'] = comparison_periods
        else:
            filters['comparison_periods'] = None
        
        # 단일 기간 추출
        period = self._extract_period(question)
        if period:
            filters['period_start'] = period[0]
            filters['period_end'] = period[1]
        
        return filters
    
    def _extract_team(self, question: str) -> Optional[str]:
        """팀 추출"""
        for keyword, team_name in self.team_keywords.items():
            if keyword in question:
                return team_name
        return None
    
    def _extract_nps_target(self, question: str) -> Optional[dict]:
        """
        NPS 목표값 및 비교 방향 추출
        
        Returns:
            {'target': 87, 'comparison': 'below'} 형태
            NPS 언급이 없으면 None
        """
        # NPS 언급이 있는지 먼저 확인
        if 'nps' not in question:
            return None
        
        # 패턴 1: "NPS 90% 미만"
        pattern1 = re.search(r'nps[^\d]*(\d+)%?[^\d]*(미만|이하|낮은|아래)', question)
        if pattern1:
            return {
                'target': int(pattern1.group(1)),
                'comparison': 'below'
            }
        
        # 패턴 2: "NPS 90% 이상"
        pattern2 = re.search(r'nps[^\d]*(\d+)%?[^\d]*(이상|초과|넘는|넘은|높은|위)', question)
        if pattern2:
            return {
                'target': int(pattern2.group(1)),
                'comparison': 'above'
            }
        
        # 패턴 3: "NPS가 낮은" (숫자 없이)
        if any(keyword in question for keyword in ['낮은', '낮고', '낮으면서', '낮음', '낮아']):
            return {
                'target': 87,  # 기본 목표
                'comparison': 'below'
            }
        elif any(keyword in question for keyword in ['높은', '높고', '높으면서', '높음', '높아']):
            return {
                'target': 87,
                'comparison': 'above'
            }
        
        # NPS 언급만 있고 구체적인 조건이 없으면 None
        return None
    
    def _extract_senior_threshold(self, question: str) -> Optional[str]:
        """
        시니어 비중 기준 추출
        
        Returns:
            'avg' (평균 이상), 'custom:30' (특정값 이상), 'below_avg' (평균 이하)
            시니어 언급이 없으면 None
        """
        # 시니어 언급이 있는지 먼저 확인
        if '시니어' not in question:
            return None
        
        # "시니어 비중 30% 이상"
        pattern = re.search(r'시니어[^\d]*비중[^\d]*(\d+)%?[^\d]*(이상|넘는)', question)
        if pattern:
            return f"custom:{pattern.group(1)}"  # "custom:30" 형태
        
        # "시니어 비중이 높은"
        if any(keyword in question for keyword in ['비중이 높은', '비중 높은', '많은', '높고', '높으면서']):
            return 'avg'  # 평균 이상
        elif any(keyword in question for keyword in ['비중이 낮은', '비중 낮은', '적은', '낮으면서']):
            return 'below_avg'  # 평균 이하
        
        # 시니어 언급만 있고 구체적인 조건이 없으면 평균 기준
        return 'avg'
    
    def _extract_min_responses(self, question: str) -> Optional[int]:
        """최소 응답수 추출"""
        pattern = re.search(r'응답[^\d]*(\d+)건', question)
        if pattern:
            return int(pattern.group(1))
        return 5  # 기본값
    
    def _extract_store_name(self, question: str) -> Optional[str]:
        """매장명 추출"""
        pattern = re.search(r'([가-힣]+점)', question)
        if pattern:
            return pattern.group(1)
        return None
    
    def _extract_store_code(self, question: str) -> Optional[str]:
        """매장코드 추출"""
        pattern = re.search(r'매장[^\d]*(\d{4})', question)
        if pattern:
            return pattern.group(1)
        return None
    
    def _extract_dealer_code(self, question: str) -> Optional[str]:
        """대리점코드 추출"""
        # 대리점코드는 다양한 형식이 가능하므로 간단하게 처리
        pattern = re.search(r'대리점[^\w]*([A-Z0-9]+)', question, re.IGNORECASE)
        if pattern:
            return pattern.group(1).upper()
        return None
    
    def _extract_dealer_id(self, question: str) -> Optional[str]:
        """대리점 코드 추출"""
        pattern = re.search(r'대리점[^\w]*(D\d+)', question, re.IGNORECASE)
        if pattern:
            return pattern.group(1)
        return None
    
    def _extract_period(self, question: str) -> Optional[tuple]:
        """기간 추출"""
        # "12월"
        month_pattern = re.search(r'(\d+)월', question)
        if month_pattern:
            month = int(month_pattern.group(1))
            return (f'2025-{month:02d}-01', f'2025-{month:02d}-31')
        
        # "12월 25일 기준"
        date_pattern = re.search(r'(\d+)월\s*(\d+)일', question)
        if date_pattern:
            month = int(date_pattern.group(1))
            day = int(date_pattern.group(2))
            return (f'2025-{month:02d}-{day:02d}', f'2025-{month:02d}-{day:02d}')
        
        return None

    def _extract_comparison_periods(self, question: str, analysis_month: str = None) -> Optional[dict]:
        """
        비교 기간 추출 (기준 기간 vs 비교 기간)
        
        Returns:
            dict: 기간 정보 딕셔너리 또는 None
        """
        import calendar
        
        def get_month_last_day(year: int, month: int) -> int:
            """해당 월의 마지막 날 반환"""
            return calendar.monthrange(year, month)[1]
        
        # "12월 대비 1월"
        pattern1 = re.search(r'(\d+)월\s*대비\s*(\d+)월', question)
        if pattern1:
            base_month = int(pattern1.group(1))
            compare_month = int(pattern1.group(2))
            
            # 연도 처리 (1월이면 2026년, 나머지는 2025년)
            base_year = 2025
            compare_year = 2026 if compare_month <= 3 else 2025  # 1~3월은 2026년
            
            # 각 월의 마지막 날 계산
            base_last_day = get_month_last_day(base_year, base_month)
            compare_last_day = get_month_last_day(compare_year, compare_month)
            
            return {
                'period1_start': f'{base_year}-{base_month:02d}-01',
                'period1_end': f'{base_year}-{base_month:02d}-{base_last_day:02d}',
                'period2_start': f'{compare_year}-{compare_month:02d}-01',
                'period2_end': f'{compare_year}-{compare_month:02d}-{compare_last_day:02d}',
                'period1_label': f'{base_month}월',
                'period2_label': f'{compare_month}월'
            }
        
        # "9~12월 대비 1월"
        pattern2 = re.search(r'(\d+)~(\d+)월\s*대비\s*(\d+)월', question)
        if pattern2:
            start_month = int(pattern2.group(1))
            end_month = int(pattern2.group(2))
            compare_month = int(pattern2.group(3))
            
            base_year = 2025
            compare_year = 2026 if compare_month <= 3 else 2025
            
            # 각 월의 마지막 날 계산
            end_last_day = get_month_last_day(base_year, end_month)
            compare_last_day = get_month_last_day(compare_year, compare_month)
            
            return {
                'period1_start': f'{base_year}-{start_month:02d}-01',
                'period1_end': f'{base_year}-{end_month:02d}-{end_last_day:02d}',
                'period2_start': f'{compare_year}-{compare_month:02d}-01',
                'period2_end': f'{compare_year}-{compare_month:02d}-{compare_last_day:02d}',
                'period1_label': f'{start_month}~{end_month}월',
                'period2_label': f'{compare_month}월'
            }
        
        # "2일 누적 대비 5일 누적" 또는 "2일 대비 5일" (분석월 선택 시)
        pattern3 = re.search(r'(\d+)일\s*(?:누적\s*)?대비\s*(\d+)일', question)
        if pattern3 and analysis_month:
            base_day = int(pattern3.group(1))
            compare_day = int(pattern3.group(2))
            
            # analysis_month: "2025년 09월" 형식
            # 년도와 월 추출
            year_month_match = re.search(r'(\d{4})년\s*(\d{1,2})월', analysis_month)
            if year_month_match:
                year = int(year_month_match.group(1))
                month = int(year_month_match.group(2))
                
                # 월의 마지막 날 계산
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                
                # 일자 유효성 검사
                if base_day > last_day or compare_day > last_day:
                    return None
                
                return {
                    'period1_start': f'{year}-{month:02d}-01',
                    'period1_end': f'{year}-{month:02d}-{base_day:02d}',
                    'period2_start': f'{year}-{month:02d}-01',
                    'period2_end': f'{year}-{month:02d}-{compare_day:02d}',
                    'period1_label': f'{month}월 {base_day}일 누적',
                    'period2_label': f'{month}월 {compare_day}일 누적'
                }
        elif pattern3 and not analysis_month:
            # 분석월이 선택되지 않았을 때
            return {
                'error': '분석월을 선택해주세요',
                'period1_label': '오류',
                'period2_label': '오류'
            }

        return None
    
    def _detect_comparison(self, question: str) -> bool:
        """비교 모드 감지"""
        comparison_keywords = ['대비', '비교', 'vs', '차이']
        return any(keyword in question for keyword in comparison_keywords)
    
    def _detect_trend(self, question: str) -> Optional[str]:
        """트렌드 방향 감지"""
        if '하락' in question or '낮아진' in question or '떨어진' in question:
            return 'decrease'
        elif '상승' in question or '높아진' in question or '올라간' in question:
            return 'increase'
        return None
    
    def _detect_analysis_type(self, question: str) -> str:
        """분석 유형 감지"""
        # 1순위: 단순 필터 (NPS만, 시니어/기간비교 없음)
        if ('nps' in question or 'NPS' in question):
            if '시니어' not in question and '대비' not in question and '비교' not in question:
                return 'simple_filter'
        
        # 2순위: 시니어 GAP 분석 (시니어 + NPS 조합)
        if '시니어' in question:
            if ('nps' in question or 'NPS' in question):
                # 시니어 비중 관련 키워드가 있으면 시니어 GAP 분석
                senior_keywords = ['비중', '높은', '높고', '높으면서', '낮은', '낮고', '낮으면서', '많은', '적은']
                if any(keyword in question for keyword in senior_keywords):
                    return 'senior_gap'
                # "시니어 GAP" 명시
                elif 'gap' in question or 'GAP' in question or '차이' in question:
                    return 'senior_gap'
        
        # 3순위: 기간별 비교 분석
        if '기간' in question or '대비' in question or '비교' in question:
            if '상승' in question or '하락' in question:
                return 'period_comparison'
        
        # 4순위: 매장별 분석
        if '매장' in question or '대리점' in question:
            return 'store_analysis'
        
        # 기본: 일반 분석
        return 'general'
    
    def get_filter_summary(self, filters: Dict[str, Any]) -> str:
        """필터 조건 요약"""
        summary = []
        
        # 분석월 (맨 앞에 표시)
        if filters.get('analysis_month'):
            summary.append(f"분석월: {filters['analysis_month']}")
        
        if filters['team']:
            summary.append(f"팀: {filters['team']}")
        
        # NPS 목표 (NPS 조건이 있을 때만)
        if filters.get('nps_target'):
            comparison_text = "미만" if filters['nps_comparison'] == 'below' else "이상"
            summary.append(f"NPS 목표: {filters['nps_target']}% {comparison_text}")
        
        # 시니어 비중 (시니어 조건이 있을 때만)
        if filters.get('senior_threshold'):
            if filters['senior_threshold'] == 'avg':
                summary.append("시니어 비중: 평균 이상")
            elif filters['senior_threshold'] == 'below_avg':
                summary.append("시니어 비중: 평균 이하")
            elif filters['senior_threshold'].startswith('custom:'):
                value = filters['senior_threshold'].split(':')[1]
                summary.append(f"시니어 비중: {value}% 이상")
        
        if filters['min_responses']:
            summary.append(f"최소 응답수: {filters['min_responses']}건")
        
        if filters['store_name']:
            summary.append(f"매장: {filters['store_name']}")
        
        if filters['analysis_type']:
            type_names = {
                'senior_gap': '시니어 GAP 분석',
                'period_comparison': '기간별 비교',
                'simple_filter': '단순 필터 분석',
                'store_analysis': '매장 분석',
                'general': '일반 분석'
            }
            summary.append(f"분석 유형: {type_names[filters['analysis_type']]}")
        
        return ' | '.join(summary) if summary else "조건 없음"