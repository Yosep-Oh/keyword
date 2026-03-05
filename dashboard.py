import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# 1. 수파베이스 연결
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="쿠팡 마켓 분석기")

# 2. 숫자 정제 함수 (소수점 제거 및 정수화)
def clean_to_int(val):
    if pd.isna(val) or val == "": return 0
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').strip()
    try:
        if '만' in s:
            num = float(s.replace('만', '')) * 10000
        else:
            num = float(s)
        return int(round(num))
    except:
        return 0

# 3. 데이터 로드 (무제한)
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
        # 화면에 보여줄 숫자 전용 컬럼 생성
        df['검색량_숫자'] = df['keyword_vol'].apply(clean_to_int)
        df['노출수'] = df['keyword_exposure'].apply(clean_to_int)
        df['클릭수'] = df['keyword_clicks'].apply(clean_to_int)
        df['평균가'] = df['avg_price'].apply(clean_to_int)
    return df

try:
    df = load_all_data()
    if not df.empty:
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🔎 메인 검색어 선택", main_list)
        
        view_df = df[df['main_keyword'] == target]
        st.title(f"📊 {target} 분석 리포트")
        
        products = view_df['product_name'].unique()
        for i, p_name in enumerate(products, 1):
            with st.expander(f"{i}. {p_name}", expanded=True if i <= 3 else False):
                sub_data = view_df[view_df['product_name'] == p_name].copy()
                
                # --- 표 설정 시작 (한글화 핵심!) ---
                # 보여줄 컬럼만 선택 (영어 컬럼은 제외)
                display_df = sub_data[['sub_keyword', 'keyword_vol', '검색량_숫자', '노출수', '클릭수', '평균가']]
                
                gb = GridOptionsBuilder.from_dataframe(display_df)
                
                # 각 컬럼의 제목을 한글로 고정
                gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left')
                gb.configure_column("keyword_vol", headerName="검색량(원문)")
                gb.configure_column("검색량_숫자", headerName="검색량(정렬)", type=["numericColumn"], sort="desc", valueFormatter="x.toLocaleString()")
                gb.configure_column("노출수", headerName="노출수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("클릭수", headerName="클릭수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("평균가", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
                
                grid_options = gb.build()
                
                AgGrid(
                    display_df, 
                    gridOptions=grid_options, 
                    theme='alpine', 
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
                )
    else:
        st.info("데이터가 없습니다.")
except Exception as e:
    st.error(f"오류 발생: {e}")
