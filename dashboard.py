import streamlit as st
from supabase import create_client, Client
import pandas as pd

# [중요] Streamlit 페이지 설정은 무조건 최상단에 위치해야 에러가 나지 않습니다.
st.set_page_config(page_title="쿠팡 키워드 정밀 분석", layout="wide")

# 1. 보안 및 접속 설정
try:
    url = st.secrets["https://aywlsumqnuqhckpmftzr.supabase.co"]
    key = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF5d2xzdW1xbnVxaGNrcG1mdHpyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2NjU1MTEsImV4cCI6MjA4ODI0MTUxMX0.cBGF9L8YP0EydrCwQEYRdKcK557CJAIp78YQw9w_mtw"]
except KeyError:
    st.error("❌ secrets.toml 설정 확인 필요")
    st.stop()

@st.cache_resource
def init_connection():
    return create_client(url, key)

supabase = init_connection()

# --- 숫자를 한글 단위로 변환하는 함수 ---
def format_korean_unit(num):
    if num >= 10000:
        return f"{num / 10000:.2f}만".replace('.00', '')
    elif num >= 1000:
        return f"{num / 1000:.1f}천".replace('.0', '')
    return str(int(num))

# --- 한글 단위를 숫자로 변환하는 함수 ---
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
        # [수정] 테이블명을 새롭게 만든 'coupang_keywords'로 변경
        res = supabase.table("coupang_keywords").select("*").range(offset, offset + page_size - 1).execute()
        data = res.data
        all_data.extend(data)
        if len(data) < page_size: break
        offset += page_size
    df = pd.DataFrame(all_data)
    
    # [수정] 계산을 위해 숫자로 변환 (click -> clicks 로 컬럼명 변경)
    if not df.empty:
        for col in ['search_volume', 'exposure', 'clicks']:
            df[col] = df[col].apply(convert_unit)
    return df

df = get_all_data()

if not df.empty:
    st.markdown("<h1 style='text-align: center; color: #0074e9;'>🚀 쿠팡 랭킹 & 키워드 정밀 분석</h1>", unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 수집된 세부 키워드", f"{len(df):,}개")
    m2.metric("🔥 최고 검색량", format_korean_unit(df['search_volume'].max()))
    m3.metric("👀 총 노출수", format_korean_unit(df['exposure'].sum()))
    
    # [수정] total_click -> total_clicks 로 변경
    total_exp = df['exposure'].sum()
    total_clicks = df['clicks'].sum()
    avg_ctr = (total_clicks / total_exp * 100) if total_exp > 0 else 0
    m4.metric("🎯 전체 평균 클릭률", f"{avg_ctr:.2f}%")

    st.write("---")

    # --- 필터 및 검색 ---
    c1, c2 = st.columns([2, 1])
    search_query = c1.text_input("🔍 상품명/키워드 찾기", "")
    cat_filter = c2.selectbox("📌 카테고리 필터", ["전체"] + sorted(df['category'].dropna().unique().tolist()))

    filtered_df = df.copy()
    if search_query:
        # [수정] search_term 대신 top_keyword 사용
        filtered_df = filtered_df[filtered_df['product_name'].str.contains(search_query, na=False, case=False) | 
                                  filtered_df['top_keyword'].str.contains(search_query, na=False, case=False)]
    if cat_filter != "전체":
        filtered_df = filtered_df[filtered_df['category'] == cat_filter]

    st.subheader(f"📋 키워드 분석 리스트 ({len(filtered_df):,}건)")
    
    # 가독성을 위해 데이터프레임 복사본 생성
    display_df = filtered_df.copy()
    display_df['검색량'] = display_df['search_volume'].apply(format_korean_unit)
    display_df['노출수'] = display_df['exposure'].apply(format_korean_unit)
    display_df['클릭수'] = display_df['clicks'].apply(format_korean_unit)

    # [수정] 새롭게 추가된 메인검색어, 랭킹, 평균가격 컬럼까지 모두 예쁘게 매핑
    display_df = display_df.rename(columns={
        'search_keyword': '메인 검색어',
        'category': '카테고리',
        'product_rank': '상품 랭킹',
        'product_name': '실제 판매 상품',
        'top_keyword': '유입 키워드 (Top 10)',
        'avg_price': '평균 가격'
    })

    # 화면에 보여줄 컬럼 순서 지정
    st.dataframe(
        display_df[['메인 검색어', '카테고리', '상품 랭킹', '실제 판매 상품', '유입 키워드 (Top 10)', '검색량', '노출수', '클릭수', '평균 가격']],
        use_container_width=True,
        hide_index=True
    )

    # --- 하단 그래프 ---
    if st.checkbox("📈 키워드별 CTR(클릭률) 상위 20 분석"):
        # [수정] clicks 컬럼으로 계산
        filtered_df['ctr'] = (filtered_df['clicks'] / filtered_df['exposure'] * 100).fillna(0)
        top_20 = filtered_df.sort_values(by='ctr', ascending=False).head(20)
        # [수정] x축을 top_keyword로 변경
        st.bar_chart(data=top_20, x='top_keyword', y='ctr', color="#0074e9")

else:
    st.warning("데이터베이스에 아직 데이터가 없거나 연결에 실패했습니다.")

st.caption("Coupang Keyword Admin | Powered by Supabase & Streamlit")
