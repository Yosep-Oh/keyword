import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [1] 페이지 설정 및 스타일 (UI 강화) ---
# 원본의 블루 톤을 포인트로 사용합니다.
st.set_page_config(layout="wide", page_title="오셀러 마켓 리포트", page_icon="📈")

# 원본의 디자인 요소를 모방한 커스텀 CSS
# 글꼴 크기, 색상, 여백 등을 미세하게 조정했습니다.
st.markdown("""
    <style>
    /* 기본 배경색과 서체 */
    .main { background-color: #fcfcfc; font-family: 'Malgun Gothic', sans-serif; }
    
    /* 제목 및 헤더 스타일 */
    .stHeader { color: #202020; font-weight: 800; }
    
    /* 상품명 스타일 */
    .p_name_label { 
        font-size: 1.1rem !important; 
        font-weight: 600 !important; 
        color: #202020 !important;
        margin-bottom: 0px;
    }

    /* 원본의 메트릭 카드 느낌을 살린 스타일 */
    [data-testid="stMetricValue"] { 
        font-size: 1.6rem !important; 
        color: #3867d6 !important; /* 포인트 블루 색상 */
        font-weight: 700 !important;
    }
    
    /* 드롭다운 스타일 */
    .stSelectbox label { font-size: 1rem; font-weight: 600; color: #404040; }
    
    /* AgGrid 테마 커스텀 (헤더 색상 등) */
    .ag-theme-alpine .ag-header {
        background-color: #f7f9fc;
        color: #606060;
        font-weight: 600;
    }
    .ag-theme-alpine .ag-cell { color: #303030; }

    /* 로딩바 색상 커스텀 */
    div[st-metric-id="검색량"] [data-testid="stLineChart"] path {
        stroke: #3867d6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [2] 보안 접속 (비밀번호) ---
# 기존 비밀번호 기능을 유지합니다.
MY_PASSWORD = "yosep1234" 

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 보안 접속")
    pwd_input = st.text_input("비밀번호", type="password")
    if st.button("데이터 분석 시작", use_container_width=True):
        if pwd_input == MY_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop() 

# --- [3] 수파베이스 데이터 로드 (금고 정보 필수) ---
# 사장님이 Advanced settings에 주소와 키를 이미 넣어두셨다고 가정합니다.
# 만약 TypeError가 나면 금고 정보를 다시 확인해 주세요.
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def clean_to_int(val):
    if pd.isna(val) or val == "": return 0
    # 특수문자 제거 로직 강화
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').strip()
    try:
        # '만' 단위 처리
        if '만' in s:
            num = float(s.replace('만', '')) * 10000
        else:
            num = float(s)
        return int(round(num))
    except: return 0

@st.cache_data(ttl=600) # 10분간 캐시 유지
def load_all_data():
    all_rows = []
    step = 1000  # 무료 버전 안전장치
    offset = 0
    while True:
        res = supabase.table("market_analysis").select("*").range(offset, offset + step - 1).execute()
        if not res.data: break
        all_rows.extend(res.data)
        if len(res.data) < step: break
        offset += step
    
    df = pd.DataFrame(all_rows)
    if not df.empty:
        # 데이터 정제 및 앞뒤 공백 제거
        for col in ['main_keyword', 'product_name', 'sub_keyword']:
            df[col] = df[col].astype(str).str.strip()
        
        # 숫자 변환
        df['검색량_숫자'] = df['keyword_vol'].apply(clean_to_int)
        df['노출수'] = df['keyword_exposure'].apply(clean_to_int)
        df['클릭수'] = df['keyword_clicks'].apply(clean_to_int)
        df['평균가'] = df['avg_price'].apply(clean_to_int)
    return df

# --- [4] 메인 대시보드 ---
try:
    df = load_all_data()
    
    if not df.empty:
        # 사이드바 설정 (필터)
        st.sidebar.header("📊 분석 필터")
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🎯 메인 키워드", main_list)
        
        # 메인 키워드로 1차 필터링
        view_df = df[df['main_keyword'] == target]
        
        # 상단 상품 선택 UI
        products = sorted(view_df['product_name'].unique())
        selected_product = st.selectbox("🔎 분석할 상품명을 선택하세요", ["--- 상품 선택 ---"] + products)
        
        # 상품 이미지 없더라도 헤더를 풍성하게 구성
        # 1. 원본의 'Top 10 검색어 보기' 스타일로 링크 텍스트 추가
        col1, col2 = st.columns([8, 2])
        with col1:
            st.title(f"🚀 '{target}' 마켓 리포트")
        with col2:
            st.markdown("<br><br><a href='#' style='color: #3867d6; font-size: 0.9rem; text-decoration: none;'>원본 페이지 보기 ></a>", unsafe_allow_html=True)
        
        st.divider()

        if selected_product != "--- 상품 선택 ---":
            # 해당 상품의 상세 데이터만 추출
            sub_data = view_df[view_df['product_name'] == selected_product].copy()
            
            # 상품 정보 요약 카드 (원본의 느낌을 살림)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 연관 키워드", f"{len(sub_data)}개")
            with col2:
                top_vol = sub_data['검색량_숫자'].max()
                st.metric("최고 검색량", f"{top_vol:,}")
            with col3:
                # 0원 데이터 제외 평균 시장가 계산
                actual_prices = sub_data[sub_data['평균가'] > 0]['평균가']
                avg_p = int(actual_prices.mean()) if not actual_prices.empty else 0
                st.metric("평균 시장가", f"₩{avg_p:,}")
            
            st.divider()
            
            # 상품 상세 분석 영역
            st.subheader(f"📍 {selected_product}")
            
            if not sub_data.empty:
                # 필요한 컬럼만 깔끔하게 정렬하여 추출 (원본과 동일 순서)
                # 'keyword_vol' 원문 대신 '검색량_숫자'만 사용
                display_df = sub_data[['sub_keyword', '검색량_숫자', '노출수', '클릭수', '평균가']]
                
                # AgGrid 설정 빌더
                gb = GridOptionsBuilder.from_dataframe(display_df)
                
                # 컬럼 헤더 및 포맷 설정 (원본과 동일하게)
                # 1. '연관 키워드'를 맨 왼쪽에 고정
                gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left', width=170)
                
                # 2. '검색량' (숫자형, 천 단위 콤마)
                gb.configure_column("검색량_숫자", headerName="검색량", type=["numericColumn"], sort="desc", valueFormatter="x.toLocaleString()")
                
                # 3. '노출수', '클릭수' (천 단위 콤마)
                gb.configure_column("노출수", headerName="노출수", valueFormatter="x.toLocaleString()")
                gb.configure_column("클릭수", headerName="클릭수", valueFormatter="x.toLocaleString()")
                
                # 4. '평균단가' (₩ 표시와 천 단위 콤마)
                gb.configure_column("평균가", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
                
                # 모바일 대응을 위한 설정 (자동 너비 조절)
                grid_options = gb.build()
                
                # 표 그리기
                AgGrid(
                    display_df, 
                    gridOptions=grid_options, 
                    theme='alpine', # 세련된 테마
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                    height=500
                )
            else:
                st.warning("⚠️ 해당 상품에 대한 상세 키워드 데이터가 DB에 없습니다. 다시 업로드해 주세요.")
        else:
            # 상품 선택 전, 원본 이미지 느낌을 주는 빈 카드 표시
            st.info("개별 상품을 선택하시면 상세 표가 나타납니다.")
            # col1, col2, col3 = st.columns(3)
            # col1.markdown("<div style='background-color: #f7f9fc; height: 100px; border-radius: 8px;'></div>", unsafe_allow_html=True)
            # col2.markdown("<div style='background-color: #f7f9fc; height: 100px; border-radius: 8px;'></div>", unsafe_allow_html=True)
            # col3.markdown("<div style='background-color: #f7f9fc; height: 100px; border-radius: 8px;'></div>", unsafe_allow_html=True)
            # st.markdown("<br><div style='background-color: #f7f9fc; height: 400px; border-radius: 8px;'></div>", unsafe_allow_html=True)

    else:
        st.warning("표시할 데이터가 없습니다. upload.py를 실행해 주세요.")

except Exception as e:
    st.error(f"⚠️ 시스템 오류 발생: {e}")

# --- ---
st.markdown("---")
st.caption("© 2026 오셀러 마켓 리포트 v1.3.0 | 본 서비스는 사장님 전용입니다.")
