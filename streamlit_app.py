import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from supabase import create_client, Client
import requests
import math

# --- 1. Supabase 接続設定 ---
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

# --- 2. ページ設定 ---
st.set_page_config(page_title="パーソナル貯金プランナー", page_icon="👛", layout="wide")

# --- 3. WebAPI 関数 (ここが消えるとエラーになります！) ---
def get_address_from_zip(zipcode):
    """郵便番号APIから住所を取得"""
    if not zipcode:
        return None, None
    url = f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={zipcode}"
    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        if data["status"] == 200 and data["results"]:
            res = data["results"][0]
            prefecture = res["address1"]
            full_address = f"{res['address1']}{res['address2']}{res['address3']}"
            return prefecture, full_address
    except:
        pass
    return None, None

# --- 4. 計算ロジック ---
def calculate_plan_by_months(income, rent, target_amount, months_input, prefecture):
    # 地域係数の判定
    high_cost_areas = ["東京都", "神奈川県", "大阪府", "京都府", "兵庫県", "福岡県"]
    
    if prefecture in high_cost_areas:
        living_cost_factor = 1.10
        area_type = "都市部"
    else:
        living_cost_factor = 0.90
        area_type = "地方・郊外"

    # 計算
    required_monthly_savings = math.ceil(target_amount / months_input)
    estimated_living_cost = (income * 0.3) * living_cost_factor
    disposable_income = income - rent - estimated_living_cost 

    # アドバイス作成
    advice = ""
    is_feasible = True
    saving_ratio = required_monthly_savings / income if income > 0 else 0

    advice += f"📍 **地域: {prefecture} ({area_type})**\n生活費を **{living_cost_factor}倍** で計算しました。\n\n"

    if required_monthly_savings > disposable_income:
        advice += f"⚠️ **注意:** 月々 {required_monthly_savings:,}円 の貯金が必要です。\n{area_type}の生活費を考えると、カツカツ生活になるリスクが高いです。"
        is_feasible = False
    elif saving_ratio > 0.4:
        advice += f"⚠️ **注意:** 手取りの40%以上 ({int(saving_ratio*100)}%) を貯金する計画です。かなり節約が必要です。"
    else:
        advice += "✅ **判定:** 無理のない良いプランです！この調子で頑張りましょう。"

    return required_monthly_savings, advice, is_feasible, area_type

# --- 5. データベース操作関数 ---
