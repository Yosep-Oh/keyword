import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

st.set_page_config(layout="wide", page_title="쿠팡 정밀 리포트")

try:
    df = pd.read_csv('data_final.csv')
    
    st.title(f"📊 {df['메인키워드'].iloc[0]} 시장 분석 리포트")
    st.caption(f"📂 카테고리: {df['카테고리'].iloc[0]}")

    # 1. 사이드바 - 상품 선택
    st.sidebar.header("🔍 상품 필터")
    selected_product = st.sidebar.selectbox("상품명 선택", ["전체 보기"] + list(df['상품명'].unique()))
    
    view_df = df if selected_product == "전체 보기" else df[df['상품명'] == selected_product]

    # 2. 메인 표 (AgGrid)
    gb = GridOptionsBuilder.from_dataframe(view_df)
    gb.configure_default_column(sortable=True, filterable=True, resizable=True)
    gb.configure_column("순위", width=80, pinned='left')
    gb.configure_column("세부키워드", width=180, pinned='left')
    gb.configure_column("상품명", width=300)
    
    # 숫자 포맷팅 및 정렬 설정
    gb.configure_column("검색량", type=["numericColumn"], sort='desc')
    gb.configure_column("노출수", type=["numericColumn"])
    gb.configure_column("클릭수", type=["numericColumn"])
    gb.configure_column("평균단가", valueFormatter="'₩' + x.toLocaleString()")
    
    grid_options = gb.build()

    AgGrid(
        view_df,
        gridOptions=grid_options,
        theme='alpine',
        height=600,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
    )

except Exception:
    st.warning("먼저 Clean_Data.py를 실행하여 데이터를 정제해주세요.")
