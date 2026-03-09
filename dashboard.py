import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
import re

st.set_page_config(layout="wide", page_title="쿠팡 윙 데이터 분석기")

# --- [데이터 분석 엔진] 텍스트에서 핵심 정보 추출 ---
def parse_coupang_data(text):
    # 1. 상품별 섹션 나누기 (숫자만 있는 라인 기준: 1, 2, 3...)
    items = re.split(r'\n(\d+)\n', text)
    
    results = []
    for i in range(1, len(items), 2):
        rank = items[i]
        content = items[i+1]
        
        # 상품명 추출 (첫 번째 줄)
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if not lines: continue
        p_name = lines[0]
        
        # 숫자 수치들 추출 (검색량, 노출, 클릭 등)
        # 1.44만, 1167.19%, 7,658 같은 형태를 모두 찾아냄
        numbers = re.findall(r'(\d[\d,.]*(?:만|%)?)', content)
        
        # 소수점 반올림 처리 함수
        def format_num(n_str):
            n_str = n_str.replace(',', '')
            if '%' in n_str:
                val = float(n_str.replace('%', ''))
                return f"{round(val, 2)}%"
            if '만' in n_str:
                val = float(n_str.replace('만', ''))
                return f"{round(val, 2)}만"
            try:
                val = float(n_str)
                return str(round(val, 2))
            except:
                return n_str

        formatted_nums = [format_num(n) for n in numbers[:10]] # 주요 수치 10개만 추출
        
        results.append({
            "순위": rank,
            "상품명": p_name,
            "데이터 요약": " | ".join(formatted_nums)
        })
    
    return pd.DataFrame(results)

# --- 메인 UI ---
st.title("📊 쿠팡 검색 결과 정밀 분석")

try:
    with open('data.txt', 'r', encoding='utf-8') as f:
        raw_text = f.read()

    df = parse_coupang_data(raw_text)

    if not df.empty:
        st.success(f"총 {len(df)}개의 상품 분석 완료 (소수점 반올림 적용)")
        
        # AgGrid 설정
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        gb.configure_column("상품명", width=400, pinned='left')
        gb.configure_column("데이터 요약", width=500)
        
        grid_options = gb.build()

        AgGrid(
            df,
            gridOptions=grid_options,
            theme='alpine',
            height=600,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
        )
    else:
        st.warning("데이터를 분석할 수 없습니다. 형식을 확인해주세요.")

except FileNotFoundError:
    st.error("data.txt 파일이 없습니다.")
except Exception as e:
    st.error(f"분석 중 오류: {e}")

if st.sidebar.button("🔄 데이터 새로고침"):
    st.rerun()
