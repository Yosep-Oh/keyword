import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [1] 페이지 설정 및 스타일 (UI 강화) ---
st.set_page_config(layout="wide", page_title="오셀러 쿠팡 분석기", page_icon="📊")

# 모바일 가독성을 위한 커스텀 CSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stSelectbox label { font-size: 1.1rem; font-weight: bold; color: #1f77b4; }
    .stHeader { color: #2c3e50; }
    div[data-testid="stExpander"] { border: 1px solid #dee2e6; border-radius: 10px; background: white; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- [2] 보안 접속 ---
MY_PASSWORD = "141242" 

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 오셀러 전용 보안 채널")
    st.info("사장님, 접속을 위해 비밀번호를 입력해 주세요.")
    pwd_input = st.text_input("비밀번호", type="password")
    if st.button("데이터 분석 시작", use_container_width=True):
        if pwd_input == MY_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

# --- [3] 수파베이스 데이터 로드 ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def clean_to_int(val):
    if pd.isna(val) or val == "": return 0
    # ₩, 콤마, % 제거 및 '만' 단위 처리
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').strip()
    try:
        if '만' in s:
            num = float(s.replace('만', '')) * 10000
        else:
            num = float(s)
        return int(round(num))
    except: return 0

@st.cache_data(ttl=600) # 10분간 캐시 유지
def load_all_data():
    all_rows = []
    step = 1000
    offset = 0
    with st.spinner("데이터베이스 최신화 중..."):
        while True:
            res = supabase.table("market_analysis").select("*").range(offset, offset + step - 1).execute()
            if not res.data: break
            all_rows.extend(res.data)
            if len(res.data) < step: break
            offset += step
    
    df = pd.DataFrame(all_rows)
    if not df.empty:
        # 데이터 정제 및 공백 제거
        for col in ['main_keyword', 'product_name', 'sub_keyword']:
            df[col] = df[col].astype(str).str.strip()
        
        # 숫자 변환
        df['검색량_숫자'] = df['keyword_vol'].apply(clean_to_int)
        df['노출수'] = df['keyword_exposure'].apply(clean_to_int)
        df['클릭수'] = df['keyword_clicks'].apply(clean_to_int)
        df['평균가'] = df['avg_price'].apply(clean_to_int)
    return df

# --- [4] 메인 대시보드 ---
try:
    df = load_all_data()
    
    if not df.empty:
        # 사이드바 설정
        st.sidebar.header("📊 분석 필터")
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🎯 메인 키워드", main_list)
        
        view_df = df[df['main_keyword'] == target]
        
        st.title(f"🚀 {target} 마켓 분석")
        st.write(f"현재 이 시장에서 분석된 상품은 총 **{len(view_df['product_name'].unique())}개**입니다.")
        
        # 상품 선택 UI
        products = sorted(view_df['product_name'].unique())
        selected_product = st.selectbox("🔎 분석할 상품명을 선택하세요", ["--- 상품 선택 ---"] + products)
        
        if selected_product == "--- 상품 선택 ---":
            st.divider()
            st.warning("위 목록에서 상품을 선택하면 상세 키워드 분석표가 나타납니다.")
            # 요약 차트나 통계 추가 가능
        else:
            sub_data = view_df[view_df['product_name'] == selected_product].copy()
            
            # 상단 요약 카드 (UI 강조)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("연관 키워드 수", f"{len(sub_data)}개")
            with col2:
                top_vol = sub_data['검색량_숫자'].max()
                st.metric("최대 검색량", f"{top_vol:,}")
            with col3:
                avg_p = int(sub_data['평균가'].mean())
                st.metric("평균 시장가", f"₩{avg_p:,}")
            
            st.divider()
            st.subheader(f"📍 {selected_product} 상세 분석")

            if not sub_data.empty:
                # 보여줄 컬럼만 선택
                display_df = sub_data[['sub_keyword', '검색량_숫자', '노출수', '클릭수', '평균가']]
                
                gb = GridOptionsBuilder.from_dataframe(display_df)
                
                # 컬럼별 세부 설정 (UI 디자인)
                gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left', minWidth=140)
                gb.configure_column("검색량_숫자", headerName="검색량", type=["numericColumn"], sort="desc", valueFormatter="x.toLocaleString()")
                gb.configure_column("노출수", headerName="노출수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("클릭수", headerName="클릭수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("평균가", headerName="평균단가", type=["numericColumn"], valueFormatter="'₩' + x.toLocaleString()")
                
                # 모바일 대응 설정
                grid_options = gb.build()
                
                AgGrid(
                    display_df, 
                    gridOptions=grid_options, 
                    theme='alpine', # 세련된 테마
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                    height=450, 
                    allow_unsafe_jscode=True
                )
            else:
                st.error("해당 상품의 상세 데이터를 찾을 수 없습니다.")

    else:
        st.warning("데이터베이스에 연결되었으나 표시할 데이터가 없습니다.")

except Exception as e:
    st.error(f"⚠️ 시스템 오류 발생: {e}")

# --- [5] 푸터 ---
st.markdown("---")
st.caption("© 2026 오셀러 쿠팡 마켓 분석 대시보드 v1.2.0")
