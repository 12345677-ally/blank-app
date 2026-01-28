import streamlit as st
import pandas as pd
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(
    page_title="パーソナル貯金プランナー",
    page_icon="💰",
    layout="wide"
)

# --- セッション状態の初期化（データの一時保存用） ---
# 注意: 本格的な運用の場合は、ここをGoogle Sheetsやデータベース(Firestore等)に置き換える必要があります。
if "plans" not in st.session_state:
    st.session_state.plans = []

# --- ロジック関数 ---
def calculate_plan(income, rent, target_amount, location):
    """
    収入、家賃、場所に基づいて貯金可能額とアドバイスを計算する簡易ロジック
    """
    # 簡易的な生活費係数（地方と都市部で物価係数を変えるイメージ）
    living_cost_factor = 1.1 if location in ["東京都", "神奈川県", "大阪府"] else 0.95
    
    # 固定費以外の生活費（食費・光熱費など）の概算（収入の30% * 地域係数 と仮定）
    estimated_living_cost = (income * 0.3) * living_cost_factor
    
    # 貯金に回せる余剰資金（手取り - 家賃 - 想定生活費）
    disposable_income = income - rent - estimated_living_cost
    
    # 無理のない貯金額（余剰資金の70%を推奨とする）
    recommended_savings = max(0, int(disposable_income * 0.7))
    
    # 期間の計算
    if recommended_savings > 0:
        months_needed = -(-target_amount // recommended_savings) # 切り上げ計算
    else:
        months_needed = float('inf')

    # アドバイス生成
    advice = ""
    if rent > income * 0.35:
        advice += "⚠️ 家賃が収入の35%を超えています。固定費の見直しが最優先です。\n"
    elif recommended_savings > income * 0.2:
        advice += "✅ 素晴らしい収支バランスです。投資（NISA等）も検討しましょう。\n"
    
    if location == "東京都" and rent < 70000:
        advice += "ℹ️ 都内としては家賃をよく抑えられています。\n"

    return recommended_savings, months_needed, advice

# --- UI構築 ---

st.title("💰 パーソナル貯金プランナー")
st.markdown("あなたの状況に合わせて、最適な貯金のやり方を提案・管理します。")

# タブで機能を分ける
tab1, tab2 = st.tabs(["📝 新しいプランを作る", "📊 保存したプランを見る"])

with tab1:
    st.header("情報の入力")
    
    with st.form("planning_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("あなたの状況")
            income = st.number_input("月の手取り収入 (円)", min_value=0, value=250000, step=10000)
            rent = st.number_input("家賃・住宅ローン (円)", min_value=0, value=70000, step=5000)
            location = st.selectbox("お住まいの地域", ["北海道", "東京都", "神奈川県", "大阪府", "愛知県", "福岡県", "その他"])
        
        with col2:
            st.subheader("貯金の目的")
            goal_name = st.text_input("目的の名前（例：海外旅行、車購入）", "海外旅行")
            target_amount = st.number_input("目標金額 (円)", min_value=10000, value=500000, step=10000)

        submitted = st.form_submit_button("プランを診断・作成する")

    if submitted:
        rec_savings, months, advice_text = calculate_plan(income, rent, target_amount, location)
        
        st.divider()
        st.subheader("🔍 診断結果")
        
        r_col1, r_col2, r_col3 = st.columns(3)
        r_col1.metric("推奨される月々の貯金額", f"{rec_savings:,} 円")
        if months != float('inf'):
            r_col2.metric("目標達成までの期間", f"{months} ヶ月")
            today = datetime.now()
            # 簡易的な完了予定年月
            import dateutil.relativedelta
            end_date = today + dateutil.relativedelta.relativedelta(months=months)
            r_col3.metric("達成予定時期", end_date.strftime('%Y年%m月'))
        else:
            r_col2.metric("目標達成までの期間", "判定不能")
            r_col3.metric("達成予定", "-")

        if advice_text:
            st.info(f"💡 **アドバイス**\n\n{advice_text}")

        # 保存ボタン（フォームの外に配置）
        if rec_savings > 0:
            if st.button("このプランを保存する"):
                new_plan = {
                    "作成日": datetime.now().strftime("%Y-%m-%d"),
                    "目的": goal_name,
                    "目標金額": target_amount,
                    "月々の積立": rec_savings,
                    "期間(月)": months,
                    "エリア": location
                }
                st.session_state.plans.append(new_plan)
                st.success(f"「{goal_name}」のプランを保存しました！タブ「保存したプランを見る」で確認できます。")
        else:
            st.error("現在の収支では貯金が難しいようです。固定費を見直してみましょう。")

with tab2:
    st.header("保存したプラン一覧")
    
    if len(st.session_state.plans) > 0:
        # データフレームとして表示
        df = pd.DataFrame(st.session_state.plans)
        
        # 目標金額のフォーマットなどを整えて表示
        st.dataframe(
            df,
            column_config={
                "目標金額": st.column_config.NumberColumn(format="¥%d"),
                "月々の積立": st.column_config.NumberColumn(format="¥%d"),
            },
            use_container_width=True
        )
        
        # 個別カード表示
        st.subheader("プラン詳細")
        for i, plan in enumerate(st.session_state.plans):
            with st.expander(f"{plan['目的']} (目標: ¥{plan['目標金額']:,})"):
                st.write(f"**月々の目標:** ¥{plan['月々の積立']:,}")
                st.write(f"**達成までの期間:** 約 {plan['期間(月)']} ヶ月")
                st.progress(min(1.0, 1/plan['期間(月)']) if plan['期間(月)'] > 0 else 0, text="スタート地点")
                
                # 削除ボタン（簡易実装）
                if st.button("削除", key=f"del_{i}"):
                    st.session_state.plans.pop(i)
                    st.rerun()
    else:
        st.info("まだ保存されたプランはありません。「新しいプランを作る」タブで作成してください。")
