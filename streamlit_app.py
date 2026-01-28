import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from supabase import create_client, Client

# --- Supabase 接続設定 ---
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

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

def save_plan(goal_name, target_amount, rec_savings, months, location, advice):
    """プランを新規作成"""
    data = {
        "goal_name": goal_name,
        "target_amount": target_amount,
        "monthly_savings": rec_savings,
        "months_needed": months,
        "area": location,
        "memo": advice
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
    response = supabase.table("savings_logs").select("amount").eq("plan_id", plan_id).execute()
    if response.data:
        # dataは [{"amount": 1000}, {"amount": 2000}] のような形式なので合計する
        total = sum([item['amount'] for item in response.data])
        return total, response.data # 合計と、履歴データを返す
    return 0, []

# --- UI構築 ---
st.title("📈 パーソナル貯金プランナー Pro")

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

    if submitted:
        rec_savings, months, advice = calculate_plan(income, rent, target_amount, location)
        
        st.divider()
        if rec_savings > 0:
            st.success(f"推奨積立額: 月々 {rec_savings:,} 円 (期間: {months}ヶ月)")
            if advice:
                st.info(advice)
            
            # シミュレーション・グラフ
            data = []
            current_savings = 0
            for i in range(months + 1):
                data.append({"月数": i, "貯金額": current_savings, "タイプ": "計画"})
                current_savings += rec_savings
                if current_savings > target_amount:
                    current_savings = target_amount
            
            chart = alt.Chart(pd.DataFrame(data)).mark_line(point=True).encode(
                x='月数', y='貯金額', tooltip=['月数', '貯金額']
            ).properties(title="目標達成シミュレーション")
            st.altair_chart(chart, use_container_width=True)

            if st.button("このプランをクラウドに保存する"):
                save_plan(goal_name, target_amount, rec_savings, months, location, advice)
                st.success("✅ 保存しました！「貯金実績の管理」タブを見てください。")
        else:
            st.error("現在の収支バランスでは貯金が難しいようです。")

# === タブ2: 実績管理画面 ===
with tab2:
    st.header("現在進行中のプラン")
    
    plans = load_plans()
    
    if plans:
        for plan in plans:
            # 各プランの現在の貯蓄額を取得
            current_total, logs = get_total_saved(plan['id'])
            progress = min(1.0, current_total / plan['target_amount'])
            
            # カード表示
            with st.expander(f"🎯 {plan['goal_name']} (現在: ¥{current_total:,} / 目標: ¥{plan['target_amount']:,})", expanded=True):
                
                # 進捗バー
                st.write(f"**達成率: {int(progress * 100)}%** (あと ¥{plan['target_amount'] - current_total:,})")
                st.progress(progress)
                
                c1, c2 = st.columns([2, 1])
                
                # 左側：実績入力フォーム
                with c1:
                    st.subheader("💰 貯金を記録する")
                    with st.form(key=f"log_form_{plan['id']}"):
                        amount_in = st.number_input("今回貯金した金額 (円)", min_value=1, value=plan['monthly_savings'], step=1000, key=f"amt_{plan['id']}")
                        memo_in = st.text_input("メモ (任意)", key=f"memo_{plan['id']}")
                        if st.form_submit_button("記録を追加"):
                            save_log(plan['id'], amount_in, memo_in)
                            st.rerun()

                # 右側：プラン情報と削除
                with c2:
                    st.caption("プラン情報")
                    st.write(f"月々の目標: ¥{plan['monthly_savings']:,}")
                    st.write(f"開始日: {plan['created_at'][:10]}")
                    if st.button("プランを削除", key=f"del_{plan['id']}"):
                        delete_plan(plan['id'])
                        st.rerun()

                # 下部：履歴の表示
                if logs:
                    st.divider()
                    st.caption("📜 これまでの履歴")
                    # 最新順に並べて表示
                    df_logs = pd.DataFrame(logs)
                    # もしcreated_atがあれば日付も出せるが、今回は簡易的に金額のみ表示
                    st.dataframe(df_logs, use_container_width=True)

    else:
        st.info("保存されたプランはありません。「新規プラン作成」タブで作ってみましょう！")
