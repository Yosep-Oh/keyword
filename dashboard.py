import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# 1. 수파베이스 연결 (금고에서 정보 가져오기)
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="쿠팡 마켓 분석기")

# 2. 데이터 무제한 로드 함수 (영문 필수!)
@st.cache_data(ttl=300)
def load_all_data():
    all_rows = []
    limit = 1000
    offset = 0
    while True:
        res = supabase.table("market_analysis").select("*").range(offset, offset + limit - 1).execute()
        all_rows.extend(res.data)
        if len(res.data) < limit:
            break
        offset += limit
    return pd.DataFrame(all_rows)

# 3. 데이터 표시 로직
try:
    df = load_all_data()
    if not df.empty:
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🔎 메인 검색어 선택", main_list)
        
        view_df = df[df['main_keyword'] == target]
        st.title(f"📊 {target} 분석 리포트")
        
        products = view_df['product_name'].unique()
        for i, p_name in enumerate(products, 1):
            with st.expander(f"{i}. {p_name}", expanded=True):
                sub_data = view_df[view_df['product_name'] == p_name].copy()
                # 표 설정
                gb = GridOptionsBuilder.from_dataframe(sub_data[['sub_keyword', 'keyword_vol', 'keyword_exposure', 'keyword_clicks', 'avg_price']])
                gb.configure_column("sub_keyword", headerName="연관 키워드")
                gb.configure_column("keyword_vol", headerName="검색량")
                grid_options = gb.build()
                
                AgGrid(sub_data, gridOptions=grid_options, theme='alpine', columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS)
    else:
        st.info("데이터가 없습니다. upload.py를 실행해 주세요.")
except Exception as e:
    st.error(f"오류 발생: {e}")
