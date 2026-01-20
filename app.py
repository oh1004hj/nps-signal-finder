"""
NPS Signal Finder
NPS 시그널 리포트 전에, 질문을 구조화해서 인사이트 후보를 빠르게 찾는 도구입니다.
"""

import streamlit as st
import pandas as pd
from data_connector import NPSDataConnector
from query_parser import QueryParser
from analyzers.senior_gap import SeniorGapAnalyzer
from analyzers.period_comparison import PeriodComparisonAnalyzer
from analyzers.simple_filter import SimpleFilterAnalyzer
from io import BytesIO

# 페이지 설정
st.set_page_config(
    page_title="NPS Signal Finder",
    page_icon="🔍",
    layout="wide"
)

# Session state 초기화
if 'question_input' not in st.session_state:
    st.session_state.question_input = ""
if 'auto_submit' not in st.session_state:
    st.session_state.auto_submit = False

# 타이틀
st.markdown(
    """
    <style>
    .signal-finder-title {
        font-size: 48px;
        font-weight: 800;
        color: #000000;               /* 글씨 자체는 순수 검정 */
        text-shadow:
            0 0 8px  #39FF14;,          /* 밝은 그린 네온 1단계 */
            0 0 16px #2EE59D,          /* 2단계 */
            0 0 28px #2EE59D,          /* 3단계 */
            0 0 40px rgba(46, 229, 157, 0.4);  /* 더 넓게 퍼지는 잔광 */
        letter-spacing: -0.5px;
        margin-bottom: 12px;
        text-align: center;
        -webkit-font-smoothing: antialiased; /* 글씨 선명도 향상 */
    }
    .subtitle {
        font-size: 20px;
        font-weight: 600;
        color: #111111;               /* 거의 검정 */
        margin-bottom: 2px;
    }
    .caption-text {
        font-size: 15px;
        color: #444444;               /* 어두운 회색 */
        font-weight: 400;
    }
    </style>

    <div class="signal-finder-title">NPS Signal Finder 🔍</div>
    """,
    unsafe_allow_html=True
)

st.markdown("##### NPS 시그널 리포트 전에")
st.caption("질문을 구조화해서 인사이트 후보를 빠르게 찾는 도구입니다.")

# 데이터 연결
@st.cache_resource
def get_connector():
    return NPSDataConnector()

@st.cache_resource
def get_parser():
    return QueryParser()

connector = get_connector()
parser = get_parser()

# 엑셀 변환 함수
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='분석결과')
    return output.getvalue()

# 데이터 자동 로드 함수
@st.cache_data(ttl=3600)
def load_initial_data():
    """앱 시작 시 데이터 자동 로드 (1시간 캐시)"""
    connector = get_connector()
    summary = connector.get_data_summary()
    return summary

# 앱 시작 시 자동으로 데이터 로드 (조용히 백그라운드에서)
if 'data_summary' not in st.session_state:
    st.session_state.data_summary = load_initial_data()

# 데이터 기간 정보 표시 (회색 텍스트)
if st.session_state.data_summary:
    data_period = st.session_state.data_summary.get('데이터 기간', 'N/A')
    total_count = st.session_state.data_summary.get('총 데이터 수', 'N/A')
    st.caption(f"데이터 기간: {data_period} (총 {total_count}건)")

# 사이드바 - 데이터 정보를 expander로 숨김
with st.sidebar:
    st.header("⚙️ 설정")
    
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.cache_resource.clear()
        if 'data_summary' in st.session_state:
            del st.session_state.data_summary
        st.rerun()
    
    # 데이터 상세 정보는 expander로 숨김
    with st.expander("📊 데이터 상세 정보"):
        if st.session_state.data_summary:
            for key, value in st.session_state.data_summary.items():
                st.metric(key, value)

# 메인 영역
st.markdown("---")

# 메인 영역 - 탭 제거, 질문하기만 표시
st.markdown("### 💭 질문을 입력하세요")
    
# 질문 입력 (session_state 연동)
# 버튼 클릭시 key를 바꿔서 완전히 새로운 text_area 생성
text_area_key = st.session_state.get('text_area_key', 'question_area_0')

question = st.text_area(
    "질문",
    value=st.session_state.question_input,
    placeholder="예: 시니어 비중이 높으면서 NPS가 낮은 T크루는? (필터 조건 ▶분석월)",
    height=100,
    label_visibility="collapsed",
    key=text_area_key
)

# 입력창 내용이 변경되면 session_state 업데이트 (버튼 클릭 직후는 제외)
if not st.session_state.get('auto_submit', False):
    if question != st.session_state.question_input:
        st.session_state.question_input = question

