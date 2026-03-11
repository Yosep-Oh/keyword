import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. 보안 및 접속 설정 (기존과 동일)
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
except KeyError:
    st.error("❌ Secrets 설정 확인 필요")
    st.stop()

@st.cache_resource
def init_connection():
    return create_client(url, key)

supabase = init_connection()

# --- [추가] 숫자를 한글 단위로 변환하는 함수 ---
def format_korean_unit(num):
    if num >= 10000:
        return f"{num / 10000:.2f}만".replace('.00', '')
    elif num >= 1000:
        return f"{num / 1000:.1f}천".replace('.0', '')
    return str(int(num))

# --- [기존] 한글 단위를 숫자로 변환하는 함수 ---
def convert_unit(val):
    if pd.isna(val) or val == "": return 0.0
    val = str(val).replace(',', '').strip()
    try:
        if '만' in val: return float(val.replace('만', '')) * 10000
        elif '천' in val: return float(val.replace('천', '')) * 1000
        return float(val)
    except: return 0.0

@st.cache_data(ttl=600)
def get_all_data():
    all_data = []
    page_size = 1000
    offset = 0
    while True:
        res = supabase.table("keyword_data").select("*").range(offset, offset + page_size - 1).execute()
        data = res.data
        all_data.extend(data)
        if len(data) < page_size: break
        offset += page_size
    df = pd.DataFrame(all_data)
    
    # 계산을 위해 일단 숫자로 변환
    for col in ['search_volume', 'exposure', 'click']:
        df[col] = df[col].apply(convert_unit)
    return df

# UI 설정
st.set_page_config(page_title="쿠팡 키워드 정밀 분석", layout="wide")
df = get_all_data()

if not df.empty:
    # --- [상단 지표] 한글 단위 적용 ---
    st.markdown("<h1 style='text-align: center; color: #0074e9;'>🚀 쿠팡 키워드 분석 시스템</h1>", unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 전체 키워드", f"{len(df):,}개")
    m2.metric("🔥 최고 검색량", format_korean_unit(df['search_volume'].max()))
    m3.metric("👀 총 노출수", format_korean_unit(df['exposure'].sum()))
    
    total_exp = df['exposure'].sum()
    total_click = df['click'].sum()
    avg_ctr = (total_click / total_exp * 100) if total_exp > 0 else 0
    m4.metric("🎯 평균 클릭률", f"{avg_ctr:.2f}%")

    st.write("---")

    # --- 필터 및 검색 ---
    c1, c2 = st.columns([2, 1])
    search_query = c1.text_input("🔍 상품명/검색어 찾기", "")
    cat_filter = c2.selectbox("📌 카테고리 필터", ["전체"] + sorted(df['category'].unique().tolist()))

    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df['product_name'].str.contains(search_query, na=False, case=False) | 
                                  filtered_df['search_term'].str.contains(search_query, na=False, case=False)]
    if cat_filter != "전체":
        filtered_df = filtered_df[filtered_df['category'] == cat_filter]

    # --- [중요] 테이블 출력 설정 ---
    # 표기용 컬럼을 따로 만들지 않고, 정렬은 숫자로 하되 보여주는 것만 '만' 단위로 표시합니다.
    st.subheader(f"📋 분석 리스트 ({len(filtered_df):,}건)")
    
    # 가독성을 위해 데이터프레임의 숫자 컬럼을 한글 단위 텍스트로 변환한 복사본 생성
    display_df = filtered_df.copy()
    display_df['검색량(한글)'] = display_df['search_volume'].apply(format_korean_unit)
    display_df['노출수(한글)'] = display_df['exposure'].apply(format_korean_unit)
    display_df['클릭수(한글)'] = display_df['click'].apply(format_korean_unit)

    st.dataframe(
        display_df[['category', 'product_name', 'search_term', '검색량(한글)', '노출수(한글)', '클릭수(한글)', 'price_range']],
        use_container_width=True,
        hide_index=True
    )

    # --- 하단 그래프 ---
    if st.checkbox("📈 CTR 효율 상위 20 분석"):
        filtered_df['ctr'] = (filtered_df['click'] / filtered_df['exposure'] * 100).fillna(0)
        top_20 = filtered_df.sort_values(by='ctr', ascending=False).head(20)
        st.bar_chart(data=top_20, x='search_term', y='ctr', color="#0074e9")

st.caption("Coupang Keyword Admin | Powered by Supabase & Streamlit")
