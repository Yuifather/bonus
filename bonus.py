import streamlit as st
import pandas as pd
import math

# 환율/소수점 세팅
default_rates = {
    'USD': 1, 'EUR': 1.1, 'GBP': 1.25, 'JPY': 0.007,
    'BTC': 65000, 'ETH': 3500, 'XRP': 0.5, 'USDT': 1, 'USDC': 1,
}
default_digits = {
    'USD': 2, 'EUR': 2, 'GBP': 2, 'JPY': 0,
    'BTC': 8, 'ETH': 6, 'XRP': 1, 'USDT': 2, 'USDC': 2,
}

st.title('멀티통화 입출금/보너스 시뮬레이터')

# 환율/자릿수 UI & 동기화
if 'currencies' not in st.session_state:
    st.session_state['currencies'] = {
        code: {'rate': float(default_rates[code]), 'digit': int(default_digits[code])}
        for code in default_rates
    }

st.sidebar.markdown("### [환율 및 소수점 수정]")
edited = False
new_rates = {}
new_digits = {}

for code in default_rates:
    c = st.sidebar.container()
    rate = c.number_input(
        f"{code} 환율(대표통화={list(default_rates.keys())[0]}=1)",
        min_value=0.000001, step=0.000001,
        value=float(st.session_state['currencies'][code]['rate']),
        key=f"rate_{code}", format="%.6f"
    )
    digit = c.number_input(
        f"{code} 소수점(digit)", min_value=0, max_value=8, step=1,
        value=int(st.session_state['currencies'][code]['digit']),
        key=f"digit_{code}"
    )
    new_rates[code] = float(rate)
    new_digits[code] = int(digit)

if st.sidebar.button("환율/소수점 적용(모두 초기화됨)"):
    st.session_state['currencies'] = {
        code: {'rate': new_rates[code], 'digit': new_digits[code]} for code in default_rates
    }
    # 초기화 동작
    st.session_state.accounts = {
        code: {'balance': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
        for code in default_rates
    }
    st.session_state['누적보너스_USD'] = 0
    st.success("환율/소수점 변경됨: 전체 초기화 완료!")

currencies = st.session_state['currencies']

# 초기화 버튼
if st.sidebar.button("초기화(RESET)"):
    st.session_state.accounts = {
        code: {'balance': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
        for code in currencies
    }
    st.session_state['누적보너스_USD'] = 0
    st.success("모든 계좌 정보가 초기화 되었습니다.")

# 세션 상태 초기화(최초 진입 or 초기화 후)
if 'accounts' not in st.session_state:
    st.session_state.accounts = {
        code: {'balance': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
        for code in currencies
    }
if '누적보너스_USD' not in st.session_state:
    st.session_state['누적보너스_USD'] = 0

# 입금/출금 파트
st.sidebar.header("입금/출금")
action = st.sidebar.radio("동작", ["입금", "출금"])
currency = st.sidebar.selectbox("통화", list(currencies.keys()))
amount = st.sidebar.number_input("금액", min_value=0.0, step=0.01, format="%.8f")

def floor_to_digit(val, digit):
    p = 10**digit
    return math.floor(val * p) / p

def 환산금액(val, from_code, to_code):
    usd_val = val * currencies[from_code]['rate']
    return usd_val / currencies[to_code]['rate']

# 입금 처리 및 보너스 지급
if st.sidebar.button("실행"):
    acc = st.session_state.accounts[currency]
    rate = currencies[currency]['rate']
    digit = currencies[currency]['digit']
    누적보너스 = st.session_state['누적보너스_USD']
    amount = float(amount)

    if action == "입금":
        acc['balance'] += amount
        if 누적보너스 == 0:
            fifty = min(amount, 500 / rate) * 0.5
            excess = max(0, amount - 500 / rate) * 0.2
            raw_bonus = fifty + excess
        else:
            raw_bonus = amount * 0.2
        raw_bonus_usd = raw_bonus * rate
        remain_bonus_usd = max(0, 20000 - 누적보너스)
        apply_bonus_usd = min(raw_bonus_usd, remain_bonus_usd)
        apply_bonus = floor_to_digit(apply_bonus_usd / rate, digit)
        acc['bonus'] += apply_bonus
        st.session_state['누적보너스_USD'] += apply_bonus * rate
        st.success(f"{currency} {amount} 입금 및 보너스 {apply_bonus} 지급")
    elif action == "출금":
        if acc['balance'] < amount:
            st.error("잔액 부족!")
        else:
            net_capital = acc['balance'] - acc['bonus'] - acc['credit'] - acc['restricted']
            출금가능 = max(0, net_capital)
            출금액 = min(amount, 출금가능)
            acc['balance'] -= 출금액
            after_capital = acc['balance'] - acc['bonus'] - acc['credit'] - acc['restricted']
            after_capital_usd = after_capital * currencies[currency]['rate']
            if after_capital_usd < 10:
                acc['bonus'] = 0
            elif after_capital <= 0:
                acc['bonus'] = 0
            else:
                acc['bonus'] = floor_to_digit(acc['bonus'] * after_capital / 출금가능, digit)
            st.success(f"{currency} {출금액} 출금 완료 (보너스 자동 차감)")

# 통화별 현황 표
accounts = st.session_state.accounts
df = pd.DataFrame(accounts).T
st.write("### 통화별 계좌 현황")
st.dataframe(df.style.format({"balance": "{:.8f}", "bonus": "{:.8f}"}))

# 토탈(합산) 계산
st.write("---")
합산기준통화 = st.selectbox("합산(환산) 기준통화(=아래 첨자):", list(currencies.keys()), index=0)
main_digit = currencies[합산기준통화]['digit']

def total_by_key(key):
    total = 0
    for code in currencies:
        val = accounts[code][key]
        환산 = 환산금액(val, code, 합산기준통화)
        환산_floor = floor_to_digit(환산, main_digit)
        total += 환산_floor
    return total

total_balance = total_by_key('balance')
total_bonus = total_by_key('bonus')
total_credit = total_by_key('credit')
total_restricted = total_by_key('restricted')
net_asset = total_balance - total_bonus - total_credit - total_restricted

누적보너스 = st.session_state['누적보너스_USD']

st.write(f"**총자산 (Total balance):** {total_balance:.{main_digit}f} {합산기준통화}")
st.write(f"**토탈보너스 (Total Bonus):** {total_bonus:.{main_digit}f} {합산기준통화}")
st.write(f"**토탈크레딧 (Total Credit):** {total_credit:.{main_digit}f} {합산기준통화}")
st.write(f"**토탈출금제한 (Total Restricted):** {total_restricted:.{main_digit}f} {합산기준통화}")
st.write(f"**순수자본(잔고-보너스-크레딧-출금제한):** {net_asset:.{main_digit}f} {합산기준통화}")

st.write(f"**누적보너스 (USD 기준, 지급총액):** {누적보너스:.2f} USD")

st.info("""
- '토탈보너스'는 각 통화별 현재 보너스 금액을 합산환산한 값입니다.
- '누적보너스'는 입금시점부터 지급된 모든 보너스의 USD 합계(한도체크용)입니다.
- 환산 기준 통화(아래 첨자)를 바꿔서 각 금액을 원하는 통화로 확인할 수 있습니다.
- 출금 후 자기자본(USD 환산)이 10 미만이면 해당 통화 보너스는 전액 소멸됩니다.
""")
