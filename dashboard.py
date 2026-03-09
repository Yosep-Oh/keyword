import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
import re

st.set_page_config(layout="wide", page_title="쿠팡 정밀 분석 대시보드")

# --- 숫자 추출 및 반올림 함수 ---
def clean_val(val):
    if not val: return 0
    # 1.44만 -> 14400 / 7,658 -> 7658 변환 및 반올림
    s = str(val).replace(',', '').replace('₩', '').replace('%', '').strip()
    if '만' in s:
        try: return round(float(s.replace('만', '')) * 10000, 2)
        except: return 0
    try: return round(float(s), 2)
    except: return 0

# --- [핵심] 쿠팡 텍스트 파싱 엔진 ---
def parse_coupang_report(text):
    # 1. 메인 키워드 정보 추출
    main_info = {}
    main_kw_match = re.search(r'“(.+?)” 검색 결과', text)
    if main_kw_match:
        main_info['메인키워드'] = main_kw_match.group(1)
        # 메인 지표 추출 (순서: 검색량, 노출, 클릭, 평균가)
        metrics = re.findall(r'([\d,.]+(?:만|%)?)\n(?:검색량|검색어 노출|클릭|평균가격)', text)
        if len(metrics) >= 4:
            main_info['검색량'] = metrics[0]
            main_info['노출'] = metrics[1]
            main_info['클릭'] = metrics[2]
            main_info['평균가격'] = metrics[3]

    # 2. 상품별(1~10등) 상세 데이터 추출
    # 숫자(순위) 뒤에 나오는 상품명과 "Top 10 검색어 보기" 사이를 자릅니다.
    items = re.split(r'\n(\d+)\n', text)
    product_details = []

    for i in range(1, len(items), 2):
        rank = items[i]
        content = items[i+1]
        
        # 상품명 (첫 줄)
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        p_name = lines[0] if lines else "알 수 없음"

        # 세부 키워드 블록 추출
        # 각 세부 키워드와 그에 딸린 4개 지표를 매칭
        sub_kw_pattern = r'([가-힣\s\w]+)\n([\d,.]+(?:만|%)?)\n검색량\n[\d,.]+(?:만|%)?\n([\d,.]+(?:만|%)?)\n검색어 노출\n[\d,.]+(?:만|%)?\n([\d,.]+(?:만|%)?)\n클릭\n[\d,.]+(?:만|%)?\n(₩[\d,.]+)\n평균가격'
        sub_matches = re.findall(sub_kw_pattern, content)

        for sub in sub_matches:
            product_details.append({
                "순위": int(rank),
                "상품명": p_name,
                "세부키워드": sub[0].strip(),
                "검색량": sub[1],
                "검색량_수치": clean_val(sub[1]),
                "노출_수치": clean_val(sub[2]),
                "클릭_수치": clean_val(sub[3]),
                "평균가": sub[4],
                "평균가_수치": clean_val(sub[4])
            })
            
    return main_info, pd.DataFrame(product_details)

# --- UI 레이아웃 ---
st.title("🚀 쿠팡 윙 마켓 정밀 분석 리포트")

try:
    with open('data.txt', 'r', encoding='utf-8') as f:
        raw_text = f.read()

    main_data, detail_df = parse_coupang_report(raw_text)

    # 1. 메인 키워드 요약 (상단 카드)
    if main_data:
        st.subheader(f"🔍 메인 키워드: {main_data.get('메인키워드')}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("검색량", main_data.get('검색량'))
        col2.metric("노출수", main_data.get('노출'))
        col3.metric("클릭수", main_data.get('클릭'))
        col4.metric("평균가격", main_data.get('평균가격'))
    
    st.divider()

    # 2. 1~10등 세부 키워드 분석 표
    if not detail_df.empty:
        st.subheader("📊 랭킹별 세부 키워드 성과 (소수점 반올림 및 정렬 가능)")
        
        gb = GridOptionsBuilder.from_dataframe(detail_df)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        
        # 컬럼 설정
        gb.configure_column("순위", pinned='left', width=80)
        gb.configure_column("상품명", width=250, tooltipField="상품명")
        gb.configure_column("세부키워드", pinned='left', width=180)
        
        # 수치 컬럼 (반올림된 숫자 기준 정렬)
        gb.configure_column("검색량_수치", headerName="검색량(정렬)", type=["numericColumn"], sort='desc')
        gb.configure_column("노출_수치", headerName="노출수", type=["numericColumn"])
        gb.configure_column("클릭_수치", headerName="클릭수", type=["numericColumn"])
        gb.configure_column("평균가_수치", headerName="평균단가", valueFormatter="'₩' + x.toLocaleString()")
        
        # 원본 텍스트 컬럼 숨기기
        gb.configure_columns(["검색량", "평균가"], hide=True)
        
        grid_options = gb.build()

        AgGrid(
            detail_df,
            gridOptions=grid_options,
            theme='alpine',
            height=600,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
        )
    else:
        st.warning("데이터 분석 결과가 없습니다. 'data.txt'의 내용을 확인해주세요.")

except Exception as e:
    st.error(f"분석 중 에러 발생: {e}")

if st.sidebar.button("🔄 최신 데이터로 새로고침"):
    st.rerun()
