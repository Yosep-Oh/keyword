import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [1] 비밀번호 설정 ---
MY_PASSWORD = "141242" 

st.set_page_config(layout="wide", page_title="쿠팡 마켓 분석기")

# --- [2] 로그인 화면 로직 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 보안 접속 (사장님 전용)")
    pwd_input = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
        if pwd_input == MY_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop() 

# --- [3] 데이터 로드 및 표시 ---
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
    limit = 1000  # 한 번에 가져올 양
    offset = 0    # 시작점
    
    while True:
        # 수파베이스에서 1000개씩 끊어서 가져오기
        res = supabase.table("market_analysis").select("*").range(offset, offset + limit - 1).execute()
        
        # 가져온 데이터를 리스트에 추가
        all_rows.extend(res.data)
        
        # 만약 가져온 데이터가 1000개보다 적으면 더 이상 데이터가 없다는 뜻이므로 중단
        if len(res.data) < limit:
            break
            
        # 다음 1000개를 가져오기 위해 위치 이동
        offset += limit
        
    df = pd.DataFrame(all_rows)
    
    # 숫자 정제 (콤마 제거, 정수화 등)
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
                gb.configure_column("노출수", headerName="노출수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("클릭수", headerName="클릭수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("평균가", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
                
                grid_options = gb.build()
                AgGrid(display_df, gridOptions=grid_options, theme='alpine', columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS)
    else:
        st.info("데이터가 없습니다.")
except Exception as e:
    st.error(f"오류 발생: {e}")

