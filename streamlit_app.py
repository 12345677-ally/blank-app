import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from supabase import create_client, Client

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
    response = supabase.table("savings_plans").select("*").order("created_at", desc=True).execute()
    return response.data

def save_plan(data):
    """プランを新規作成"""
    supabase.table("savings_plans").insert(data).execute()

def delete_plan(plan_id):
    """プランを削除"""
    supabase.table("savings_plans").delete().eq("id", plan_id).execute()

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

# --- UI構築 ---
st.title("📈 パーソナル貯金プランナー Pro")

# セッション状態の初期化（診断結果を記憶するため）
if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = None

tab1, tab2 = st.tabs(["📝 新規プラン作成", "💰 貯金実績の管理"])

# === タブ1: 作成画面 ===
with tab1:
    st.header("条件を入力して診断")
    with st.form("planning_form"):
        col1, col2 = st.columns(2)
        with col1:
            income = st.number_input("月の手取り収入 (円)", value=250000, step=10000)
            rent = st.number_input("家賃 (円)", value=70000, step=5000)
            location = st.selectbox("地域", ["北海道", "東京都", "神奈川県", "大阪府", "福岡県", "その他"])
        with col2:
            goal_name = st.text_input("目的 (例: 結婚資金)", "海外旅行")
            target_amount = st.number_input("目標金額 (円)", value=500000, step=10000)

        submitted = st.form_submit_button("診断・作成")

    # 診断ボタンが押されたら、結果を「記憶」する
    if submitted:
        rec_savings, months, advice = calculate_plan(income, rent, target_amount, location)
        st.session_state.diagnosis_result = {
            "rec_savings": rec_savings,
            "months": months,
            "advice": advice,
            "goal_name": goal_name,
            "target_amount": target_amount,
            "area": location,
            "income": income # 参考用
        }

    # 記憶された結果があれば表示（ボタンを押した後も消えない）
    if st.session_state.diagnosis_result:
        res = st.session_state.diagnosis_result
        
        st.divider()
        if res["rec_savings"] > 0:
            st.success(f"推奨積立額: 月々 {res['rec_savings']:,} 円 (期間: {res['months']}ヶ月)")
            if res["advice"]:
                st.info(res["advice"])
            
            # グラフ描画
            data = []
            current_savings = 0
            for i in range(res["months"] + 1):
                data.append({"月数": i, "貯金額": current_savings, "タイプ": "計画"})
                current_savings += res["rec_savings"]
                if current_savings > res["target_amount"]:
                    current_savings = res["target_amount"]
            
            chart = alt.Chart(pd.DataFrame(data)).mark_line(point=True).encode(
                x='月数', y='貯金額', tooltip=['月数', '貯金額']
            ).properties(title="目標達成シミュレーション")
            st.altair_chart(chart, use_container_width=True)

            # 保存ボタン
            if st.button("このプランをクラウドに保存する"):
                try:
                    save_data = {
                        "goal_name": res["goal_name"],
                        "target_amount": res["target_amount"],
                        "monthly_savings": res["rec_savings"],
                        "months_needed": res["months"],
                        "area": res["area"],
                        "memo": res["advice"]
                    }
                    save_plan(save_data)
                    st.success("✅ 保存しました！「貯金実績の管理」タブを見てください。")
                    # 保存したら記憶をリセット（連続保存防止）
                    st.session_state.diagnosis_result = None
                except Exception as e:
                    st.error(f"保存エラー: {e}")
        else:
            st.error("現在の収支バランスでは貯金が難しいようです。")

# === タブ2: 実績管理画面 ===
with tab2:
    st.header("現在進行中のプラン")
    
    try:
        plans = load_plans()
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
        plans = []
    
    if plans:
        for plan in plans:
            current_total, logs = get_total_saved(plan['id'])
            if plan['target_amount'] > 0:
                progress = min(1.0, current_total / plan['target_amount'])
            else:
                progress = 0
            
            with st.expander(f"🎯 {plan['goal_name']} (現在: ¥{current_total:,} / 目標: ¥{plan['target_amount']:,})", expanded=True):
                st.write(f"**達成率: {int(progress * 100)}%** (あと ¥{plan['target_amount'] - current_total:,})")
                st.progress(progress)
                
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.subheader("💰 貯金を記録する")
                    with st.form(key=f"log_form_{plan['id']}"):
                        amount_in = st.number_input("今回貯金した金額 (円)", min_value=1, value=int(plan['monthly_savings']), step=1000, key=f"amt_{plan['id']}")
                        memo_in = st.text_input("メモ (任意)", key=f"memo
