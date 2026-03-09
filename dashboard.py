import streamlit as st
import pandas as pd
from supabase import create_client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [설정] 사장님 수파베이스 정보 ---
URL = "https://aywlsumqnuqhckpmftzr.supabase.co"
KEY = "sb_publishable_Sgsd4QuO1oFWaS30BI4ojQ_QbueNP90"
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="쿠팡 정밀 분석기")

def to_num(val):
    if pd.isna(val) or val == "": return 0
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').strip()
    if '만' in s:
        try: return round(float(s.replace('만', '')) * 10000, 2)
        except: return 0
    try: return round(float(s), 2)
    except: return 0

@st.cache_data(ttl=60) # 최신 데이터를 위해 캐시 시간을 줄였습니다.
def load_all_data():
    all_rows = []
    res = supabase.table("market_analysis").select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['검색량_수치'] = df['keyword_vol'].apply(to_num)
        df['노출_수치'] = df['keyword_exposure'].apply(to_num)
        df['클릭_수치'] = df['keyword_clicks'].apply(to_num)
        df['평균가_수치'] = df['avg_price'].apply(to_num)
    return df

try:
    df = load_all_data()
    if not df.empty:
        st.sidebar.header("🔍 검색 설정")
        target = st.sidebar.selectbox("메인 검색어 선택", sorted(df['main_keyword'].unique()))
        view_df = df[df['main_keyword'] == target]
        
        st.title(f"📊 “{target}” 분석 리포트")
        
        # 상품별 선택 기능 (뒤쪽 데이터 잘림 방지용 핵심 코드)
        selected_p = st.sidebar.selectbox("상세 분석할 상품명", ["전체 요약"] + list(view_df['product_name'].unique()))
        
        display_df = view_df if selected_p == "전체 요약" else view_df[view_df['product_name'] == selected_p]

        gb = GridOptionsBuilder.from_dataframe(display_df[['product_name', 'sub_keyword', '검색량_수치', '노출_수치', '클릭_수치', '평균가_수치']])
        gb.configure_default_column(sortable=True, filterable=True)
        gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left')
        gb.configure_column("검색량_수치", headerName="검색량", sort="desc")
        gb.configure_column("평균가_수치", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
        
        AgGrid(display_df, gridOptions=gb.build(), height=600, theme='alpine', columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS)

except Exception as e:
    st.error(f"오류: {e}")
