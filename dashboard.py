import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [설정] Streamlit Secrets에서 가져오기 ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="쿠팡 마켓 분석기")

# 숫자 변환 및 반올림 함수 (99.9999 방지)
def to_int(val):
    if pd.isna(val) or val == "": return 0
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').strip()
    try:
        if '만' in s:
            num = float(s.replace('만', '')) * 10000
        else:
            num = float(s)
        return int(round(num)) # 반올림 후 정수로 변환
    except:
        return 0

@st.cache_data(ttl=300)
def load_all_data():
    all_rows = []
    limit = 1000
    offset = 0
    while True:
        # range를 사용하여 1000개 이상의 데이터도 끝까지 가져옴
        res = supabase.table("market_analysis").select("*").range(offset, offset + limit - 1).execute()
        all_rows.extend(res.data)
        if len(res.data) < limit: break
        offset += limit
    
    df = pd.DataFrame(all_rows)
    if not df.empty:
        # 숫자 정제 적용
        df['검색량_수치'] = df['keyword_vol'].apply(to_int)
        df['노출_수치'] = df['keyword_exposure'].apply(to_int)
        df['클릭_수치'] = df['keyword_clicks'].apply(to_int)
        df['평균가_수치'] = df['avg_price'].apply(to_int)
    return df

try:
    df = load_all_data()
    
    if not df.empty:
        # 사이드바에서 모든 검색어가 나오도록 설정
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🔎 메인 검색어 선택", main_list)
        
        view_df = df[df['main_keyword'] == target]
        
        st.title(f"📊 “{target}” 분석 리포트")
        
        products = view_df['product_name'].unique()
        for i, p_name in enumerate(products, 1):
            with st.expander(f"{i}. {p_name}", expanded=True if i <= 3 else False):
                sub_data = view_df[view_df['product_name'] == p_name].copy()
                
                gb = GridOptionsBuilder.from_dataframe(sub_data[[
                    'sub_keyword', 'keyword_vol', '검색량_수치', '노출_수치', '클릭_수치', '평균가_수치'
                ]])
                
                # 컬럼 설정 및 콤마 포맷팅
                gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left')
                gb.configure_column("keyword_vol", headerName="검색량(원문)")
                gb.configure_column("검색량_수치", headerName="검색량(정렬)", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("노출_수치", headerName="노출수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("클릭_수치", headerName="클릭수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("평균가_수치", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
                
                grid_options = gb.build()
                
                AgGrid(sub_data, gridOptions=grid_options, height=350, theme='alpine', columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS)
    else:
        st.warning("데이터가 없습니다. upload.py로 데이터를 먼저 넣어주세요.")

except Exception as e:
    st.error(f"데이터 로드 오류: {e}")
