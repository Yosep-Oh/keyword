import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [1] 비밀번호 설정 ---
MY_PASSWORD = "141242" 

st.set_page_config(layout="wide", page_title="쿠팡 마켓 분석기")

# --- [2] 로그인 화면 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 보안 접속")
    pwd_input = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pwd_input == MY_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("틀렸습니다.")
    st.stop()

# --- [3] 데이터 로드 ---
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
    step = 1000
    offset = 0
    while True:
        res = supabase.table("market_analysis").select("*").range(offset, offset + step - 1).execute()
        if not res.data: break
        all_rows.extend(res.data)
        if len(res.data) < step: break
        offset += step
    df_loaded = pd.DataFrame(all_rows)
    if not df_loaded.empty:
        df_loaded['product_name'] = df_loaded['product_name'].astype(str).str.strip()
        df_loaded['main_keyword'] = df_loaded['main_keyword'].astype(str).str.strip()
        df_loaded['검색량_숫자'] = df_loaded['keyword_vol'].apply(clean_to_int)
        df_loaded['노출수'] = df_loaded['keyword_exposure'].apply(clean_to_int)
        df_loaded['클릭수'] = df_loaded['keyword_clicks'].apply(clean_to_int)
        df_loaded['평균가'] = df_loaded['avg_price'].apply(clean_to_int)
    return df_loaded

# --- [4] 메인 실행 (최적화 방식) ---
try:
    df = load_all_data()
    
    if not df.empty:
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🔎 메인 검색어 선택", main_list)
        
        view_df = df[df['main_keyword'] == target]
        st.title(f"📊 {target} 분석 리포트")
        
        # [핵심 변경] 모든 상품을 다 펼치지 않고, 선택해서 보게 만듭니다.
        products = sorted(view_df['product_name'].unique())
        
        # 상품 선택 드롭다운 추가 (이게 훨씬 빠릅니다)
        selected_product = st.selectbox("확인할 상품을 선택하세요", ["전체 보기"] + products)
        
        if selected_product == "전체 보기":
            st.info("개별 상품을 선택하시면 상세 표가 나타납니다.")
            st.write(view_df[['product_name', 'sub_keyword', '검색량_숫자']].head(50)) # 요약만 살짝
        else:
            sub_data = view_df[view_df['product_name'] == selected_product].copy()
            st.subheader(f"✅ {selected_product}")
            
            if not sub_data.empty:
                display_df = sub_data[['sub_keyword', 'keyword_vol', '검색량_숫자', '노출수', '클릭수', '평균가']]
                
                gb = GridOptionsBuilder.from_dataframe(display_df)
                gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left')
                gb.configure_column("검색량_숫자", headerName="검색량(정렬)", type=["numericColumn"], sort="desc", valueFormatter="x.toLocaleString()")
                gb.configure_column("노출수", headerName="노출수", valueFormatter="x.toLocaleString()")
                gb.configure_column("클릭수", headerName="클릭수", valueFormatter="x.toLocaleString()")
                gb.configure_column("평균가", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
                
                grid_options = gb.build()
                AgGrid(display_df, gridOptions=grid_options, theme='alpine', columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS)
            else:
                st.warning("상세 데이터가 없습니다.")
    else:
        st.info("데이터가 없습니다.")

except Exception as e:
    st.error(f"오류: {e}")
