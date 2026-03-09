
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

st.set_page_config(layout="wide", page_title="쿠팡 정밀 분석 리포트")

# --- 데이터 로드 함수 (캐싱 적용으로 속도 향상) ---
@st.cache_data
def get_clean_data():
    try:
        # 정제된 CSV 파일을 읽어옵니다.
        df = pd.read_csv('data_final.csv')
        return df
    except:
        return pd.DataFrame()

# --- UI 구성 ---
df = get_clean_data()

if not df.empty:
    st.title(f"📊 {df['메인키워드'].iloc[0]} 시장 분석 리포트")
    st.info(f"총 {len(df['상품명'].unique())}개의 상품 정보가 로드되었습니다.")

    # 1. 사이드바 필터 (전체 상품을 다 보여주면 느려지므로 선택한 것만 보여줌)
    st.sidebar.header("🔍 상품 필터")
    all_products = list(df['상품명'].unique())
    selected_p = st.sidebar.selectbox("보고 싶은 상품을 선택하세요", ["전체 보기"] + all_products)

    # 필터링
    view_df = df if selected_p == "전체 보기" else df[df['상품명'] == selected_p]

    # 2. 통합 분석 표 (AgGrid) - 이게 가장 빠르고 정확합니다.
    st.subheader("📝 세부 키워드 성과 리스트")
    
    gb = GridOptionsBuilder.from_dataframe(view_df)
    gb.configure_default_column(sortable=True, filterable=True, resizable=True)
    gb.configure_column("순위", width=70, pinned='left')
    gb.configure_column("세부키워드", width=160, pinned='left')
    gb.configure_column("상품명", width=300)
    
    # 수치 가독성 및 정렬
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

    # 3. 개별 상품 상세 카드 (선택시에만 렌더링해서 부하 감소)
    if selected_p != "전체 보기":
        st.divider()
        st.subheader(f"🏠 {selected_p} 상세 분석")
        st.table(view_df[['세부키워드', '검색량', '노출수', '클릭수', '평균단가']])

else:
    st.error("데이터를 불러올 수 없습니다. Clean_Data.py를 먼저 실행하고 업로드해주세요.")
