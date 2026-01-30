import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from supabase import create_client, Client

# --- Supabase 接続設定 ---
# .streamlit/secrets.toml が正しく設定されている前提です
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
st.set_page_config(page_title="パーソナル貯金プランナー Pro", page_icon="📈", layout="wide")

# --- ロジック関数 ---
def calculate_plan(income, rent, target_amount, location):
    living_cost_factor = 1.1 if location in ["東京都", "神奈川県", "大阪府"] else 0.95
    estimated_living_cost = (income * 0.3) * living_cost_factor
    disposable_income = income - rent - estimated_living_cost
    recommended_savings = max(0, int(disposable_income * 0.7))
    
    if recommended_savings > 0:
        months_needed = -(-target_amount // recommended_savings)
    else:
        months_needed = 0

    advice = ""
    if rent > income * 0.35:
        advice += "⚠️ 家賃負担が大きめです (収入の35%超)。\n"
    elif recommended_savings > income * 0.2:
        advice += "✅ 良いペースです！投資も検討しましょう。\n"
    
    return recommended_savings, months_needed, advice

# --- データベース操作関数 ---
def load_plans():
    """プラン一覧を取得"""
    # 修正: テーブル名は統一して 'savings_plans' を使用
    response = supabase.table("savings_plans").select("*").order("created_at", desc=True).execute()
    return response.data

def save_plan(goal_name, target_amount, rec_savings, months, location, advice):
    """プランを新規作成"""
    data = {
        "goal_name": goal_name,
        "target_amount": target_amount,
        "monthly_savings": rec_savings,
        "months_needed": months,
        "area": location,
        "memo": advice,
        # created_at はSupabase側でデフォルト設定されていれば不要ですが、念のため
        # "created_at": datetime.now().isoformat() 
    }
    supabase.table("savings_plans").insert(data).execute()

def delete_plan(plan_id):
    """プランを削除"""
    supabase.table("savings_plans").delete().eq("id", plan_id).execute()

# ▼▼▼ 追加機能: 実績関連 ▼▼▼
def save_log(plan_id, amount, memo):
    """貯金実績を記録"""
    data = {"plan_id": plan_id, "amount": amount, "memo": memo}
    supabase.table("savings_logs").insert(data).execute()

def get_total_saved(plan_id):
    """そのプランで合計いくら貯まったか取得"""
    response = supabase.table("savings_logs").select("amount, created_at").eq("plan_id", plan_id).order("created_at", desc=True).execute()
    if response.data:
        total = sum([item['amount'] for item in response.data])
        return total, response.data 
    return 0, []
