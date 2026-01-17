"""
기간별 비교 분석 모듈
특정 기간 대비 NPS 변화 분석
"""

import pandas as pd
import numpy as np

class PeriodComparisonAnalyzer:
    """기간별 비교 분석"""
    
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
        
        promoters = (scores >= 9).sum()
        detractors = (scores <= 6).sum()
        
        nps = ((promoters - detractors) / total) * 100
        return round(nps, 2)
    
    def analyze(self, filters: dict) -> dict:
        """
        기간별 비교 분석 실행
        
        Args:
            filters: 필터 조건
            
        Returns:
            분석 결과 딕셔너리
        """
        # 기본 필터링 (물리적 필터는 app.py에서 이미 처리됨)
        df_filtered = self.df.copy()
        
        # 날짜 컬럼 확인
        if '처리일' not in df_filtered.columns:
            return {
                'data': pd.DataFrame(),
                'insights': ["⚠️ 처리일 컬럼이 없습니다."],
                'summary': {
                    '조건 만족 T크루': 0,
                    '기준 기간': 'N/A',
                    '비교 기간': 'N/A',
                    '평균 NPS 증감': 'N/A'
                }
            }
        
        # 날짜 형식 변환 (YYYYMMDD 문자열 → datetime)
        df_filtered['처리일'] = pd.to_datetime(df_filtered['처리일'], format='%Y%m%d', errors='coerce')
        
        # 디버깅: 분석월 필터 후 데이터 확인
        print(f"🔍 분석월 필터 후 데이터: {len(df_filtered)}건")
        if len(df_filtered) > 0:
            print(f"   처리일 범위: {df_filtered['처리일'].min()} ~ {df_filtered['처리일'].max()}")
        
        # 기간 설정 (filters에서 가져오기)
        comparison_periods = filters.get('comparison_periods')
        
        # 에러 체크 (분석월 미선택 시)
        if comparison_periods and comparison_periods.get('error'):
            return {
                'by_tcrew': pd.DataFrame(),
                'by_store': pd.DataFrame(),
                'store_tcrew_detail': {},
                'insights': [f"⚠️ {comparison_periods['error']}"],
                'summary': {
                    '조건 만족 T크루': 0,
                    '조건 만족 매장': 0,
                    '기준 기간': 'N/A',
                    '비교 기간': 'N/A',
                    '평균 NPS 증감': 'N/A'
                }
            }
        
        if comparison_periods:
            # 질문에서 추출한 기간 사용
            period1_start = pd.Timestamp(comparison_periods['period1_start'])
            period1_end = pd.Timestamp(comparison_periods['period1_end'])
            period2_start = pd.Timestamp(comparison_periods['period2_start'])
            period2_end = pd.Timestamp(comparison_periods['period2_end'])
            period1_label = comparison_periods['period1_label']
            period2_label = comparison_periods['period2_label']
        else:
            # 기본값: 9~12월 vs 1월
            period1_start = pd.Timestamp('2025-09-01')
            period1_end = pd.Timestamp('2025-12-31')
            period2_start = pd.Timestamp('2026-01-01')
            period2_end = pd.Timestamp('2026-01-31')
            period1_label = '9~12월'
            period2_label = '1월'
        
        # 기간별 데이터 분리 (끝 날짜는 다음날 00:00 전까지)
        df_period1 = df_filtered[
            (df_filtered['처리일'] >= period1_start) & 
            (df_filtered['처리일'] < period1_end + pd.Timedelta(days=1))
        ]
        df_period2 = df_filtered[
            (df_filtered['처리일'] >= period2_start) & 
            (df_filtered['처리일'] < period2_end + pd.Timedelta(days=1))
        ]
        
        # 디버깅: 기간별 데이터 확인
        print(f"📊 기간1 ({period1_label}): {len(df_period1)}건")
        print(f"📊 기간2 ({period2_label}): {len(df_period2)}건")
        print(f"   period1: {period1_start} ~ {period1_end}")
        print(f"   period2: {period2_start} ~ {period2_end}")
        
        # 기간1 담당자별 집계
        period1_stats = self._aggregate_by_tcrew(df_period1)
        print(f"👥 기간1 T크루: {len(period1_stats)}명")
        
        if len(period1_stats) == 0:
            return {
                'by_tcrew': pd.DataFrame(),
                'by_store': pd.DataFrame(),
                'store_tcrew_detail': {},
                'insights': [
                    f"⚠️ 기준 기간({period1_label})에 응답 데이터가 없습니다.",
                    "💡 분석월 필터를 '전체'로 변경해보세요."
                ],
                'summary': {
                    '조건 만족 T크루': 0,
                    '조건 만족 매장': 0,
                    '기준 기간': f'{period1_label}',
                    '비교 기간': f'{period2_label}',
                }
            }
        
        period1_stats = period1_stats.rename(columns={
            'NPS': '기준기간_NPS',
            'NPS_value': '기준기간_NPS_value',
            '총응답수': '기준기간_응답수',
            '추천자수': '기준기간_추천자수',
            '비추천자수': '기준기간_비추천자수'
        })
        
        # 기간2 담당자별 집계
        period2_stats = self._aggregate_by_tcrew(df_period2)
        print(f"👥 기간2 T크루: {len(period2_stats)}명")
        
        if len(period2_stats) == 0:
            return {
                'by_tcrew': pd.DataFrame(),
                'by_store': pd.DataFrame(),
                'store_tcrew_detail': {},
                'insights': [
                    f"⚠️ 비교 기간({period2_label})에 응답 데이터가 없습니다.",
                    "💡 분석월 필터를 '전체'로 변경해보세요."
                ],
                'summary': {
                    '조건 만족 T크루': 0,
                    '조건 만족 매장': 0,
                    '기준 기간': f'{period1_label}',
                    '비교 기간': f'{period2_label}',
                    '평균 NPS 증감': 'N/A'
                }
            }
        
        period2_stats = period2_stats.rename(columns={
            'NPS': '비교기간_NPS',
            'NPS_value': '비교기간_NPS_value',
            '총응답수': '비교기간_응답수',
            '추천자수': '비교기간_추천자수',
            '비추천자수': '비교기간_비추천자수'
        })
        
        # 두 기간 데이터 병합
        result = pd.merge(
            period1_stats[['담당자', '담당자ID', '대리점명', '매장명', 
                          '기준기간_NPS', '기준기간_NPS_value', '기준기간_응답수']],
            period2_stats[['담당자', '담당자ID', '대리점명', '매장명',
                          '비교기간_NPS', '비교기간_NPS_value', '비교기간_응답수']],
            on=['담당자', '담당자ID', '대리점명', '매장명'],
            how='inner'  # 두 기간 모두 데이터가 있는 T크루만
        )
        
        print(f"🔗 병합 후 T크루: {len(result)}명")
        
        if len(result) == 0:
            return {
                'by_tcrew': pd.DataFrame(),
                'by_store': pd.DataFrame(),
                'store_tcrew_detail': {},
                'insights': [
                    "⚠️ 두 기간 모두 데이터가 있는 T크루가 없습니다.",
                    "💡 분석월 필터를 '전체'로 변경해보세요."
                ],
                'summary': {
                    '조건 만족 T크루': 0,
                    '조건 만족 매장': 0,
                    '기준 기간': f'{period1_label}',
                    '비교 기간': f'{period2_label}',
                    '평균 NPS 증감': 'N/A'
                }
            }
        
        # NPS 증감 계산
        result['NPS증감_value'] = result['비교기간_NPS_value'] - result['기준기간_NPS_value']
        result['NPS증감'] = result['NPS증감_value'].apply(
            lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%"
        )
        
        # 트렌드 필터 적용
        trend = filters.get('trend')
        if trend == 'decrease':
            # 하락한 T크루만
            result = result[result['NPS증감_value'] < 0]
        elif trend == 'increase':
            # 상승한 T크루만
            result = result[result['NPS증감_value'] > 0]
        
        # NPS 목표 기준 필터 (비교기간 NPS 기준)
        if filters.get('nps_target') is not None:
            nps_target = filters['nps_target']
            nps_comparison = filters.get('nps_comparison', 'below')
            
            if nps_comparison == 'below':
                # 비교기간 NPS가 목표 미달
                result = result[result['비교기간_NPS_value'] < nps_target]
            else:  # 'above'
                # 비교기간 NPS가 목표 달성
                result = result[result['비교기간_NPS_value'] >= nps_target]
        
        # 최소 응답수 필터 (두 기간 각각 다른 값 가능)
        min_resp_period1 = filters.get('min_responses_period1', filters.get('min_responses', 5))
        min_resp_period2 = filters.get('min_responses_period2', filters.get('min_responses', 5))
        
        result = result[
            (result['기준기간_응답수'] >= min_resp_period1) & 
            (result['비교기간_응답수'] >= min_resp_period2)
        ]
        
        # 정렬
        if trend == 'decrease':
            # 하락폭 큰 순
            result = result.sort_values('NPS증감_value', ascending=True)
        elif trend == 'increase':
            # 상승폭 큰 순
            result = result.sort_values('NPS증감_value', ascending=False)
        else:
            # 증감 절댓값 큰 순
            result = result.sort_values('NPS증감_value', key=abs, ascending=False)
        
        # 표시용 컬럼 선택
        display_columns = ['담당자', '담당자ID', '대리점명', '매장명',
                          '기준기간_NPS', '기준기간_응답수',
                          '비교기간_NPS', '비교기간_응답수',
                          'NPS증감']
        
        # 컬럼명 변경 (보기 좋게)
        result_display = result[display_columns].copy()
        result_display.columns = ['담당자', '담당자ID', '대리점명', '매장명',
                                  f'{period1_label} NPS', f'{period1_label} 응답수',
                                  f'{period2_label} NPS', f'{period2_label} 응답수',
                                  'NPS 증감']
        
        # T크루별 결과 (기존)
        result_tcrew = result_display
        
        # 매장별 결과 (신규 추가)
        result_store = self._analyze_by_store(df_period1, df_period2, period1_label, period2_label, filters, trend)
        
        # 매장별 T크루 상세 (신규 추가 - Expander용)
        store_tcrew_detail = self._get_store_tcrew_detail(df_period1, df_period2, result, period1_label, period2_label)
        
        # 인사이트 생성
        insights = self._generate_insights(result, trend)
        
        return {
            'by_tcrew': result_tcrew,
            'by_store': result_store,
            'store_tcrew_detail': store_tcrew_detail,
            'insights': insights,
            'summary': {
                '조건 만족 T크루': len(result),
                '조건 만족 매장': len(result_store),
                '기준 기간': f'{period1_label}',
                '비교 기간': f'{period2_label}',
                '평균 NPS 증감': f"{result['NPS증감_value'].mean():.1f}%"
            }
        }
    
    def _aggregate_by_tcrew(self, df: pd.DataFrame) -> pd.DataFrame:
        """담당자별 집계"""
        tcrew_stats_list = []
        
        for (tcrew_name, tcrew_id), group in df.groupby(['담당자', '담당자ID']):
            # 기본 통계
            total_responses = len(group)
            promoters = (group['추천지수'] >= 9).sum()
            detractors = (group['추천지수'] <= 6).sum()
            
            # NPS 계산
            nps = self._calculate_nps(group['추천지수'])
            
            # 대리점명, 매장명
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
                'NPS': f"{nps:.1f}%",
                'NPS_value': nps
            })
        
        return pd.DataFrame(tcrew_stats_list)
    
    def _generate_insights(self, result: pd.DataFrame, trend: str) -> list:
        """인사이트 생성"""
        insights = []
        
        if len(result) == 0:
            insights.append("⚠️ 조건을 만족하는 T크루가 없습니다.")
            return insights
        
        # 기본 통계
        total_count = len(result)
        avg_change = result['NPS증감_value'].mean()
        
        if trend == 'decrease':
            insights.append(f"📊 총 **{total_count}명**의 T크루가 NPS 하락했습니다")
            insights.append(f"📉 평균 하락폭: **{abs(avg_change):.1f}%p**")
        elif trend == 'increase':
            insights.append(f"📊 총 **{total_count}명**의 T크루가 NPS 상승했습니다")
            insights.append(f"📈 평균 상승폭: **{avg_change:.1f}%p**")
        else:
            insights.append(f"📊 총 **{total_count}명**의 T크루 데이터가 있습니다")
            insights.append(f"📊 평균 NPS 변화: **{avg_change:+.1f}%p**")
        
        # TOP 1 하이라이트
        if len(result) > 0:
            top1 = result.iloc[0]
            if trend == 'decrease':
                insights.append(
                    f"🔴 **{top1['담당자']}** T크루: 최대 하락 **{abs(top1['NPS증감_value']):.1f}%p** "
                    f"({top1['기준기간_NPS_value']:.1f}% → {top1['비교기간_NPS_value']:.1f}%)"
                )
            elif trend == 'increase':
                insights.append(
                    f"🟢 **{top1['담당자']}** T크루: 최대 상승 **{top1['NPS증감_value']:.1f}%p** "
                    f"({top1['기준기간_NPS_value']:.1f}% → {top1['비교기간_NPS_value']:.1f}%)"
                )
        
        # 큰 변화 그룹
        if trend == 'decrease':
            large_decrease = result[result['NPS증감_value'] <= -10]
            if len(large_decrease) > 0:
                insights.append(f"⚠️ NPS 10%p 이상 하락한 T크루가 **{len(large_decrease)}명**입니다")
        elif trend == 'increase':
            large_increase = result[result['NPS증감_value'] >= 10]
            if len(large_increase) > 0:
                insights.append(f"✨ NPS 10%p 이상 상승한 T크루가 **{len(large_increase)}명**입니다")
        
        return insights
    
    def _analyze_by_store(self, df_period1: pd.DataFrame, df_period2: pd.DataFrame,
                         period1_label: str, period2_label: str,
                         filters: dict, trend: str) -> pd.DataFrame:
        """
        매장별 기간 비교 분석
        
        Args:
            df_period1: 기준 기간 데이터
            df_period2: 비교 기간 데이터
            period1_label: 기준 기간 레이블
            period2_label: 비교 기간 레이블
            filters: 필터 조건
            trend: 트렌드 ('increase', 'decrease', None)
            
        Returns:
            매장별 분석 결과
        """
        # 기간1 매장별 집계
        period1_store = []
        for (team, dealer, store), group in df_period1.groupby(['마케팅팀명', '대리점명', '매장명']):
            total_responses = len(group)
            nps = self._calculate_nps(group['추천지수'])
            
            period1_store.append({
                '마케팅팀명': team,
                '대리점명': dealer,
                '매장명': store,
                '기준기간_응답수': total_responses,
                '기준기간_NPS_value': nps,
                '기준기간_NPS': f"{nps:.1f}%"
            })
        
        period1_store_df = pd.DataFrame(period1_store)
        
        if len(period1_store_df) == 0:
            return pd.DataFrame()
        
        # 기간2 매장별 집계
        period2_store = []
        for (team, dealer, store), group in df_period2.groupby(['마케팅팀명', '대리점명', '매장명']):
            total_responses = len(group)
            nps = self._calculate_nps(group['추천지수'])
            
            period2_store.append({
                '마케팅팀명': team,
                '대리점명': dealer,
                '매장명': store,
                '비교기간_응답수': total_responses,
                '비교기간_NPS_value': nps,
                '비교기간_NPS': f"{nps:.1f}%"
            })
        
        period2_store_df = pd.DataFrame(period2_store)
        
        if len(period2_store_df) == 0:
            return pd.DataFrame()
        
        # 두 기간 데이터 병합
        result = pd.merge(
            period1_store_df,
            period2_store_df,
            on=['마케팅팀명', '대리점명', '매장명'],
            how='inner'
        )
        
        if len(result) == 0:
            return pd.DataFrame()
        
        # NPS 증감 계산
        result['NPS증감_value'] = result['비교기간_NPS_value'] - result['기준기간_NPS_value']
        result['NPS증감'] = result['NPS증감_value'].apply(
            lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%"
        )
        
        # 트렌드 필터 적용
        if trend == 'decrease':
            result = result[result['NPS증감_value'] < 0]
        elif trend == 'increase':
            result = result[result['NPS증감_value'] > 0]
        
        # NPS 목표 기준 필터 (비교기간 NPS 기준)
        if filters.get('nps_target') is not None:
            nps_target = filters['nps_target']
            nps_comparison = filters.get('nps_comparison', 'below')
            
            if nps_comparison == 'below':
                result = result[result['비교기간_NPS_value'] < nps_target]
            else:
                result = result[result['비교기간_NPS_value'] >= nps_target]
        
        # 최소 응답수 필터
        min_resp_period1 = filters.get('min_responses_period1', filters.get('min_responses', 5))
        min_resp_period2 = filters.get('min_responses_period2', filters.get('min_responses', 5))
        
        result = result[
            (result['기준기간_응답수'] >= min_resp_period1) & 
            (result['비교기간_응답수'] >= min_resp_period2)
        ]
        
        # 정렬
        if trend == 'decrease':
            result = result.sort_values('NPS증감_value', ascending=True)
        elif trend == 'increase':
            result = result.sort_values('NPS증감_value', ascending=False)
        else:
            result = result.sort_values('NPS증감_value', key=abs, ascending=False)
        
        # 표시용 컬럼 선택 및 이름 변경
        result_display = result[['마케팅팀명', '대리점명', '매장명',
                                '기준기간_NPS', '기준기간_응답수',
                                '비교기간_NPS', '비교기간_응답수',
                                'NPS증감']].copy()
        
        result_display.columns = ['마케팅팀명', '대리점명', '매장명',
                                 f'{period1_label} NPS', f'{period1_label} 응답수',
                                 f'{period2_label} NPS', f'{period2_label} 응답수',
                                 'NPS 증감']
        
        return result_display.reset_index(drop=True)
    
    def _get_store_tcrew_detail(self, df_period1: pd.DataFrame, df_period2: pd.DataFrame,
                               result_tcrew: pd.DataFrame,
                               period1_label: str, period2_label: str) -> dict:
        """
        매장별 T크루 상세 정보 (Expander용)
        
        Args:
            df_period1: 기준 기간 데이터
            df_period2: 비교 기간 데이터
            result_tcrew: 조건 만족 T크루 목록
            period1_label: 기준 기간 레이블
            period2_label: 비교 기간 레이블
            
        Returns:
            {매장명: T크루 DataFrame} 딕셔너리
        """
        # 조건 만족하는 T크루의 ID 목록
        satisfied_tcrew_ids = result_tcrew['담당자ID'].tolist()
        
        # 해당 T크루들의 데이터만 필터링
        df1_satisfied = df_period1[df_period1['담당자ID'].isin(satisfied_tcrew_ids)]
        df2_satisfied = df_period2[df_period2['담당자ID'].isin(satisfied_tcrew_ids)]
        
        if len(df1_satisfied) == 0 or len(df2_satisfied) == 0:
            return {}
        
        # 매장별 전체 응답수 계산 (기간2 기준)
        store_total = df2_satisfied.groupby('매장명')['추천지수'].count().to_dict()
        
        # 매장별 평균 NPS 증감 계산
        store_nps_change = {}
        for store_name in df1_satisfied['매장명'].unique():
            store1 = df1_satisfied[df1_satisfied['매장명'] == store_name]
            store2 = df2_satisfied[df2_satisfied['매장명'] == store_name]
            
            if len(store1) > 0 and len(store2) > 0:
                nps1 = self._calculate_nps(store1['추천지수'])
                nps2 = self._calculate_nps(store2['추천지수'])
                store_nps_change[store_name] = nps2 - nps1
        
        # 매장-T크루별 집계
        tcrew_detail_list = []
        
        for store_name in df1_satisfied['매장명'].unique():
            store1_tcrews = df1_satisfied[df1_satisfied['매장명'] == store_name].groupby(['담당자', '담당자ID'])
            store2_tcrews = df2_satisfied[df2_satisfied['매장명'] == store_name].groupby(['담당자', '담당자ID'])
            
            # 기간1 T크루별 NPS
            period1_nps = {}
            for (tcrew_name, tcrew_id), group in store1_tcrews:
                period1_nps[(tcrew_name, tcrew_id)] = self._calculate_nps(group['추천지수'])
            
            # 기간2 T크루별 집계
            for (tcrew_name, tcrew_id), group in store2_tcrews:
                if (tcrew_name, tcrew_id) not in period1_nps:
                    continue
                
                nps2 = self._calculate_nps(group['추천지수'])
                nps1 = period1_nps[(tcrew_name, tcrew_id)]
                nps_change = nps2 - nps1
                
                total_responses = len(group)
                ratio = (total_responses / store_total[store_name] * 100) if store_name in store_total else 0
                
                # 매장 평균 대비 차이
                vs_store = nps_change - store_nps_change.get(store_name, 0)
                
                # 상태 표시 (색상 볼)
                if vs_store >= 5:
                    status = '🟢 우수'
                elif vs_store >= 0:
                    status = '🟢 양호'
                elif vs_store >= -5:
                    status = '🟠 주의'
                else:
                    status = '🔴 개선필요'
                
                tcrew_detail_list.append({
                    '매장명': store_name,
                    'T크루명': tcrew_name,
                    'NPS증감': round(nps_change, 1),
                    '응답수': total_responses,
                    '비중(%)': round(ratio, 1),
                    'vs매장': round(vs_store, 1),
                    '상태': status
                })
        
        tcrew_detail = pd.DataFrame(tcrew_detail_list)
        
        # 매장별로 딕셔너리 생성
        result = {}
        for store_name in tcrew_detail['매장명'].unique():
            store_df = tcrew_detail[tcrew_detail['매장명'] == store_name].copy()
            
            # NPS 증감 낮은 순으로 정렬 (문제 있는 T크루가 위로)
            store_df = store_df.sort_values('NPS증감', ascending=True)
            
            # 필요한 컬럼만
            store_df = store_df[['T크루명', 'NPS증감', '응답수', '비중(%)', 'vs매장', '상태']]
            
            result[store_name] = store_df.reset_index(drop=True)
        
        return result