# 샘플 질문 버튼
col1, col2 = st.columns([3, 1])

with col2:
    manual_submit = st.button("🔍 분석 실행", type="primary", disabled=not question)

# 수동 실행 또는 자동 실행
if manual_submit or st.session_state.auto_submit:
    # 자동 실행 플래그 리셋
    if st.session_state.auto_submit:
        st.session_state.auto_submit = False
    
    if question:
        st.session_state.current_question = question

# 샘플 질문 제공
st.markdown("---")

# 4:6 레이아웃 (질문 예시 40%, 키워드 가이드 60%)
col_left, col_right = st.columns([2, 3])

with col_left:
    st.markdown("#### 💡 질문 예시")
    
    sample_questions = [
        "NPS가 낮은 T크루는? (필터 조건 ▶분석월)",
        "2일 누적 대비 5일 누적 NPS가 상승한 T크루는? (필터 조건 ▶분석월)",
        "12월 대비 1월 NPS가 하락한 T크루는? (필터 조건 ▶분석월: 전체)",
        "시니어 비중이 높으면서 NPS가 낮은 T크루는? (필터 조건 ▶분석월)"
    ]
    
    for i, q in enumerate(sample_questions):
        if st.button(f"💬 {q}", key=f"sample_{i}"):
            st.session_state.question_input = q
            # text_area key를 바꿔서 완전히 새로 생성
            import time
            st.session_state.text_area_key = f'question_area_{time.time()}'
            st.session_state.auto_submit = True
            st.session_state.current_question = q
            st.rerun()
    
    st.caption("💡 분석 결과 탭에서 T크루별/매장별 조회 가능")

with col_right:
    st.markdown("#### 📝 키워드 가이드")
    st.info("""
**▶ 교체 가능한 키워드**
- 🔴 낮은 ↔ 🔵 높은  
- 🔴 낮으면서 ↔ 🔵 높으면서
- 📉 하락 ↔ 📈 상승  
- ⬇️ 미만 ↔ ⬆️ 이상  

**▶ 기간 비교 표현**
- 12월 대비 1월  
- 2일 누적 대비 5일 누적

**▶ 시니어 분석 표현**
- 시니어 비중이 높으면서 NPS가 낮은

**▶ 기타 조건**
- 분석월/팀/ 대리점명/ 매장명 (필터에서 조정)
- 최소 응답수/ 결과 개수/ NPS목표값/ NPS기준 (필터에서 조정)  
    """)

