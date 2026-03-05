import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [설정] 사장님 수파베이스 정보 ---
URL = "https://aywlsumqnuqhckpmftzr.supabase.co"
KEY = "sb_publishable_Sgsd4QuO1oFWaS30BI4ojQ_QbueNP90"
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="쿠팡 마켓 정밀 분석기")

# 숫자 변환 함수
def to_num(val):
    if pd.isna(val) or val == "": return 0
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').strip()
    if '만' in s:
        try: return float(s.replace('만', '')) * 10000
        except: return 0
    try: return float(s)
    except: return 0

# 데이터 전량 불러오기 (1000개 제한 돌파)
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
        # 정렬용 숫자 컬럼 생성
        df['검색량_수치'] = df['keyword_vol'].apply(to_num)
        df['노출_수치'] = df['keyword_exposure'].apply(to_num)
        df['클릭_수치'] = df['keyword_clicks'].apply(to_num)
        df['평균가_수치'] = df['avg_price'].apply(to_num)
    return df

try:
    df = load_all_data()
    
    if not df.empty:
        # 1. 사이드바 검색어 필터
        st.sidebar.header("🔍 검색 설정")
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("메인 검색어 선택", main_list)
        
        view_df = df[df['main_keyword'] == target]
        
        # 2. 메인 화면 헤더
        st.title(f"📊 “{target}” 분석 리포트")
        st.info(f"선택된 시장 내 총 {len(view_df['product_name'].unique())}개의 경쟁 상품이 분석되었습니다.")

        # 3. 상품별 상세 리스트
        products = view_df['product_name'].unique()
        for i, p_name in enumerate(products, 1):
            with st.expander(f"{i}. {p_name}", expanded=True if i <= 3 else False):
                sub_data = view_df[view_df['product_name'] == p_name].copy()
                
                # 표 제목 한글화 및 설정
                gb = GridOptionsBuilder.from_dataframe(sub_data[[
                    'sub_keyword', 'keyword_vol', 'keyword_exposure', 'keyword_clicks', 'avg_price',
                    '검색량_수치', '노출_수치', '클릭_수치', '평균가_수치'
                ]])
                
                # 한글 이름 매칭
                gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left', width=180)
                gb.configure_column("keyword_vol", headerName="검색량(원문)")
                gb.configure_column("검색량_수치", headerName="검색량(정렬)", type=["numericColumn", "numberColumnFilter"], sort="desc")
                gb.configure_column("노출_수치", headerName="노출수", type=["numericColumn"])
                gb.configure_column("클릭_수치", headerName="클릭수", type=["numericColumn"])
                gb.configure_column("평균가_수치", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
                
                # 원본 영어 컬럼은 숨기기 (보기 지저분하니까요)
                gb.configure_columns(['keyword_exposure', 'keyword_clicks', 'avg_price'], hide=True)
                
                grid_options = gb.build()
                
                AgGrid(
                    sub_data, 
                    gridOptions=grid_options, 
                    height=350, 
                    theme='alpine', # 더 깔끔한 테마
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
                )
    else:
        st.warning("데이터베이스가 비어있습니다.")

except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")

input_val = st.sidebar.button("💾 데이터 새로고침")
if input_val: st.cache_data.clear()