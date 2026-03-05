import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [1] UI 및 페이지 설정 ---
st.set_page_config(layout="wide", page_title="오셀러 쿠팡 분석기")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #eb4d4b !important; }
    .stSelectbox label { font-size: 1.1rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- [2] 보안 접속 ---
MY_PASSWORD = "141242" 
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 오셀러 전용 보안 채널")
    pwd_input = st.text_input("비밀번호", type="password")
    if st.button("접속하기", use_container_width=True):
        if pwd_input == MY_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- [3] 데이터 로드 및 정제 ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def clean_to_int(val):
    if pd.isna(val) or val == "": return 0
    # 모든 특수문자 제거 로직 강화 (단가 ₩0 해결용)
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').replace(' ', '').strip()
    try:
        if '만' in s:
            num = float(s.replace('만', '')) * 10000
        else:
            num = float(s)
        return int(round(num))
    except: return 0

@st.cache_data(ttl=600)
def load_all_data():
    all_rows = []
    step = 1000
    offset = 0
    while True:
        res = supabase.table("market_analysis").select("*").range(offset, offset + step - 1).execute()
        if not res.data: break
        all_rows.extend(res.data)
        if len(res.data) < step: break
        offset += step
    
    df = pd.DataFrame(all_rows)
    if not df.empty:
        # 중복 데이터 제거 (2개씩 뜨는 문제 해결 핵심!)
        df = df.drop_duplicates(subset=['main_keyword', 'product_name', 'sub_keyword'])
        
        for col in ['main_keyword', 'product_name', 'sub_keyword']:
            df[col] = df[col].astype(str).str.strip()
        
        df['검색량_숫자'] = df['keyword_vol'].apply(clean_to_int)
        df['노출수'] = df['keyword_exposure'].apply(clean_to_int)
        df['클릭수'] = df['keyword_clicks'].apply(clean_to_int)
        df['평균가'] = df['avg_price'].apply(clean_to_int)
    return df

# --- [4] 메인 대시보드 ---
try:
    df = load_all_data()
    
    if not df.empty:
        st.sidebar.header("📊 필터")
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🎯 메인 키워드", main_list)
        
        view_df = df[df['main_keyword'] == target]
        st.title(f"📊 {target} 분석 리포트")
        
        products = sorted(view_df['product_name'].unique())
        selected_product = st.selectbox("🔎 분석할 상품 선택", ["--- 선택하세요 ---"] + products)
        
        if selected_product != "--- 선택하세요 ---":
            sub_data = view_df[view_df['product_name'] == selected_product].copy()
            
            # 상단 요약 지표
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("연관 키워드", f"{len(sub_data)}개")
            with c2: st.metric("최고 검색량", f"{sub_data['검색량_숫자'].max():,}")
            with c3: 
                # 0원 방지 로직 포함 평균가 계산
                actual_prices = sub_data[sub_data['평균가'] > 0]['평균가']
                avg_val = int(actual_prices.mean()) if not actual_prices.empty else 0
                st.metric("평균 시장가", f"₩{avg_val:,}")
            
            st.divider()

            if not sub_data.empty:
                display_df = sub_data[['sub_keyword', '검색량_숫자', '노출수', '클릭수', '평균가']]
                
                gb = GridOptionsBuilder.from_dataframe(display_df)
                gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left', width=170)
                gb.configure_column("검색량_숫자", headerName="검색량", type=["numericColumn"], sort="desc", valueFormatter="x.toLocaleString()")
                gb.configure_column("노출수", headerName="노출수", valueFormatter="x.toLocaleString()")
                gb.configure_column("클릭수", headerName="클릭수", valueFormatter="x.toLocaleString()")
                # 단가 표시 형식 수정
                gb.configure_column("평균가", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
                
                grid_options = gb.build()
                AgGrid(display_df, gridOptions=grid_options, theme='alpine', columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS, height=500)
    else:
        st.warning("표시할 데이터가 없습니다.")

except Exception as e:
    st.error(f"오류: {e}")
