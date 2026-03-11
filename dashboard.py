import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. 보안 설정 (Secrets에서 값 불러오기)
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
st.set_page_config(page_title="쿠팡 키워드 정밀 분석", layout="wide")

# 깔끔한 제목
st.markdown("<h1 style='text-align: center; color: #0074e9;'>🚀 쿠팡 키워드 정밀 분석 시스템</h1>", unsafe_allow_html=True)
st.write("---")

# 3. 데이터 로드 함수 (Pagination 적용)
@st.cache_data(ttl=600)
def get_all_data():
    try:
        all_data = []
        page_size = 1000
        offset = 0
        
        loading_text = st.empty()
        loading_text.info("⏳ 데이터베이스에서 정보를 긁어모으는 중입니다...")
        
        while True:
            # 테이블명을 우리가 새로 만든 'keyword_data'로 변경
            res = supabase.table("keyword_data").select("*").range(offset, offset + page_size - 1).execute()
            data = res.data
            all_data.extend(data)
            
            if len(data) < page_size:
                break
            offset += page_size
            
        loading_text.empty()
        df = pd.DataFrame(all_data)

        # [중요] 텍스트로 저장된 숫자를 실제 계산 가능한 숫자로 변환 (콤마 제거)
        num_cols = ['search_volume', 'exposure', 'click']
        for col in num_cols:
            df[col] = df[col].str.replace(',', '').astype(float)
            
        return df
    
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# 데이터 호출
df = get_all_data()

if df.empty:
    st.warning("⚠️ 데이터베이스에 표시할 데이터가 없습니다. 업로드가 완료되었는지 확인해주세요.")
else:
    # --- [상단] 핵심 요약 지표 ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 전체 키워드 수", f"{len(df):,}개")
    with col2:
        st.metric("🔥 최고 검색량", f"{int(df['search_volume'].max()):,}건")
    with col3:
        st.metric("👀 최고 노출수", f"{int(df['exposure'].max()):,}건")
    with col4:
        total_exp = df['exposure'].sum()
        total_click = df['click'].sum()
        avg_ctr = (total_click / total_exp * 100) if total_exp > 0 else 0
        st.metric("🎯 평균 클릭률", f"{avg_ctr:.2f}%")

    st.write("---")

    # --- [중간] 필터 및 검색 ---
    c1, c2 = st.columns([2, 1])
    with c1:
        search_query = st.text_input("🔍 상품명 또는 연관키워드 검색 (예: 무드등, 연마기)", "")
    with c2:
        # 중복 제거된 카테고리 리스트
        cat_list = sorted(df['category'].unique().tolist())
        cat_filter = st.selectbox("📌 카테고리 필터", ["전체"] + cat_list)

    # 데이터 필터링 로직
    filtered_df = df.copy()
    if search_query:
        # 상품명(product_name)과 검색어(search_term) 양쪽에서 검색
        filtered_df = filtered_df[
            filtered_df['product_name'].str.contains(search_query, na=False, case=False) | 
            filtered_df['search_term'].str.contains(search_query, na=False, case=False)
        ]
    if cat_filter != "전체":
        filtered_df = filtered_df[filtered_df['category'] == cat_filter]

    # --- [하단] 데이터 리스트 ---
    st.subheader(f"📋 분석 리스트 (검색 결과: {len(filtered_df):,}건)")
    
    # 출력용 컬럼 정리 및 정렬 기본값 설정
    display_df = filtered_df[['category', 'product_name', 'search_term', 'search_volume', 'exposure', 'click', 'price_range']]
    
    st.dataframe(
        display_df,
        column_config={
            "category": "카테고리 경로",
            "product_name": "상품명",
            "search_term": "연관 검색어",
            "search_volume": st.column_config.NumberColumn("검색량", format="%d"),
            "exposure": st.column_config.NumberColumn("노출수", format="%d"),
            "click": st.column_config.NumberColumn("클릭수", format="%d"),
            "price_range": "가격 범위",
        },
        use_container_width=True,
        hide_index=True
    )

    # --- [최하단] 시각화 (CTR 분석) ---
    st.write("---")
    if st.checkbox("📈 클릭률(CTR) 및 효율 분석 그래프 보기"):
        st.subheader("🚀 효율 상위 20개 키워드 (CTR %)")
        # CTR 계산
        filtered_df['ctr'] = (filtered_df['click'] / filtered_df['exposure'] * 100).fillna(0)
        top_20 = filtered_df.sort_values(by='ctr', ascending=False).head(20)
        
        # 바 차트 시각화
        st.bar_chart(data=top_20, x='search_term', y='ctr', color="#0074e9")

st.write("---")
st.caption("Admin Dashboard for Coupang Keyword Analysis | Powered by Supabase & Streamlit")
