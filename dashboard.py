import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode

# --- [1] 비밀번호 설정 ---
MY_PASSWORD = "141242" 

st.set_page_config(layout="wide", page_title="쿠팡 마켓 분석기")

# --- [2] 로그인 화면 로직 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 보안 접속 (사장님 전용)")
    pwd_input = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
        if pwd_input == MY_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop() 

# --- [3] 데이터 로드 및 표시 ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def clean_to_int(val):
    if pd.isna(val) or val == "": return 0
    s = str(val).replace('₩', '').replace(',', '').replace('%', '').strip()
    try:
        num = float(s.replace('만', '')) * 10000 if '만' in s else float(s)
        return int(round(num))
    except: return 0

@st.cache_data(ttl=300)
def load_all_data():
    all_rows = []
    step = 1000
    offset = 0
    while True:
        res = supabase.table("market_analysis").select("*").range(offset, offset + step - 1).execute()
        if not res.data: break
        all_rows.extend(res.data)
        if len(res.data) < step: break
        offset += step

    df = pd.DataFrame(all_rows)
    if not df.empty:
        # [강력 조치] 모든 텍스트 데이터의 앞뒤 공백을 제거하고 문자로 통일
        for col in ['main_keyword', 'product_name', 'sub_keyword']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        
        # 숫자 변환 (에러 방지용)
        df['검색량_숫자'] = df['keyword_vol'].apply(clean_to_int)
        df['노출수'] = df['keyword_exposure'].apply(clean_to_int)
        df['클릭수'] = df['keyword_clicks'].apply(clean_to_int)
        df['평균가'] = df['avg_price'].apply(clean_to_int)
    return df

# --- 출력 부분 (필터링 강화) ---
if not df.empty:
    main_list = sorted(df['main_keyword'].unique())
    target = st.sidebar.selectbox("🔎 메인 검색어 선택", main_list)
    
    # 메인 키워드로 1차 필터링
    view_df = df[df['main_keyword'] == target]
    st.title(f"📊 {target} 분석 리포트")
    
    products = sorted(view_df['product_name'].unique())
    
    for i, p_name in enumerate(products, 1):
        # 해당 상품의 데이터만 정확히 추출
        sub_data = view_df[view_df['product_name'] == p_name]
        
        with st.expander(f"{i}. {p_name} ({len(sub_data)}개 키워드)", expanded=(i<=3)):
            if not sub_data.empty:
                display_df = sub_data[['sub_keyword', 'keyword_vol', '검색량_숫자', '노출수', '클릭수', '평균가']]
                # AgGrid 설정... (기존과 동일)
                # ...
                st.write(display_df) # AgGrid가 안 나오면 일반 표라도 띄워보라는 뜻입니다.
            else:
                st.error("이 상품은 DB에 데이터가 매칭되지 않습니다.")

try:
    df = load_all_data()
    if not df.empty:
        st.sidebar.success("✅ 인증 완료")
        main_list = sorted(df['main_keyword'].unique())
        target = st.sidebar.selectbox("🔎 메인 검색어 선택", main_list)
        
        view_df = df[df['main_keyword'] == target]
        st.title(f"📊 {target} 분석 리포트")
        
        products = view_df['product_name'].unique()
        for i, p_name in enumerate(products, 1):
            with st.expander(f"{i}. {p_name}", expanded=True if i <= 3 else False):
                sub_data = view_df[view_df['product_name'] == p_name].copy()
                display_df = sub_data[['sub_keyword', 'keyword_vol', '검색량_숫자', '노출수', '클릭수', '평균가']]
                
                gb = GridOptionsBuilder.from_dataframe(display_df)
                gb.configure_column("sub_keyword", headerName="연관 키워드", pinned='left')
                gb.configure_column("keyword_vol", headerName="검색량(원문)")
                gb.configure_column("검색량_숫자", headerName="검색량(정렬)", type=["numericColumn"], sort="desc", valueFormatter="x.toLocaleString()")
                gb.configure_column("노출수", headerName="노출수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("클릭수", headerName="클릭수", type=["numericColumn"], valueFormatter="x.toLocaleString()")
                gb.configure_column("평균가", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
                
                grid_options = gb.build()
                AgGrid(display_df, gridOptions=grid_options, theme='alpine', columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS)
    else:
        st.info("데이터가 없습니다.")
except Exception as e:
    st.error(f"오류 발생: {e}")




