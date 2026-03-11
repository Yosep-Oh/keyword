import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. 보안 설정 (Secrets에서 값 불러오기)
# Streamlit Cloud 설정창의 Advanced Settings > Secrets에 URL과 KEY를 넣어야 작동합니다.
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except KeyError:
    st.error("❌ Streamlit Cloud의 Secrets 설정이 누락되었습니다. URL과 KEY를 등록해주세요.")
    st.stop()

# 2. Supabase 접속
@st.cache_resource
def init_connection():
    return create_client(url, key)

supabase = init_connection()

# --- UI 설정 ---
st.set_page_config(page_title="쿠팡 키워드 대시보드", layout="wide")

# 깔끔한 제목
st.markdown("<h1 style='text-align: center; color: #0074e9;'>🚀 쿠팡 키워드 정밀 분석 시스템</h1>", unsafe_allow_html=True)
st.write("---")

# 3. 데이터 로드 함수 (속도를 위해 캐싱 적용)
@st.cache_data(ttl=600) # 10분마다 갱신
def get_data():
    try:
        # DB의 모든 데이터를 가져옴
        res = supabase.table("coupang_keywords").select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

df = get_data()

if df.empty:
    st.warning("⚠️ 데이터베이스에 표시할 데이터가 없습니다. 업로드가 완료되었는지 확인해주세요.")
else:
    # --- [상단] 핵심 요약 지표 ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 전체 키워드 수", f"{len(df):,}개")
    with col2:
        st.metric("🔥 최고 검색량", f"{df['search_count'].max():,}건")
    with col3:
        st.metric("👀 최고 노출수", f"{df['impression_count'].max():,}건")
    with col4:
        # 클릭률(CTR) 계산
        total_imp = df['impression_count'].sum()
        total_click = df['click_count'].sum()
        avg_ctr = (total_click / total_imp * 100) if total_imp > 0 else 0
        st.metric("🎯 평균 클릭률", f"{avg_ctr:.2f}%")

    st.write("---")

    # --- [중간] 필터 및 검색 ---
    c1, c2 = st.columns([2, 1])
    with c1:
        search_query = st.text_input("🔍 상품명 또는 연관키워드 검색 (예: 무드등, 크리스마스)", "")
    with c2:
        main_kw_filter = st.selectbox("📌 메인키워드 필터", ["전체"] + list(df['main_keyword'].unique()))

    # 데이터 필터링 로직
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df['product_name'].str.contains(search_query, na=False) | 
            filtered_df['sub_keyword'].str.contains(search_query, na=False)
        ]
    if main_kw_filter != "전체":
        filtered_df = filtered_df[filtered_df['main_keyword'] == main_kw_filter]

    # --- [하단] 데이터 리스트 (정렬 기능 내장) ---
    st.subheader("📋 키워드 분석 리스트")
    st.info("💡 각 열 제목을 클릭하면 오름차순/내림차순으로 정렬됩니다.")

    # 사용자가 보기 편하게 컬럼 순서 및 이름 변경
    display_df = filtered_df[['main_keyword', 'category', 'product_name', 'sub_keyword', 'search_count', 'impression_count', 'click_count']]
    
    st.dataframe(
        display_df,
        column_config={
            "main_keyword": "메인키워드",
            "category": "카테고리",
            "product_name": "상품명(i+2)",
            "sub_keyword": "연관키워드",
            "search_count": st.column_config.NumberColumn("검색량", format="%d"),
            "impression_count": st.column_config.NumberColumn("노출수", format="%d"),
            "click_count": st.column_config.NumberColumn("클릭수", format="%d"),
        },
        use_container_width=True,
        hide_index=True
    )

    # --- [최하단] 시각화 (선택사항) ---
    if st.checkbox("📈 클릭률(CTR) 그래프 보기"):
        st.subheader("효율 상위 20개 키워드 (CTR %)")
        filtered_df['ctr'] = (filtered_df['click_count'] / filtered_df['impression_count'] * 100).fillna(0)
        top_20 = filtered_df.sort_values(by='ctr', ascending=False).head(20)
        st.bar_chart(data=top_20, x='sub_keyword', y='ctr')

st.write("---")
st.caption("Admin Dashboard for Coupang Keyword Analysis | Powered by Supabase & Streamlit")
