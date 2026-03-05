import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [1] 비밀번호 설정 (사장님만 아는 암호로 바꾸셔도 됩니다) ---
MY_PASSWORD = "141242" 

st.set_page_config(layout="wide", page_title="쿠팡 마켓 분석기")

# --- [2] 로그인 화면 로직 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 보안 접속 (사장님 전용)")
    # 비밀번호 입력 칸
    pwd_input = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
        if pwd_input == MY_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop() # 로그인 전에는 아래 코드를 실행 안 함

# --- [3] 데이터 로드 및 표시 (로그인 성공 시) ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def clean_to_int(val):
    if pd.isna(val) or val == "": return 0
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').strip()
    try:
        num = float(s.replace('만', '')) * 10000 if '만' in s else float(s)
        return int(round(num))
    except: return 0

@st.cache_data(ttl=300)
def load_all_data():
    all_rows = []
    limit = 1000
    offset = 0
    while True:
        res = supabase.table("market_analysis").select("*").range(offset, offset + limit - 1).execute()
        all_rows.extend(res.data)
        if len(res.data) < limit: break
        offset += limit
    df = pd.DataFrame(all_rows)
    if not df.empty:
        df['검색량_숫자'] = df['keyword_vol'].apply(clean_to_int)
        df['노출수'] = df['keyword_exposure'].apply(clean_to_int)
        df['클릭수'] = df['keyword_clicks'].apply(clean_to_int)
        df['평균가'] = df['avg_price'].apply(clean_to_int)
    return df

try:
    df = load_all_data()
    if not df.empty:
        st.sidebar.success("✅ 인증 완료")
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🔎 메인 검색어 선택", main_list)
        
        view_df = df[df['main_keyword'] == target]
        st.title(f"📊 {target} 분석 리포트")
        
        products = view_df['product_name'].unique()
        for i, p_name in enumerate(products, 1):
            with st.expander(f"{i}. {p_name}", expanded=True if i <= 3 else False):
                sub_data = view_df[view_df['product_name'] == p_name].copy()
                display_df = sub_data[['sub_keyword', 'keyword_vol', '검색량_숫자', '노출수', '클릭수', '평균가']]
                
                gb = GridOptionsBuilder.from_dataframe(display_df)
                gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left')
                gb.configure_column("keyword_vol", headerName="검색량(원문)")
                gb.configure_column("검색량_숫자", headerName="검색량(정렬)", type=["numericColumn"], sort="desc", valueFormatter="x.toLocaleString()")
                gb.configure

