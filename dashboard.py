import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [설정] 사장님 수파베이스 정보 ---
URL = "https://aywlsumqnuqhckpmftzr.supabase.co"
KEY = "sb_publishable_Sgsd4QuO1oFWaS30BI4ojQ_QbueNP90"
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="쿠팡 마켓 정밀 분석기")

# 숫자 변환 및 소수점 2자리 반올림 함수 (보강됨)
def to_num(val):
    if pd.isna(val) or val == "": return 0
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').strip()
    if '만' in s:
        try: return round(float(s.replace('만', '')) * 10000, 2)
        except: return 0
    try:
        return round(float(s), 2) # 여기서 소수점 반올림 처리
    except:
        return 0

# 데이터 로딩 (캐싱 적용)
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
        # 정렬용 숫자 컬럼 생성 (반올림 적용)
        df['검색량_수치'] = df['keyword_vol'].apply(to_num)
        df['노출_수치'] = df['keyword_exposure'].apply(to_num)
        df['클릭_수치'] = df['keyword_clicks'].apply(to_num)
        df['평균가_수치'] = df['avg_price'].apply(to_num)
    return df

try:
    df = load_all_data()
    
    if not df.empty:
        st.sidebar.header("🔍 검색 설정")
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("메인 검색어 선택", main_list)
        
        view_df = df[df['main_keyword'] == target]
        
        st.title(f"📊 “{target}” 분석 리포트")
        st.info(f"총 {len(view_df['product_name'].unique())}개의 상품 데이터가 로드되었습니다.")

        # --- [중요] 뒤쪽 데이터가 안 나오는 문제 해결책 ---
        # 1. 사이드바에서 상품을 선택하도록 유도 (브라우저 부하 방지)
        all_products = view_df['product_name'].unique()
        selected_p = st.sidebar.selectbox("상세 분석할 상품 선택", ["전체 요약 보기"] + list(all_products))

        if selected_p == "전체 요약 보기":
            # 전체 데이터를 한꺼번에 정렬해서 보여주는 모드
            st.subheader("📋 전체 상품 통합 분석 (검색량 순 정렬)")
            display_df = view_df.sort_values(by="검색량_수치", ascending=False)
        else:
            # 선택한 상품만 보여주는 모드
            st.subheader(f"🏠 {selected_p} 상세 키워드 분석")
            display_df = view_df[view_df['product_name'] == selected_p]

        # AgGrid 설정 (원래 코드 스타일)
        gb = GridOptionsBuilder.from_dataframe(display_df[[
            'product_name', 'sub_keyword', '검색량_수치', '노출_수치', '클릭_수치', '평균가_수치'
        ]])
        
        gb.configure_column("product_name", headerName="상품명", width=200)
        gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left', width=180)
        gb.configure_column("검색량_수치", headerName="검색량", type=["numericColumn"], sort="desc")
        gb.configure_column("노출_수치", headerName="노출수", type=["numericColumn"])
        gb.configure_column("클릭_수치", headerName="클릭수", type=["numericColumn"])
        gb.configure_column("평균가_수치", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
        
        grid_options = gb.build()
        
        AgGrid(
            display_df, 
            gridOptions=grid_options, 
            height=600, # 높이를 충분히 주어 짤림 방지
            theme='alpine',
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
        )

    else:
        st.warning("데이터베이스가 비어있습니다.")

except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")

input_val = st.sidebar.button("💾 데이터 새로고침")
if input_val: st.cache_data.clear()
