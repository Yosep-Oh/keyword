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

# --- [3] 수파베이스 연결 및 데이터 로드 함수 ---
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
        # 데이터 정제: 앞뒤 공백 제거 및 숫자 변환
        df_loaded['product_name'] = df_loaded['product_name'].astype(str).str.strip()
        df_loaded['main_keyword'] = df_loaded['main_keyword'].astype(str).str.strip()
        df_loaded['검색량_숫자'] = df_loaded['keyword_vol'].apply(clean_to_int)
        df_loaded['노출수'] = df_loaded['keyword_exposure'].apply(clean_to_int)
        df_loaded['클릭수'] = df_loaded['keyword_clicks'].apply(clean_to_int)
        df_loaded['평균가'] = df_loaded['avg_price'].apply(clean_to_int)
    return df_loaded

# --- [4] 메인 실행부 ---
try:
    # 여기서 df를 확실하게 정의합니다! (이게 없어서 아까 에러가 난 거예요)
    df = load_all_data()
    
    if not df.empty:
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🔎 메인 검색어 선택", main_list)
        
        view_df = df[df['main_keyword'] == target]
        st.title(f"📊 {target} 분석 리포트")
        
        products = sorted(view_df['product_name'].unique())
        
        for i, p_name in enumerate(products, 1):
            sub_data = view_df[view_df['product_name'] == p_name].copy()
            # 해당 상품의 키워드 개수를 제목에 표시
            with st.expander(f"{i}. {p_name} ({len(sub_data)}개 키워드)", expanded=(i<=3)):
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
                    st.warning("이 상품에는 상세 데이터가 없습니다.")
    else:
        st.info("데이터베이스가 비어 있습니다. upload.py를 실행해 주세요.")

except Exception as e:
    st.error(f"오류 발생: {e}")
