"""
Google Sheets 데이터 연결 모듈
기존 NPS 시그널 리포트와 동일한 데이터 소스 사용
"""

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
import gspread

class NPSDataConnector:
    """NPS RAW DATA 연결 클래스"""
    
    def __init__(self):
        """Google Sheets 연결 초기화"""
        try:
            # Streamlit secrets에서 인증 정보 로드
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["google_service_account"],
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
            
            self.gc = gspread.authorize(credentials)
            self.sheet_url = st.secrets["google_sheets"]["sheet_url"]
            
        except Exception as e:
            st.error(f"Google Sheets 연결 실패: {str(e)}")
            self.gc = None
            self.sheet_url = None
    
    @st.cache_data(ttl=3600)  # 1시간 캐싱
    def load_raw_data(_self):
        """
        Google Sheets에서 RAW DATA 로드
        
        Returns:
            pd.DataFrame: NPS RAW DATA
        """
        if _self.gc is None:
            st.error("Google Sheets 연결이 초기화되지 않았습니다.")
            return None
        
        try:
            with st.spinner("📊 데이터 로드 중..."):
                # Google Sheets 열기
                sheet = _self.gc.open_by_url(_self.sheet_url)
                worksheet = sheet.get_worksheet(0)  # 첫 번째 시트
                
                # 데이터 가져오기
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)
                
                # 제외 데이터 필터링
                df = df[df['제외'] == 'N'].copy()
                
                # 날짜 변환
                df['처리일'] = pd.to_datetime(df['처리일'], format='%Y%m%d', errors='coerce')
                
                # 숫자 변환
                df['추천지수'] = pd.to_numeric(df['추천지수'], errors='coerce')
                
                st.success(f"✅ 데이터 로드 완료: {len(df):,}건")
                
                return df
                
        except Exception as e:
            st.error(f"데이터 로드 실패: {str(e)}")
            return None
    
    def get_data_summary(_self):
        """데이터 요약 정보"""
        df = _self.load_raw_data()
        
        if df is None:
            return None
        
        summary = {
            '총 데이터 수': len(df),
            '데이터 기간': f"{df['처리일'].min().strftime('%Y-%m-%d')} ~ {df['처리일'].max().strftime('%Y-%m-%d')}",
            '팀 수': df['마케팅팀명'].nunique(),
            '매장 수': df['매장명'].nunique(),
            'T크루 수': df['담당자ID'].nunique(),
            '평균 NPS': f"{(df['추천지수'] >= 9).sum() / len(df) * 100:.2f}%"
        }
        
        return summary
