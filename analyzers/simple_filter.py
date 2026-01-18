
"""
단순 필터링 분석기
NPS, 응답수 등 기본 조건만 있는 단순 필터링 질문 처리
예: "NPS 87% 미만인 곳은?", "2026년 1월 NPS 낮은 곳은?"
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

class SimpleFilterAnalyzer:
    """단순 필터 조건만 있는 질문 분석"""
    
    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: NPS 원본 데이터
        """
        self.df = df
    
    def analyze(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        단순 필터 조건으로 분석
        
        Args:
            filters: 필터 조건 딕셔너리
            
        Returns:
            분석 결과 (담당자별 + 매장별 + 매장-담당자 상세)
        """
        # 담당자별 분석
        result_tcrew, nps_values = self._analyze_by_tcrew(filters)
        
        # 매장별 분석
        result_store = self._analyze_by_store(filters)
        
        # 매장별 담당자 상세 (Expander용)
        store_tcrew_detail = self._get_store_tcrew_detail(filters)
        
        # 요약 정보
        nps_avg = nps_values.mean() if len(nps_values) > 0 else 0
        summary = {
            '담당자 수': len(result_tcrew),
            '매장 수': len(result_store),
            '평균 NPS': f"{nps_avg:.1f}%" if len(result_tcrew) > 0 else "N/A"
        }
        
        return {
            'by_tcrew': result_tcrew,
            'by_store': result_store,
            'store_tcrew_detail': store_tcrew_detail,
            'summary': summary,
            'insights': self._generate_insights(result_tcrew, result_store, filters, nps_values)
        }
    
    def _analyze_by_tcrew(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """담당자별 단순 필터 분석"""
        df = self.df.copy()
        
        # NPS 계산 (점수별 카운트)
        df['추천고객'] = (df['추천지수'] >= 9).astype(int)
        df['중립고객'] = ((df['추천지수'] >= 7) & (df['추천지수'] <= 8)).astype(int)
        df['비추천고객'] = (df['추천지수'] <= 6).astype(int)
        
        # 담당자별 집계 (팀, 대리점, 매장 포함)
        grouped = df.groupby(['마케팅팀명', '대리점명', '매장명', '담당자']).agg({
            '추천지수': 'count',
            '추천고객': 'sum',
            '비추천고객': 'sum'
        }).reset_index()
        
        grouped.columns = ['마케팅팀명', '대리점명', '매장명', '담당자', '응답수', '추천고객', '비추천고객']
        
        # NPS 계산
        grouped['NPS_value'] = ((grouped['추천고객'] - grouped['비추천고객']) / grouped['응답수'] * 100).round(1)
        grouped['NPS(%)'] = grouped['NPS_value'].apply(lambda x: f"{x}%")
        
        # 매장별 전체 응답수 계산 (비중 계산용)
        store_total = df.groupby(['마케팅팀명', '대리점명', '매장명'])['추천지수'].count().to_dict()
        
        # 매장내 모수 비중(%) 계산
        grouped['매장내_모수_비중_value'] = grouped.apply(
            lambda row: round(row['응답수'] / store_total.get((row['마케팅팀명'], row['대리점명'], row['매장명']), row['응답수']) * 100, 1),
            axis=1
        )
        grouped['매장내 모수 비중(%)'] = grouped['매장내_모수_비중_value'].apply(lambda x: f"{x}%")
        
        # 최소 응답수 필터
        min_responses = filters.get('min_responses_period1', 5)
        grouped = grouped[grouped['응답수'] >= min_responses]
        
        # NPS 목표 필터 적용 (NPS_value로 비교)
        if filters.get('nps_target') is not None:
            nps_target = filters['nps_target']
            comparison = filters.get('nps_comparison', 'below')
            
            if comparison == 'below':
                grouped = grouped[grouped['NPS_value'] < nps_target]
            elif comparison == 'above':
                grouped = grouped[grouped['NPS_value'] >= nps_target]
        
        # 정렬: 팀 → 대리점 → 매장 → NPS (숫자값 기준)
        grouped = grouped.sort_values(
            ['마케팅팀명', '대리점명', '매장명', 'NPS_value'],
            ascending=[True, True, True, True]
        ).reset_index(drop=True)
        
        # 화면 표시용 컬럼만 선택
        result = grouped[['마케팅팀명', '대리점명', '매장명', '담당자', 'NPS(%)', '응답수', '매장내 모수 비중(%)']].copy()
        
        # NPS_value는 별도로 반환 (summary/insights용)
        nps_values = grouped['NPS_value'].values
        
        return result, nps_values
    
    def _analyze_by_store(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """매장별 단순 필터 분석"""
        df = self.df.copy()
        
        # NPS 계산
        df['추천고객'] = (df['추천지수'] >= 9).astype(int)
        df['비추천고객'] = (df['추천지수'] <= 6).astype(int)
        
        # 매장별 집계 (팀 → 대리점 → 매장 순)
        grouped = df.groupby(['마케팅팀명', '대리점명', '매장명']).agg({
            '추천지수': 'count',
            '추천고객': 'sum',
            '비추천고객': 'sum'
        }).reset_index()
        
        grouped.columns = ['마케팅팀명', '대리점명', '매장명', '응답수', '추천고객', '비추천고객']
        
        # NPS 계산
        grouped['NPS_value'] = ((grouped['추천고객'] - grouped['비추천고객']) / grouped['응답수'] * 100).round(1)
        grouped['NPS(%)'] = grouped['NPS_value'].apply(lambda x: f"{x}%")
        
        # 최소 응답수 필터
        min_responses = filters.get('min_responses_period1', 5)
        grouped = grouped[grouped['응답수'] >= min_responses]
        
        # NPS 목표 필터 적용 (NPS_value로 비교)
        if filters.get('nps_target') is not None:
            nps_target = filters['nps_target']
            comparison = filters.get('nps_comparison', 'below')
            
            if comparison == 'below':
                grouped = grouped[grouped['NPS_value'] < nps_target]
            elif comparison == 'above':
                grouped = grouped[grouped['NPS_value'] >= nps_target]
        
        # 정렬: 팀 → 대리점 → 매장 → NPS (숫자값 기준)
        grouped = grouped.sort_values(
            ['마케팅팀명', '대리점명', '매장명', 'NPS_value'],
            ascending=[True, True, True, True]
        ).reset_index(drop=True)
        
        # 필요한 컬럼 선택 (추천수, 비추천수 추가)
        result = grouped[['마케팅팀명', '대리점명', '매장명', 'NPS(%)', '응답수', '추천고객', '비추천고객']].copy()
        
        # 컬럼명 변경
        result.columns = ['마케팅팀명', '대리점명', '매장명', 'NPS(%)', '응답수', '추천수', '비추천수']
        
        return result
    
    def _get_store_tcrew_detail(self, filters: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """
        매장별 담당자 상세 정보 (Expander용)
        
        Returns:
            {매장명: 담당자 DataFrame}
        """
        df = self.df.copy()
        
        # NPS 계산
        df['추천고객'] = (df['추천지수'] >= 9).astype(int)
        df['비추천고객'] = (df['추천지수'] <= 6).astype(int)
        
        # 매장별 전체 응답수 계산 (비중 계산용)
        store_total = df.groupby('매장명')['추천지수'].count().to_dict()
        
        # 매장별 평균 NPS 계산 (vs 비교용)
        store_nps = df.groupby('매장명').apply(
            lambda x: ((x['추천고객'].sum() - x['비추천고객'].sum()) / len(x) * 100)
        ).to_dict()
        
        # 매장-담당자별 집계
        grouped = df.groupby(['매장명', '담당자']).agg({
            '추천지수': 'count',
            '추천고객': 'sum',
            '비추천고객': 'sum'
        }).reset_index()
        
        grouped.columns = ['매장명', '담당자', '응답수', '추천고객', '비추천고객']
        
        # NPS 계산
        grouped['NPS_value'] = ((grouped['추천고객'] - grouped['비추천고객']) / grouped['응답수'] * 100).round(1)
        grouped['NPS(%)'] = grouped['NPS_value'].apply(lambda x: f"{x}%")
        
        # 비중 계산
        grouped['매장내_모수_비중_value'] = grouped.apply(
            lambda row: round(row['응답수'] / store_total[row['매장명']] * 100, 1),
            axis=1
        )
        grouped['매장내 모수 비중(%)'] = grouped['매장내_모수_비중_value'].apply(lambda x: f"{x}%")
        
        # 매장 평균 대비 차이
        grouped['vs매장_value'] = grouped.apply(
            lambda row: row['NPS_value'] - store_nps[row['매장명']],
            axis=1
        ).round(1)
        
        # 상태 표시 (색상 볼) - vs매장_value(숫자)로 판단
        def get_status(diff):
            if diff >= 5:
                return '🟢 우수'
            elif diff >= 0:
                return '🟢 양호'
            elif diff >= -5:
                return '🟠 주의'
            else:
                return '🔴 개선필요'
        
        grouped['상태'] = grouped['vs매장_value'].apply(get_status)
        
        # 표시용으로 % 추가 (상태 계산 이후)
        grouped['vs매장'] = grouped['vs매장_value'].apply(lambda x: f"{x}%")
        
        # 매장별로 딕셔너리 생성
        result = {}
        for store_name in grouped['매장명'].unique():
            store_df = grouped[grouped['매장명'] == store_name].copy()
            
            # NPS 낮은 순으로 정렬 (문제 있는 담당자가 위로)
            store_df = store_df.sort_values('NPS_value', ascending=True)
            
            # 필요한 컬럼만 (NPS_value는 정렬용으로 이미 사용했으므로 제거)
            store_df = store_df[['담당자', 'NPS(%)', '응답수', '매장내 모수 비중(%)', 'vs매장', '상태']]
            
            result[store_name] = store_df.reset_index(drop=True)
        
        return result
    
    def _generate_insights(self, result_tcrew: pd.DataFrame, result_store: pd.DataFrame, 
                          filters: Dict[str, Any], nps_values) -> list:
        """인사이트 생성"""
        insights = []
        
        if len(result_tcrew) > 0:
            # 최저 NPS 담당자 (NPS 기준으로 실제 최저값 찾기)
            result_tcrew_temp = result_tcrew.copy()
            result_tcrew_temp['NPS_numeric'] = result_tcrew_temp['NPS(%)'].str.rstrip('%').astype(float)
            
            # 최저 NPS값 찾기
            min_nps = result_tcrew_temp['NPS_numeric'].min()
            
            # 최저 NPS와 같은 값을 가진 모든 T크루 찾기
            worst_tcrews = result_tcrew_temp[result_tcrew_temp['NPS_numeric'] == min_nps]
            
            if len(worst_tcrews) == 1:
                # 동점자 없음 - 1명만 표시
                worst_tcrew = worst_tcrews.iloc[0]
                insights.append(
                    f"📌 {worst_tcrew['담당자']} ({worst_tcrew['매장명']})의 NPS가 "
                    f"{worst_tcrew['NPS(%)']}로 가장 낮습니다."
                )
            else:
                # 동점자 있음 - 첫 번째 + 나머지 인원수 표시
                worst_tcrew = worst_tcrews.iloc[0]
                others_count = len(worst_tcrews) - 1
                insights.append(
                    f"📌 {worst_tcrew['담당자']} ({worst_tcrew['매장명']}) "
                    f"외 {others_count}명의 NPS가 {worst_tcrew['NPS(%)']}로 가장 낮습니다."
                )
            
            # NPS 범위
            if len(nps_values) > 0:
                nps_min = nps_values.min()
                nps_max = nps_values.max()
                insights.append(f"📊 NPS 범위: {nps_min}% ~ {nps_max}% (편차 {nps_max - nps_min}%p)")
        
        if len(result_store) > 0:
            # 최저 NPS 매장 (NPS 기준으로 실제 최저값 찾기)
            result_store_temp = result_store.copy()
            result_store_temp['NPS_numeric'] = result_store_temp['NPS(%)'].str.rstrip('%').astype(float)
            
            # 최저 NPS값 찾기
            min_nps = result_store_temp['NPS_numeric'].min()
            
            # 최저 NPS와 같은 값을 가진 모든 매장 찾기
            worst_stores = result_store_temp[result_store_temp['NPS_numeric'] == min_nps]
            
            if len(worst_stores) == 1:
                # 동점 매장 없음 - 1개만 표시
                worst_store = worst_stores.iloc[0]
                insights.append(
                    f"🏪 {worst_store['매장명']}의 NPS가 "
                    f"{worst_store['NPS(%)']}로 가장 낮습니다."
                )
            else:
                # 동점 매장 있음 - 첫 번째 + 나머지 개수 표시
                worst_store = worst_stores.iloc[0]
                others_count = len(worst_stores) - 1
                insights.append(
                    f"🏪 {worst_store['매장명']} "
                    f"외 {others_count}개 매장의 NPS가 {worst_store['NPS(%)']}로 가장 낮습니다."
                )
        
        return insights