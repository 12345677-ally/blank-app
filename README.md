# 💰 パーソナル貯金プランナー (Personal Savings Planner)

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?logo=supabase&logoColor=white)

毎月の収支と目標金額を入力することで、目標達成までの期間や資産推移をシミュレーションできるWebアプリケーションです。
日々の生活費や家賃を考慮し、無理のない貯金計画を立てるサポートをします。

## 🚀 デモアプリ (Demo)
以下のURLからブラウザ上でアプリを試すことができます。

👉 **https://share.streamlit.io/your-account/your-repo/main/app.py**
> **Note:** アプリがスリープ状態（画面が黒くなっている場合）のときは、画面中央の青い **「Yes, get this app back up!」** ボタンを押して起動してください。

## 🌟 主な機能 (Features)
* **💸 収支シミュレーション**
    * 収入、家賃、生活費係数を入力し、月々の「現実的な貯金可能額」を自動算出します。
* **🎯 目標設定と期間予測**
    * 「いつまでに、いくら貯めたいか」を設定すると、目標達成に必要な期間を計算します。
* **📈 資産推移の可視化**
    * 将来の資産が増えていく様子を、Altairを使ったインタラクティブなグラフで確認できます。
* **☁️ クラウド保存 (Supabase連携)**
    * 作成したプランや設定データをクラウドデータベース(Supabase)に保存し、いつでも呼び出せます。

## 🛠 セットアップ方法 (Installation)
ローカル環境で実行するための手順です。

### 1. 依存ライブラリのインストール
Python環境がインストールされていることを確認し、以下のコマンドを実行してください。
