import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from supabase import create_client, Client
import requests
import math

# --- Supabase 接続設定 ---
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception:
        st.error("Supabaseの接続設定が見つかりません。.streamlit/secrets.toml を確認してください。")
        st.stop()

supabase: Client = init_supabase()

# --- ページ設定 ---
st.set_page_config(page_title="パーソナル貯金プランナー ", page_icon="👛", layout="wide")

# --- WebAPI 2: 郵便番号検索API (ZipCloud) ---
def get_address_from_zip(zipcode):
    """郵便番号から住所と都道府県を取得する"""
    if not zipcode:
        return None, None
    url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={zipcode}"
    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        if data["status"] == 200 and data["results"]:
            res = data["results"][0]
            prefecture = res["address1"] # 都道府県 (例: 東京都)
            full_address = f"{res['address1']}{res['address2']}{res['address3']}"
            return prefecture, full_address
    except:
        pass
    return None, None

# --- 計算ロジック ---
def calculate_plan_by_months(income, rent, target_amount, months_input, prefecture):
    # 1. 地域係数の判定 (APIで取得した都道府県を使う)
    high_cost_areas = ["東京都", "神奈川県", "大阪府", "京都府", "兵庫県", "福岡県"]
    
    if prefecture in high_cost_areas:
        living_cost_factor = 1.10 # 都市部は高く設定
        area_type = "都市部"
    else:
        living_cost_factor = 0.90
        area_type = "地方・郊外"

    # 2. 計算
    required_monthly_savings = math.ceil(target_amount / months_input)
    estimated_living_cost = (income * 0.3) * living_cost_factor
    disposable_income = income - rent - estimated_living_cost 

    # 3. アドバイス作成
    advice = ""
    is
