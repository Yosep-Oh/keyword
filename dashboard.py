import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
import re

st.set_page_config(layout="wide", page_title="쿠팡 키워드 정밀 분석기")

# --- 소수점 반올림 및 숫자 정리 함수 ---
def clean_numeric_value(val):
    try:
        # 소수점이 포함된 숫자를 찾아 둘째 자리까지 반올림
        if isinstance(val, float):
            return round(val, 2)
        if isinstance(val, str) and '.' in val:
            return round(float(val), 2)
        return val
    except:
        return val

# --- 데이터 불러오기 (data.txt 기반) ---
def load_file_data():
    try:
        # data.txt 내용을 한 줄씩 읽어오기
        with open('data.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 텍스트 파일의 줄바꿈 제거 및 데이터 프레임화
        data_list = [line.strip() for line in lines if line.strip()]
        df = pd.DataFrame(data_list, columns=["분석 결과 및 키워드 데이터"])
        
        # 데이터 내의 모든 소수점 숫자를 찾아 반올림 처리 (정규식 활용)
        def fix_text(text):
            return re.sub(r'\d+\.\d+', lambda m: str(round(float(m.group()), 2)), text)
        
        df["분석 결과 및 키워드 데이터"] = df["분석 결과 "].apply(fix_text) if "분석 결과 " in df else df["분석 결과 및 키워드 데이터"].apply(fix_text)
        
        return df
    except Exception as e:
        st.error(f"파일을 읽는 중 오류 발생: {e}")
        return pd.DataFrame()

# --- 메인 UI 구성 ---
st.title("📊 쿠팡 마켓 분석 대시보드 (파일 연동)")

df = load_file_data()

if not df.empty:
    st.info(f"현재 `data.txt`로부터 {len(df)}개의 분석 줄을 읽어왔습니다.")

    # AgGrid 설정 (기존 사장님 스타일 유지)
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    gb.configure_column("분석 결과 및 키워드 데이터", headerName="📋 분석 내용 및 키워드 리포트", width=800)
    
    grid_options = gb.build()

    # 표 출력
    AgGrid(
        df,
        gridOptions=grid_options,
        height=500,
        theme='alpine',
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
    )
else:
    st.warning("`data.txt` 파일이 비어있거나 찾을 수 없습니다.")

# 새로고침 버튼
if st.sidebar.button("💾 화면 새로고침"):
    st.rerun()
