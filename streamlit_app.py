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

# --- WebAPI : 郵便番号検索API (ZipCloud) ---
def get_address_from_zip(zipcode):
    """郵便番号から住所と都道府県を取得する"""
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
    high_cost_areas = ["東京都", "神奈川県", "大阪府", "京都府", "兵庫県","福岡県"]
    
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

# --- データベース操作関数 ---
def load_plans():
    response = supabase.table("savings_plans").select("*").order("created_at", desc=True).execute()
    return response.data

def save_plan(data):
    supabase.table("savings_plans").insert(data).execute()

def delete_plan(plan_id):
    supabase.table("savings_plans").delete().eq("id", plan_id).execute()

def save_log(plan_id, amount, memo):
    data = {"plan_id": plan_id, "amount": amount, "memo": memo}
    supabase.table("savings_logs").insert(data).execute()

def get_total_saved(plan_id):
    response = supabase.table("savings_logs").select("amount, created_at").eq("plan_id", plan_id).order("created_at", desc=True).execute()
    if response.data:
        total = sum([item['amount'] for item in response.data])
        return total, response.data 
    return 0, []

# --- UI構築 ---
st.title("👛 パーソナル貯金プランナー ")
st.markdown(get_motivational_quote())

if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = None

# セッション状態で住所を保持（検索ボタン用）
if "address_found" not in st.session_state:
    st.session_state.address_found = ""
if "prefecture_found" not in st.session_state:
    st.session_state.prefecture_found = "その他"

tab1, tab2 = st.tabs(["📝 新規プラン作成", "💰 貯金実績の管理"])

# === タブ1: 作成画面 ===
with tab1:
    st.header("目標と期間を設定")
    
    with st.form("planning_form"):
        col1, col2 = st.columns(2)
        with col1:
            goal_name = st.text_input("目的 (例: 結婚資金)", "海外旅行")
            target_amount = st.number_input("目標金額 (円)", value=500000, step=10000)
            months_input = st.number_input("達成したい期間 (ヶ月)", min_value=1, value=12, step=1)
            
        with col2:
            st.info("👇 正確な生活費判定のために住所を使います")
            
            # --- 郵便番号検索UI ---
            c_zip, c_btn = st.columns([2, 1])
            with c_zip:
                zipcode = st.text_input("郵便番号 (ハイフンなし)", max_chars=7, placeholder="1000001")
            with c_btn:
                st.write("") # レイアウト調整
                st.write("")
                if st.form_submit_button("住所検索"):
                    pref, addr = get_address_from_zip(zipcode)
                    if pref:
                        st.session_state.prefecture_found = pref
                        st.session_state.address_found = addr
                        st.success(f"📍 {addr}")
                    else:
                        st.error("見つかりませんでした")

            # 検索結果を表示（編集不可でもOK）
            st.text_input("住所 (自動入力)", value=st.session_state.address_found, disabled=True)
            
            income = st.number_input("月の手取り収入 (円)", value=250000, step=10000)
            rent = st.number_input("家賃 (円)", value=70000, step=5000)

        # フォームのメイン送信ボタン
        calc_submitted = st.form_submit_button("この条件で診断する", type="primary")

    if calc_submitted:
        # 検索されていなければ「その他」として計算
        pref_to_use = st.session_state.prefecture_found if st.session_state.prefecture_found else "その他"
        
        req_savings, advice, is_feasible, area_type = calculate_plan_by_months(
            income, rent, target_amount, months_input, pref_to_use
        )
        
        st.session_state.diagnosis_result = {
            "req_savings": req_savings,
            "months": months_input,
            "advice": advice,
            "goal_name": goal_name,
            "target_amount": target_amount,
            "area": f"{pref_to_use} ({area_type})", # 保存用に詳細を記録
            "is_feasible": is_feasible
        }

    if st.session_state.diagnosis_result:
        res = st.session_state.diagnosis_result
        
        st.divider()
        st.subheader(f"結果: 月々 {res['req_savings']:,} 円 の貯金が必要です")
        
        if res["advice"]:
            if res["is_feasible"]:
                st.success(res["advice"])
            else:
                st.error(res["advice"])
        
        # グラフ描画
        data = []
        current_savings = 0
        for i in range(res["months"] + 1):
            data.append({"月数": i, "貯金額": current_savings, "タイプ": "計画"})
            current_savings += res["req_savings"]
            if current_savings > res["target_amount"]:
                current_savings = res["target_amount"]
        
        chart = alt.Chart(pd.DataFrame(data)).mark_line(point=True).encode(
            x='月数', y='貯金額', tooltip=['月数', '貯金額']
        ).properties(title="目標達成シミュレーション")
        st.altair_chart(chart, use_container_width=True)

        if st.button("このプランをクラウドに保存する"):
            try:
                save_data = {
                    "goal_name": res["goal_name"],
                    "target_amount": res["target_amount"],
                    "monthly_savings": res["req_savings"],
                    "months_needed": res["months"],
                    "area": res["area"],
                    "memo": res["advice"]
                }
                save_plan(save_data)
                st.success("✅ 保存しました！「貯金実績の管理」タブを見てください。")
                st.session_state.diagnosis_result = None
            except Exception as e:
                st.error(f"保存エラー: {e}")

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
                        memo_in = st.text_input("メモ (任意)", key=f"memo_{plan['id']}")
                        if st.form_submit_button("記録を追加"):
                            save_log(plan['id'], amount_in, memo_in)
                            st.rerun()

                with c2:
                    st.caption("プラン情報")
                    st.write(f"地域: {plan.get('area', '-')}") # 地域情報を表示
                    st.write(f"月々の目標: ¥{plan['monthly_savings']:,}")
                    try:
                        date_str = plan['created_at'][:10]
                    except:
                        date_str = "-"
                    st.write(f"作成日: {date_str}")
                    
                    if st.button("プランを削除", key=f"del_{plan['id']}"):
                        delete_plan(plan['id'])
                        st.rerun()

                if logs:
                    st.divider()
                    st.caption("📜 これまでの履歴")
                    df_logs = pd.DataFrame(logs)
                    df_logs = df_logs.rename(columns={"amount": "金額", "created_at": "日時"})
                    st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("保存されたプランはありません。「新規プラン作成」タブで作ってみましょう！")