# 질문 처리
if hasattr(st.session_state, 'current_question'):
    question = st.session_state.current_question
    
    st.markdown("---")
    
    with st.spinner("🔍 질문 분석 중..."):
        # 질문 파싱
        filters = parser.parse(question)
        
    # 추출된 필터 표시
    with st.expander("🎛️ 추출된 필터 조건", expanded=True):
        # 필터 수정 옵션 (Form 제거 - 실시간 필터링)
        st.markdown("##### 필터 조건")
        
        # 데이터 로드 (필터 옵션용)
        df_for_filter = connector.load_raw_data()
        
        # 분석월 옵션 생성 (데이터 기반 동적 생성)
        month_options = ["전체"]
        if df_for_filter is not None and '처리일' in df_for_filter.columns:
            # 처리일을 datetime으로 변환
            df_for_filter['처리일_dt'] = pd.to_datetime(df_for_filter['처리일'], format='%Y%m%d', errors='coerce')
            # 년월 추출 (YYYY년 MM월)
            df_for_filter['년월'] = df_for_filter['처리일_dt'].dt.strftime('%Y년 %m월')
            # 유니크한 년월 리스트 (정렬)
            unique_months = sorted(df_for_filter['년월'].dropna().unique().tolist())
            month_options.extend(unique_months)
        
        # 월 단위 기간 비교일 경우만 경고 메시지 (일 단위 비교는 제외)
        if filters.get('analysis_type') == 'period_comparison' and '일' not in question:
            st.warning("""
            ⚠️ **월 단위 기간 비교 분석 주의사항**
            - 기간 비교는 전체 기간 데이터가 필요합니다
            """)
        
        # 변수 초기화
        team = None
        dealer_name = None
        
        # 첫 번째 줄: 분석월
        # 분석월 선택 (기간 비교일 때 자동으로 "전체" 설정)
        month_index = 0
        
        if filters.get('analysis_type') == 'period_comparison':
            # 기간 비교: 자동으로 "전체" 선택 (변경은 가능)
            month_index = 0
        elif filters.get('analysis_month') and filters['analysis_month'] in month_options:
            # 일반 분석: 파싱된 분석월 사용
            month_index = month_options.index(filters['analysis_month'])
        
        analysis_month = st.selectbox("분석월", month_options, index=month_index, key="month_select")
        if analysis_month != "전체":
            filters['analysis_month'] = analysis_month
            # 분석월 필터 적용
            if df_for_filter is not None:
                df_for_filter = df_for_filter[df_for_filter['년월'] == analysis_month]
        else:
            filters['analysis_month'] = "전체"
        
        # 두 번째 줄: 팀, 대리점명, 매장명
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 팀 옵션을 데이터에서 동적으로 가져오기
            if df_for_filter is not None and '마케팅팀명' in df_for_filter.columns:
                team_options = ["전체"] + sorted(df_for_filter['마케팅팀명'].dropna().unique().tolist())
            else:
                team_options = ["전체", "인천마케팅팀", "남부마케팅팀", "강서마케팅팀"]
            
            team_index = 0
            if filters.get('team') and filters['team'] in team_options:
                team_index = team_options.index(filters['team'])
            
            team = st.selectbox("팀", team_options, index=team_index, key="team_select")
            if team != "전체":
                filters['team'] = team
            else:
                filters['team'] = None
        
        with col2:
            # 대리점명 필터 (팀 선택 시 해당 팀 소속만 표시)
            if df_for_filter is not None and '대리점명' in df_for_filter.columns:
                # 팀 필터 적용
                df_for_dealer = df_for_filter.copy()
                if team and team != "전체":
                    df_for_dealer = df_for_dealer[df_for_dealer['마케팅팀명'] == team]
                
                dealer_list = ["전체"] + sorted(df_for_dealer['대리점명'].dropna().unique().tolist())
                dealer_index = 0
                if filters.get('dealer_name') and filters['dealer_name'] in dealer_list:
                    dealer_index = dealer_list.index(filters['dealer_name'])
                
                dealer_name = st.selectbox("대리점명", dealer_list, index=dealer_index, key="dealer_select")
                if dealer_name != "전체":
                    filters['dealer_name'] = dealer_name
                else:
                    filters['dealer_name'] = None
            else:
                dealer_name = None
                filters['dealer_name'] = None
        
        with col3:
            # 매장명 필터 (팀, 대리점명 선택 시 해당 소속만 표시)
            if df_for_filter is not None and '매장명' in df_for_filter.columns:
                # 팀, 대리점명 필터 적용
                df_for_store = df_for_filter.copy()
                if team and team != "전체":
                    df_for_store = df_for_store[df_for_store['마케팅팀명'] == team]
                if dealer_name and dealer_name != "전체":
                    df_for_store = df_for_store[df_for_store['대리점명'] == dealer_name]
                
                store_list = ["전체"] + sorted(df_for_store['매장명'].dropna().unique().tolist())
                store_index = 0
                if filters.get('store_name') and filters['store_name'] in store_list:
                    store_index = store_list.index(filters['store_name'])
                
                store_name = st.selectbox("매장명", store_list, index=store_index, key="store_select")
                if store_name != "전체":
                    filters['store_name'] = store_name
                else:
                    filters['store_name'] = None
            else:
                filters['store_name'] = None
        
        # 두 번째 줄: 최소 응답수 (2개), 결과 개수
        col5, col6, col7 = st.columns(3)
        
        with col5:
            min_resp_period1 = st.number_input(
                "기준기간 최소 응답수",
                min_value=1,
                value=filters.get('min_responses_period1', 5),
                key="min_resp_period1_input",
                help="기간 비교 시: 기준기간(앞), 시니어 분석 시: 전체 기간"
            )
            filters['min_responses_period1'] = min_resp_period1
            filters['min_responses'] = min_resp_period1  # 하위 호환성
        
        with col6:
            min_resp_period2 = st.number_input(
                "비교기간 최소 응답수",
                min_value=1,
                value=filters.get('min_responses_period2', 5),
                key="min_resp_period2_input",
                help="기간 비교 시만 사용 (뒤 기간)"
            )
            filters['min_responses_period2'] = min_resp_period2
        
        with col7:
            top_n = st.slider("결과 개수", 5, 50, 20, key="top_n_slider")
        
        # 세 번째 줄: NPS 목표값
        col7, col8 = st.columns(2)
        
        with col7:
            nps_target = st.number_input(
                "NPS 목표값",
                min_value=-100,
                max_value=100,
                value=int(filters.get('nps_target', 87)) if filters.get('nps_target') else 87,
                key="nps_target_input"
            )
            filters['nps_target'] = nps_target
        
        with col8:
            nps_comp_options = {"목표 미달": "below", "목표 달성": "above"}
            nps_comp_default = filters.get('nps_comparison', 'below')
            
            nps_comparison = st.radio(
                "NPS 기준",
                list(nps_comp_options.keys()),
                index=0 if nps_comp_default == 'below' else 1,
                key="nps_comp_radio"
            )
            filters['nps_comparison'] = nps_comp_options[nps_comparison]
    
    # 실제 적용된 필터 조건 표시 (UI 필터 변경 후)
    st.markdown("---")
    
    # 월 단위 기간 비교일 때만 표시용으로 분석월을 "전체"로 강제 설정
    # (일 단위 비교는 특정 월이 필요하므로 제외)
    if filters.get('analysis_type') == 'period_comparison' and '일' not in question:
        filters['analysis_month'] = "전체"
    
    filter_summary = parser.get_filter_summary(filters)
    st.info(f"**✅ 적용된 분석 조건:** {filter_summary}")
    
    # comparison_periods 재계산 (analysis_month가 UI에서 설정된 후)
    if filters.get('analysis_month'):
        # query_parser에서 다시 비교 기간 추출
        comparison_periods = parser._extract_comparison_periods(question, filters['analysis_month'])
        if comparison_periods:
            filters['comparison_periods'] = comparison_periods
                    
    # 분석 실행 (실시간 필터 적용)
    with st.spinner("📊 데이터 분석 중..."):
        # 캐시된 데이터 사용
        df, _ = load_data_once()
        
        if df is not None:
            # 물리적 데이터 필터링 (분석월, 팀, 대리점명, 매장명)
            df_for_analysis = df.copy()
            
            # 분석월 필터
            if filters.get('analysis_month') and filters['analysis_month'] != "전체":
                analysis_month = filters['analysis_month']
                df_for_analysis['처리일_dt'] = pd.to_datetime(df_for_analysis['처리일'], format='%Y%m%d', errors='coerce')
                df_for_analysis['년월'] = df_for_analysis['처리일_dt'].dt.strftime('%Y년 %m월')
                df_for_analysis = df_for_analysis[df_for_analysis['년월'] == analysis_month]
                df_for_analysis = df_for_analysis.drop(columns=['처리일_dt', '년월'])
            
            # 팀 필터
            if filters.get('team'):
                df_for_analysis = df_for_analysis[df_for_analysis['마케팅팀명'] == filters['team']]
            
            # 대리점명 필터
            if filters.get('dealer_name'):
                df_for_analysis = df_for_analysis[df_for_analysis['대리점명'] == filters['dealer_name']]
            
            # 매장 필터
            if filters.get('store_name'):
                df_for_analysis = df_for_analysis[df_for_analysis['매장명'] == filters['store_name']]
            
            # 분석 유형에 따라 적절한 분석기 선택
            analysis_type = filters['analysis_type']
            
            if analysis_type == 'simple_filter':
                # 단순 필터 분석
                analyzer = SimpleFilterAnalyzer(df_for_analysis)
                result = analyzer.analyze(filters)
                
            elif analysis_type == 'senior_gap':
                # 시니어 GAP 분석
                analyzer = SeniorGapAnalyzer(df_for_analysis)
                result = analyzer.analyze(filters)
                
            elif analysis_type == 'period_comparison':
                # 기간별 비교 분석
                analyzer = PeriodComparisonAnalyzer(df_for_analysis)
                result = analyzer.analyze(filters)
                
            elif analysis_type == 'store_analysis':
                # 매장별 분석 (미구현)
                st.warning("⚠️ **매장별 상세 분석은 다음 버전에서 지원 예정입니다!**")
                st.info("현재는 **시니어 GAP 분석**과 **단순 필터 분석**만 지원됩니다. 질문을 다시 입력해주세요.")
                result = None
                
            else:
                # 일반 분석 - 시니어 관련 질문이 아닌 경우
                st.warning("⚠️ **질문 유형을 인식할 수 없습니다.**")
                st.info("""
                지원되는 질문 예시:
                - "NPS 87% 미만인 곳은?"
                - "시니어 비중이 높으면서 NPS가 낮은 T크루는? (필터 조건 ▶분석월)"
                - "12월 대비 1월 NPS 상승한 곳은?"
                """)
                result = None
            
            # 결과 표시 (result가 None이 아닐 때만)
            if result is not None:
                st.markdown("---")
                
                # Chat 형태로 결과 표시
                with st.chat_message("assistant"):
                    st.success("✅ 분석 완료!")
                    
                    # 요약 정보
                    with st.expander("📋 분석 요약", expanded=True):
                        cols = st.columns(len(result['summary']))
                        for i, (key, value) in enumerate(result['summary'].items()):
                            cols[i].metric(key, value)
                    
                    # 결과 테이블 - 탭으로 T크루별 / 매장별 구분
                    with st.expander("📊 분석 결과", expanded=True):
                        tab1, tab2 = st.tabs(["👤 T크루별", "🏪 매장별"])
                        
                        # T크루별 탭
                        with tab1:
                            if 'by_tcrew' in result and len(result['by_tcrew']) > 0:
                                # 상위 N개만 표시
                                display_data = result['by_tcrew'].head(top_n)
                                
                                st.dataframe(
                                    display_data,
                                    use_container_width=True,
                                    hide_index=True
                                )
                                
                                st.caption(f"전체 {len(result['by_tcrew'])}명 중 상위 {len(display_data)}명 표시")
                                
                                # 다운로드 버튼
                                excel_data = to_excel(result['by_tcrew'])
                                st.download_button(
                                    "📥 T크루별 전체 결과 엑셀 다운로드",
                                    data=excel_data,
                                    file_name=f"nps_tcrew_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="download_tcrew"
                                )
                            else:
                                st.warning("조건을 만족하는 T크루가 없습니다.")
                        
                        # 매장별 탭
                        with tab2:
                            if 'by_store' in result and len(result['by_store']) > 0:
                                # 분석 유형에 따라 다른 표시
                                if analysis_type == 'period_comparison':
                                    # 기간 비교: 데이터프레임으로 표시
                                    st.dataframe(
                                        result['by_store'].head(top_n),
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                    st.caption(f"전체 {len(result['by_store'])}개 매장 중 상위 {min(top_n, len(result['by_store']))}개 표시")
                                else:
                                    # 단순 필터 등: 매장별 리스트 + Expander 표시
                                    for idx, row in result['by_store'].head(top_n).iterrows():
                                        col1, col2 = st.columns([3, 7])
                                        
                                        with col1:
                                            # 매장 정보
                                            st.markdown(f"### 🏪 {row['매장명']} ({row['대리점명']})")
                                            
                                            # simple_filter는 2개, senior_gap은 4개 metric 표시
                                            if analysis_type == 'simple_filter':
                                                metric_cols = st.columns(2)
                                                with metric_cols[0]:
                                                    st.metric("NPS", row['NPS(%)'])
                                                with metric_cols[1]:
                                                    st.metric("응답수", f"{row['응답수']}건")
                                            else:
                                                metric_cols = st.columns(4)
                                                with metric_cols[0]:
                                                    st.metric("NPS", row['NPS(%)'])
                                                with metric_cols[1]:
                                                    st.metric("응답수", f"{row['응답수']}건")
                                                with metric_cols[2]:
                                                    st.metric("시니어비중", row['시니어비중(%)'])
                                                with metric_cols[3]:
                                                    st.metric("시니어NPS", row['시니어NPS(%)'])
                                        
                                        with col2:
                                            # 매장별 T크루 상세 (Container로 변경)
                                            store_name = row['매장명']
                                            if store_name in result.get('store_tcrew_detail', {}):
                                                store_tcrew_df = result['store_tcrew_detail'][store_name]
                                                
                                                # 작은 컨테이너로 표시
                                                with st.container():
                                                    st.caption("👤 **T크루 상세**")
                                                    st.caption(f"매장 전체 응답: {int(row['응답수'])}건")
                                                    
                                                    st.dataframe(
                                                        store_tcrew_df,
                                                        use_container_width=True,
                                                        hide_index=True,
                                                        height=200
                                                    )
                                        
                                        st.markdown("---")
                                    
                                    st.caption(f"전체 {len(result['by_store'])}개 매장 중 상위 {min(top_n, len(result['by_store']))}개 표시")
                                
                                # 다운로드 버튼
                                excel_data = to_excel(result['by_store'])
                                st.download_button(
                                    "📥 매장별 전체 결과 엑셀 다운로드",
                                    data=excel_data,
                                    file_name=f"nps_store_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="download_store"
                                )
                            else:
                                st.warning("조건을 만족하는 매장이 없습니다.")
                    
                    # 인사이트
                    with st.expander("💡 핵심 인사이트", expanded=True):
                        for insight in result['insights']:
                            st.markdown(f"- {insight}")
                
                st.session_state.analysis_done = True


# 푸터
st.markdown("---")
st.caption("💡 Tip: 위 예시와 유사한 표현으로 질문하면 분석 정확도가 높아집니다.")