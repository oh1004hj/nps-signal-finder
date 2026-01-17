"""
시니어 GAP 분석 모듈
시니어 응답 비중이 높은데 NPS가 목표 미달인 T크루 찾기
"""

import pandas as pd
import numpy as np

class SeniorGapAnalyzer:
    """시니어 GAP 분석"""
    
    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: NPS RAW DATA
        """
        self.df = df
    
    def _calculate_nps(self, scores):
        """
        NPS 계산 (추천자 비율 - 비추천자 비율)
        
        Args:
            scores: 추천지수 시리즈
            
        Returns:
            NPS 값
        """
        total = len(scores)
        if total == 0:
            return 0
        
        promoters = (scores >= 9).sum()  # 추천자 (9-10점)
        detractors = (scores <= 6).sum()  # 비추천자 (0-6점)
        
        nps = ((promoters - detractors) / total) * 100
        return round(nps, 2)

    def _get_weighted_avg_nps(self, df_filtered: pd.DataFrame, result: pd.DataFrame) -> str:
        """
        가중 평균 NPS 계산
        
        Args:
            df_filtered: 필터링된 원본 데이터
            result: 조건을 만족하는 T크루 목록
            
        Returns:
            가중 평균 NPS 문자열 (예: "72.5%")
        """
        if len(result) == 0:
            return "N/A"
        
        # result에 해당하는 담당자들의 원본 데이터 필터링
        filtered_tcrews = result['담당자ID'].tolist()
        result_data = df_filtered[df_filtered['담당자ID'].isin(filtered_tcrews)]
        
        # 전체 응답 데이터로 NPS 계산 (가중 평균)
        weighted_nps = self._calculate_nps(result_data['추천지수'])
        
        return f"{weighted_nps:.1f}%"
    
    def analyze(self, filters: dict) -> dict:
        """
        시니어 GAP 분석 실행
        
        Args:
            filters: 필터 조건
            
        Returns:
            분석 결과 딕셔너리
        """
        # 기본 필터링
        df_filtered = self.df.copy()
        
        # 분석월 필터 (NEW!)
        if filters.get('analysis_month') and filters['analysis_month'] != "전체":
            analysis_month = filters['analysis_month']
            # 처리일을 datetime으로 변환
            df_filtered['처리일_dt'] = pd.to_datetime(df_filtered['처리일'], format='%Y%m%d', errors='coerce')
            # 년월 추출 (YYYY년 MM월)
            df_filtered['년월'] = df_filtered['처리일_dt'].dt.strftime('%Y년 %m월')
            # 선택한 월만 필터링
            df_filtered = df_filtered[df_filtered['년월'] == analysis_month]
            # 임시 컬럼 제거
            df_filtered = df_filtered.drop(columns=['처리일_dt', '년월'])
        
        # 팀 필터
        if filters.get('team'):
            df_filtered = df_filtered[df_filtered['마케팅팀명'] == filters['team']]
        
        # 대리점명 필터
        if filters.get('dealer_name'):
            df_filtered = df_filtered[df_filtered['대리점명'] == filters['dealer_name']]
        
        # 매장 필터
        if filters.get('store_name'):
            df_filtered = df_filtered[df_filtered['매장명'] == filters['store_name']]
        
        # 담당자별 집계 (대리점코드, 매장명 포함)
        tcrew_stats_list = []
        
        for (tcrew_name, tcrew_id), group in df_filtered.groupby(['담당자', '담당자ID']):
            # 기본 통계
            total_responses = len(group)
            promoters = (group['추천지수'] >= 9).sum()
            detractors = (group['추천지수'] <= 6).sum()
            senior_responses = (group['시니어여부'] == 'Y').sum()
            
            # 전체 NPS
            nps = self._calculate_nps(group['추천지수'])
            
            # 시니어 NPS
            senior_data = group[group['시니어여부'] == 'Y']
            senior_nps = self._calculate_nps(senior_data['추천지수']) if len(senior_data) > 0 else 0
            
            # 시니어 비중
            senior_rate = (senior_responses / total_responses * 100) if total_responses > 0 else 0
            
            # 대리점명, 매장명 (첫 번째 값 사용)
            dealer_name = group['대리점명'].iloc[0] if '대리점명' in group.columns else ''
            store_name = group['매장명'].iloc[0] if '매장명' in group.columns else ''
            
            tcrew_stats_list.append({
                '담당자': tcrew_name,
                '담당자ID': tcrew_id,
                '대리점명': dealer_name,
                '매장명': store_name,
                '총응답수': total_responses,
                '추천자수': promoters,
                '비추천자수': detractors,
                '시니어응답수': senior_responses,
                'NPS': f"{nps:.1f}%",
                'NPS_value': nps,  # 정렬용 숫자값
                '시니어비중': f"{senior_rate:.1f}%",
                '시니어비중_value': senior_rate,  # 정렬용 숫자값
                '시니어NPS': f"{senior_nps:.1f}%"
            })
        
        tcrew_stats = pd.DataFrame(tcrew_stats_list)
        
        if len(tcrew_stats) == 0:
            return {
                'data': pd.DataFrame(),
                'insights': ["⚠️ 조건을 만족하는 데이터가 없습니다."],
                'summary': {
                    '조건 만족 T크루': 0,
                    'NPS 목표': "N/A",
                    '필터 조건 Y 시니어 비중': "N/A",
                    '조건 만족 T크루 NPS': "N/A"
                }
            }
        
        # 전체 평균 (원본 데이터 기준 - 응답수 가중)
        total_responses = len(df_filtered)
        total_senior_responses = len(df_filtered[df_filtered['시니어여부'] == 'Y'])
        avg_senior_rate = (total_senior_responses / total_responses) * 100 if total_responses > 0 else 0
        
        # 전체 NPS (원본 데이터 기준)
        avg_nps = self._calculate_nps(df_filtered['추천지수'])
        
        # 시니어 NPS 평균 계산 (시니어 응답이 있는 T크루만)
        tcrew_with_senior = tcrew_stats[tcrew_stats['시니어응답수'] > 0]
        if len(tcrew_with_senior) > 0:
            # 시니어NPS에서 %를 제거하고 숫자로 변환
            senior_nps_values = tcrew_with_senior['시니어NPS'].str.rstrip('%').astype(float)
            avg_senior_nps = senior_nps_values.mean()
        else:
            avg_senior_nps = 0
        
        # 필터링 조건 적용
        result = tcrew_stats.copy()
        
        # 시니어 비중 필터 (시니어 조건이 있을 때만)
        senior_threshold = filters.get('senior_threshold')
        
        if senior_threshold:  # None이 아닐 때만 적용
            if senior_threshold == 'avg':
                # 평균 이상
                result = result[result['시니어비중_value'] >= avg_senior_rate]
            elif senior_threshold == 'below_avg':
                # 평균 이하
                result = result[result['시니어비중_value'] < avg_senior_rate]
            elif senior_threshold.startswith('custom:'):
                # 특정 값 이상
                custom_value = float(senior_threshold.split(':')[1])
                result = result[result['시니어비중_value'] >= custom_value]
        else:
            # 시니어 조건이 없으면 기본값 평균 이상 적용
            result = result[result['시니어비중_value'] >= avg_senior_rate]
        
        # 시니어 NPS 필터 (NEW! - 평균보다 낮은 T크루만)
        if len(result) > 0:
            # 시니어 응답이 있는 T크루만 대상
            result = result[result['시니어응답수'] > 0]
            # 시니어NPS를 숫자로 변환하여 필터링
            result_senior_nps = result['시니어NPS'].str.rstrip('%').astype(float)
            result = result[result_senior_nps < avg_senior_nps]
        
        # NPS 목표 기준 필터 (NPS 조건이 있을 때만)
        if filters.get('nps_target') is not None:
            nps_target = filters['nps_target']
            nps_comparison = filters.get('nps_comparison', 'below')
            
            if nps_comparison == 'below':
                result = result[result['NPS_value'] < nps_target]
            else:  # 'above'
                result = result[result['NPS_value'] >= nps_target]
        else:
            # NPS 조건이 없으면 기본값 87 미만 적용
            nps_target = 87
            nps_comparison = 'below'
            result = result[result['NPS_value'] < nps_target]
        
        # 최소 응답수
        min_resp = filters.get('min_responses', 5)
        result = result[result['총응답수'] >= min_resp]
        
        # 최소 시니어 응답수
        result = result[result['시니어응답수'] >= 1]
        
        # 정렬: 시니어 비중 높은 순, NPS 낮은 순
        result = result.sort_values(['시니어비중_value', 'NPS_value'], ascending=[False, True])
        
        # 정렬용 숫자값 컬럼 제거 및 컬럼명 변경
        display_columns = ['담당자', '담당자ID', '대리점명', '매장명', '총응답수', 
                          '추천자수', '비추천자수', '시니어응답수', 'NPS', '시니어비중', '시니어NPS']
        result_display = result[display_columns].copy()
        
        # 컬럼명 변경 (다른 분석 타입과 통일)
        result_display.columns = ['담당자', '담당자ID', '대리점명', '매장명', '응답수', 
                                 '추천수', '비추천수', '시니어응답수', 'NPS(%)', '시니어비중(%)', '시니어NPS(%)']
        
        # T크루별 결과 (기존)
        result_tcrew = result_display
        
        # 매장별 결과 (조건 만족 T크루만 대상)
        result_store = self._analyze_by_store(df_filtered, filters, avg_senior_rate, avg_nps, nps_target, nps_comparison, result)
        
        # 매장별 T크루 상세 (신규 추가 - Expander용)
        store_tcrew_detail = self._get_store_tcrew_detail(df_filtered, result, avg_senior_rate)
        
        # 인사이트 생성
        insights = self._generate_insights(
            result, 
            avg_senior_rate, 
            avg_nps,
            nps_target,
            nps_comparison
        )
        
        # summary 구성
        summary_dict = {
            '조건 만족 T크루': len(result),
            '조건 만족 매장': len(result_store),
            'NPS 목표': f"{nps_target}%",
            '필터 조건Y 시니어 비중': f"{avg_senior_rate:.1f}% ({total_senior_responses}/{total_responses})",
            '조건 만족 T크루 NPS': self._get_weighted_avg_nps(df_filtered, result) if len(result) > 0 else "N/A"
        }
        
        # 분석월이 있으면 summary에 추가
        if filters.get('analysis_month'):
            summary_dict['분석월'] = filters['analysis_month']
        
        return {
            'by_tcrew': result_tcrew,
            'by_store': result_store,
            'store_tcrew_detail': store_tcrew_detail,
            'insights': insights,
            'summary': summary_dict
        }
    
    def _generate_insights(self, result: pd.DataFrame, avg_senior_rate: float, 
                          avg_nps: float, nps_target: float, nps_comparison: str) -> list:
        """인사이트 생성"""
        insights = []
        
        if len(result) == 0:
            insights.append("⚠️ 조건을 만족하는 T크루가 없습니다.")
            if nps_comparison == 'below':
                insights.append(f"✨ 모든 T크루가 NPS 목표({nps_target}%)를 달성했습니다!")
            else:
                insights.append("💡 필터 조건을 완화해보세요!")
            return insights
        
        # 기본 통계
        insights.append(f"📊 총 **{len(result)}명**의 T크루가 조건을 만족합니다")
        
        if nps_comparison == 'below':
            insights.append(f"🎯 NPS 목표 **{nps_target}%** 미달 T크루입니다")
        else:
            insights.append(f"🎯 NPS 목표 **{nps_target}%** 달성 T크루입니다")
        
        insights.append(f"📈 필터 조건Y 비중: **{result['시니어비중_value'].mean():.1f}%** (전체 평균: {avg_senior_rate:.1f}%)")
        insights.append(f"📉 평균 NPS: **{result['NPS_value'].mean():.1f}** (전체 평균: {avg_nps:.1f}%)")
        
        # TOP 1 하이라이트
        if len(result) > 0:
            top1 = result.iloc[0]
            insights.append(
                f"🔴 **{top1['담당자']}** T크루: 시니어 비중 **{top1['시니어비중']}**, NPS **{top1['NPS']}**, 시니어NPS **{top1['시니어NPS']}**"
            )
        
        # 시니어 비중이 특히 높은 그룹
        high_senior = result[result['시니어비중_value'] >= 30]
        if len(high_senior) > 0:
            insights.append(f"⚠️ 시니어 비중 30% 이상인 T크루가 **{len(high_senior)}명**입니다")
        
        # 시니어 NPS와 전체 NPS 차이 분석 (순수한 숫자값 사용)
        if 'NPS_value' in result.columns and len(result) > 0:
            # 시니어NPS에서 %를 제거하고 숫자로 변환
            senior_nps_values = result['시니어NPS'].str.rstrip('%').astype(float)
            nps_gaps = abs(result['NPS_value'] - senior_nps_values)
            
            # GAP이 10 이상인 T크루 수 계산
            large_gap_count = (nps_gaps >= 10).sum()
            if large_gap_count > 0:
                insights.append(f"⚠️ 시니어 NPS와 전체 NPS 차이가 10% 이상인 T크루가 **{large_gap_count}명**입니다")
        
        # 액션 아이템
        if nps_comparison == 'below':
            insights.append(f"💡 **시니어 고객 응대 개선**이 NPS 목표 달성의 핵심입니다!")
        
        return insights
    
    def _analyze_by_store(self, df_filtered: pd.DataFrame, filters: dict,
                         avg_senior_rate: float, avg_nps: float, 
                         nps_target: float, nps_comparison: str,
                         result_tcrew: pd.DataFrame) -> pd.DataFrame:
        """
        매장별 시니어 GAP 분석 (조건 만족 T크루만 대상)
        
        Args:
            df_filtered: 필터링된 원본 데이터
            filters: 필터 조건
            avg_senior_rate: 전체 평균 시니어 비중
            avg_nps: 전체 평균 NPS
            nps_target: NPS 목표값
            nps_comparison: NPS 비교 방향
            result_tcrew: 조건 만족 T크루 목록
            
        Returns:
            매장별 분석 결과
        """
        # 조건 만족하는 T크루의 ID 목록
        satisfied_tcrew_ids = result_tcrew['담당자ID'].tolist()
        
        # 해당 T크루들의 데이터만 필터링
        df_satisfied = df_filtered[df_filtered['담당자ID'].isin(satisfied_tcrew_ids)]
        
        if len(df_satisfied) == 0:
            return pd.DataFrame()
        
        store_stats_list = []
        
        for (team, dealer, store), group in df_satisfied.groupby(['마케팅팀명', '대리점명', '매장명']):
            # 기본 통계
            total_responses = len(group)
            promoters = (group['추천지수'] >= 9).sum()
            detractors = (group['추천지수'] <= 6).sum()
            senior_responses = (group['시니어여부'] == 'Y').sum()
            
            # 전체 NPS
            nps = self._calculate_nps(group['추천지수'])
            
            # 시니어 NPS
            senior_data = group[group['시니어여부'] == 'Y']
            senior_nps = self._calculate_nps(senior_data['추천지수']) if len(senior_data) > 0 else 0
            
            # 시니어 비중
            senior_rate = (senior_responses / total_responses * 100) if total_responses > 0 else 0
            
            store_stats_list.append({
                '마케팅팀명': team,
                '대리점명': dealer,
                '매장명': store,
                '총응답수': total_responses,
                '추천자수': promoters,
                '비추천자수': detractors,
                '시니어응답수': senior_responses,
                'NPS': f"{nps:.1f}%",
                'NPS_value': nps,
                '시니어비중': f"{senior_rate:.1f}%",
                '시니어비중_value': senior_rate,
                '시니어NPS': f"{senior_nps:.1f}%"
            })
        
        store_stats = pd.DataFrame(store_stats_list)
        
        if len(store_stats) == 0:
            return pd.DataFrame()
        
        # 매장별 필터링 적용 (T크루와 동일 기준)
        # NPS 필터
        if nps_comparison == 'below':
            store_stats = store_stats[store_stats['NPS_value'] < nps_target]
        else:
            store_stats = store_stats[store_stats['NPS_value'] >= nps_target]
        
        # 시니어 비중 필터
        senior_threshold = filters.get('senior_threshold')
        if senior_threshold:
            if senior_threshold == 'avg':
                store_stats = store_stats[store_stats['시니어비중_value'] >= avg_senior_rate]
            elif senior_threshold == 'below_avg':
                store_stats = store_stats[store_stats['시니어비중_value'] < avg_senior_rate]
            elif senior_threshold.startswith('custom:'):
                custom_value = float(senior_threshold.split(':')[1])
                store_stats = store_stats[store_stats['시니어비중_value'] >= custom_value]
        else:
            # 기본값: 평균 이상
            store_stats = store_stats[store_stats['시니어비중_value'] >= avg_senior_rate]
        
        # 최소 응답수
        min_resp = filters.get('min_responses', 5)
        store_stats = store_stats[store_stats['총응답수'] >= min_resp]
        
        # 최소 시니어 응답수
        store_stats = store_stats[store_stats['시니어응답수'] >= 1]
        
        if len(store_stats) == 0:
            return pd.DataFrame()
        
        # 정렬: 시니어비중 높은 순, NPS 낮은 순 (T크루와 동일)
        store_stats = store_stats.sort_values(
            ['시니어비중_value', 'NPS_value'],
            ascending=[False, True]
        )
        
        # 표시용 컬럼만 선택 및 컬럼명 변경
        display_columns = ['마케팅팀명', '대리점명', '매장명', '총응답수', 
                          '추천자수', '비추천자수', '시니어응답수', 'NPS', '시니어비중', '시니어NPS']
        result_display = store_stats[display_columns].copy()
        
        # 컬럼명 변경 (다른 분석 타입과 통일)
        result_display.columns = ['마케팅팀명', '대리점명', '매장명', '응답수', 
                                 '추천수', '비추천수', '시니어응답수', 'NPS(%)', '시니어비중(%)', '시니어NPS(%)']
        
        result_display = result_display.reset_index(drop=True)
        
        return result_display
    
    def _get_store_tcrew_detail(self, df_filtered: pd.DataFrame, 
                               result_tcrew: pd.DataFrame,
                               avg_senior_rate: float) -> dict:
        """
        매장별 T크루 상세 정보 (Expander용)
        
        Args:
            df_filtered: 필터링된 원본 데이터
            result_tcrew: 조건 만족 T크루 목록
            avg_senior_rate: 전체 평균 시니어 비중
            
        Returns:
            {매장명: T크루 DataFrame} 딕셔너리
        """
        # 조건 만족하는 T크루의 ID 목록
        satisfied_tcrew_ids = result_tcrew['담당자ID'].tolist()
        
        # 해당 T크루들의 데이터만 필터링
        df_satisfied = df_filtered[df_filtered['담당자ID'].isin(satisfied_tcrew_ids)]
        
        if len(df_satisfied) == 0:
            return {}
        
        # 매장별 전체 응답수 계산 (비중 계산용)
        store_total = df_satisfied.groupby('매장명')['추천지수'].count().to_dict()
        
        # 매장별 평균 NPS 계산 (vs 비교용)
        store_nps = {}
        for store_name, group in df_satisfied.groupby('매장명'):
            store_nps[store_name] = self._calculate_nps(group['추천지수'])
        
        # 매장-T크루별 집계
        tcrew_detail_list = []
        
        for (store, tcrew_name, tcrew_id), group in df_satisfied.groupby(['매장명', '담당자', '담당자ID']):
            # 기본 통계
            total_responses = len(group)
            promoters = (group['추천지수'] >= 9).sum()
            detractors = (group['추천지수'] <= 6).sum()
            senior_responses = (group['시니어여부'] == 'Y').sum()
            
            # 전체 NPS
            nps = self._calculate_nps(group['추천지수'])
            
            # 시니어 NPS
            senior_data = group[group['시니어여부'] == 'Y']
            senior_nps = self._calculate_nps(senior_data['추천지수']) if len(senior_data) > 0 else 0
            
            # 시니어 비중
            senior_rate = (senior_responses / total_responses * 100) if total_responses > 0 else 0
            
            tcrew_detail_list.append({
                '매장명': store,
                'T크루명': tcrew_name,
                '응답수': total_responses,
                '추천수': promoters,
                '비추천수': detractors,
                '시니어응답수': senior_responses,
                'NPS(%)': f"{nps:.1f}%",
                '시니어비중(%)': f"{senior_rate:.1f}%",
                '시니어NPS(%)': f"{senior_nps:.1f}%"
            })
        
        tcrew_detail = pd.DataFrame(tcrew_detail_list)
        
        # 매장별로 딕셔너리 생성
        result = {}
        for store_name in tcrew_detail['매장명'].unique():
            store_df = tcrew_detail[tcrew_detail['매장명'] == store_name].copy()
            
            # NPS 낮은 순으로 정렬 (문제 있는 T크루가 위로)
            # NPS에서 % 제거하고 정렬
            store_df['NPS_value'] = store_df['NPS(%)'].str.rstrip('%').astype(float)
            store_df = store_df.sort_values('NPS_value', ascending=True)
            store_df = store_df.drop(columns=['NPS_value'])
            
            # 필요한 컬럼만 (T크루별 탭과 동일)
            store_df = store_df[['T크루명', '응답수', '추천수', '비추천수', '시니어응답수', 
                               'NPS(%)', '시니어비중(%)', '시니어NPS(%)']]
            
            result[store_name] = store_df.reset_index(drop=True)
        
        return result