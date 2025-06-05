import streamlit as st
import pandas as pd
import math

default_rates = {
    'USD': 1, 'EUR': 1.14, 'GBP': 1.25, 'JPY': 0.007,
    'BTC': 105193.5, 'ETH': 2629.69, 'XRP': 2.21, 'USDT': 1, 'USDC': 1,
}
default_digits = {
    'USD': 2, 'EUR': 2, 'GBP': 2, 'JPY': 0,
    'BTC': 8, 'ETH': 6, 'XRP': 4, 'USDT': 2, 'USDC': 2,
}
default_bonus_ratio_first = 50
default_bonus_ratio_next = 20
default_bonus_limit_usd = 20000

def floor_to_digit(val, digit):
    p = 10 ** digit
    return math.floor(val * p) / p

def 환산금액(val, from_code, to_code, currencies):
    usd_val = val * currencies[from_code]['rate']
    return usd_val / currencies[to_code]['rate']

# 세션상태 초기화
if 'currencies' not in st.session_state:
    st.session_state['currencies'] = {
        code: {'rate': float(default_rates[code]), 'digit': int(default_digits[code])}
        for code in default_rates
    }
if 'accounts' not in st.session_state:
    st.session_state.accounts = {
        code: {'balance': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
        for code in default_rates
    }
if '누적보너스_USD' not in st.session_state:
    st.session_state['누적보너스_USD'] = 0
if 'bonus_ratio_first' not in st.session_state:
    st.session_state['bonus_ratio_first'] = default_bonus_ratio_first
if 'bonus_ratio_next' not in st.session_state:
    st.session_state['bonus_ratio_next'] = default_bonus_ratio_next
if 'bonus_limit_usd' not in st.session_state:
    st.session_state['bonus_limit_usd'] = default_bonus_limit_usd
if 'setting_menu' not in st.session_state:
    st.session_state['setting_menu'] = None

currencies = st.session_state['currencies']

# 메뉴
main_menu = st.sidebar.radio(
    "메뉴",
    ["입금/출금", "설정"],
    key="main_menu"
)
setting_menu = st.session_state['setting_menu'] if main_menu == "설정" else None

if main_menu == "설정":
    st.sidebar.write("### 설정")
    if st.sidebar.button("환율 및 소수점 수정", key="rate_digit_btn"):
        st.session_state['setting_menu'] = "환율 및 소수점 수정"
        setting_menu = "환율 및 소수점 수정"
    if st.sidebar.button("보너스 비율 수정", key="bonus_ratio_btn"):
        st.session_state['setting_menu'] = "보너스 비율 수정"
        setting_menu = "보너스 비율 수정"
    if st.sidebar.button("누적보너스 한도 설정", key="limit_btn"):
        st.session_state['setting_menu'] = "누적보너스 한도 설정"
        setting_menu = "누적보너스 한도 설정"
    if st.sidebar.button("초기화", key="reset_btn"):
        st.session_state['setting_menu'] = "초기화"
        setting_menu = "초기화"
    if st.sidebar.button("뒤로가기", key="back_btn"):
        st.session_state['setting_menu'] = None
        setting_menu = None

# 입금/출금
if main_menu == "입금/출금":
    st.sidebar.header("입금/출금")
    st.session_state['setting_menu'] = None
    action = st.sidebar.radio("동작", ["입금", "출금"], key="action")
    currency = st.sidebar.selectbox("통화", list(currencies.keys()), key="currency")
    digit = currencies[currency]['digit']
    amount_input = st.sidebar.number_input("금액", min_value=0.0, step=0.01, format="%.8f", key="amount")
    amount = floor_to_digit(amount_input, digit)

    if st.sidebar.button("실행", key="run_action"):
        acc = st.session_state.accounts[currency]
        rate = currencies[currency]['rate']
        digit = currencies[currency]['digit']
        누적보너스 = st.session_state['누적보너스_USD']
        bonus_ratio_first = st.session_state['bonus_ratio_first']
        bonus_ratio_next = st.session_state['bonus_ratio_next']
        bonus_limit_usd = st.session_state['bonus_limit_usd']

        if action == "입금":
            amount = floor_to_digit(amount, digit)
            if 누적보너스 == 0:
                fifty = min(amount, 500 / rate) * (bonus_ratio_first / 100)
                excess = max(0, amount - 500 / rate) * (bonus_ratio_next / 100)
                raw_bonus = fifty + excess
            else:
                raw_bonus = amount * (bonus_ratio_next / 100)
            raw_bonus_usd = raw_bonus * rate
            remain_bonus_usd = max(0, bonus_limit_usd - 누적보너스)
            apply_bonus_usd = min(raw_bonus_usd, remain_bonus_usd)
            apply_bonus = floor_to_digit(apply_bonus_usd / rate, digit)
            
            # balance = 기존 balance + 입금액 + 지급된 보너스
            acc['balance'] = floor_to_digit(acc['balance'] + amount + apply_bonus, digit)
            if apply_bonus > 0:
                acc['bonus'] = floor_to_digit(acc['bonus'] + apply_bonus, digit)
                st.session_state['누적보너스_USD'] = floor_to_digit(
                    st.session_state['누적보너스_USD'] + apply_bonus * rate, 2
                )
                st.success(f"{currency} {amount} 입금 및 보너스 {apply_bonus} 지급")
            else:
                st.success(f"{currency} {amount} 입금 (보너스 한도 도달로 보너스 지급 없음)")

        elif action == "출금":
            # 출금가능: 해당 통화 순수자본 한도 내
            net_capital = floor_to_digit(acc['balance'] - acc['bonus'] - acc['credit'] - acc['restricted'], digit)
            출금가능 = max(0, net_capital)
            출금액 = min(amount, 출금가능)
            출금액 = floor_to_digit(출금액, digit)
            if 출금액 <= 0:
                st.error("출금 가능 순수자본이 부족합니다.")
            elif acc['balance'] < 출금액:
                st.error("잔액 부족!")
            else:
                # 출금 비율 = 출금액 / 순수자본
                ratio = 출금액 / net_capital if net_capital > 0 else 1

                # 해당 통화에 대해서만 보너스 비례 차감
                acc['bonus'] = floor_to_digit(acc['bonus'] * (1 - ratio), digit)

                # 순수자본에서 출금액 차감 → balance에서 출금액 차감
                acc['balance'] = floor_to_digit(acc['balance'] - 출금액, digit)

                # 출금 후 전체 순수자본(USD) < 10 이면 모든 보너스 소멸
                total_net_after = 0
                for code in currencies:
                    acc0 = st.session_state.accounts[code]
                    d0 = currencies[code]['digit']
                    net0 = floor_to_digit(acc0['balance'] - acc0['bonus'] - acc0['credit'] - acc0['restricted'], d0)
                    total_net_after += net0 * currencies[code]['rate']
                if total_net_after < 10:
                    for code in currencies:
                        st.session_state.accounts[code]['bonus'] = 0

                st.success(f"{currency} {출금액} 출금 완료 (보너스 {ratio:.2%} 차감)")

# 설정 > 환율 및 소수점 수정
if main_menu == "설정" and setting_menu == "환율 및 소수점 수정":
    st.subheader("환율 및 소수점 수정")
    st.write("'적용' 클릭시 전체 초기화 됩니다.")
    new_rates = {}
    new_digits = {}
    cols = st.columns([1,2,1])
    cols[0].write("**통화**")
    cols[1].write("**환율**")
    cols[2].write("**소수점**")
    for code in currencies.keys():
        col1, col2, col3 = st.columns([1,2,1])
        col1.write(code)
        rate = col2.number_input(
            "", min_value=0.000001, step=0.000001, value=float(currencies[code]['rate']), key=f"rate_set_{code}", format="%.6f"
        )
        digit = col3.number_input(
            "", min_value=0, max_value=8, step=1, value=int(currencies[code]['digit']), key=f"digit_set_{code}"
        )
        new_rates[code] = float(rate)
        new_digits[code] = int(digit)
    if st.button("적용(전체초기화)", key="apply_rate_digit"):
        st.session_state['currencies'] = {
            code: {'rate': new_rates[code], 'digit': new_digits[code]} for code in currencies
        }
        st.session_state.accounts = {
            code: {'balance': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
            for code in currencies
        }
        st.session_state['누적보너스_USD'] = 0
        st.success("환율/소수점 변경 및 전체 초기화 완료!")

# 설정 > 보너스 비율 수정
if main_menu == "설정" and setting_menu == "보너스 비율 수정":
    st.subheader("보너스 비율 수정")
    st.write("아래 비율을 변경 후 '적용'을 누르면 전체 초기화 됩니다.")
    col1, col2 = st.columns(2)
    bonus_ratio_first = col1.number_input("첫입금 보너스(%)", min_value=0, max_value=100, value=int(st.session_state['bonus_ratio_first']), step=1, key="bonus_ratio_first_set")
    bonus_ratio_next = col2.number_input("추가입금 보너스(%)", min_value=0, max_value=100, value=int(st.session_state['bonus_ratio_next']), step=1, key="bonus_ratio_next_set")
    if st.button("적용(전체초기화)", key="apply_bonus_ratio"):
        st.session_state['bonus_ratio_first'] = int(bonus_ratio_first)
        st.session_state['bonus_ratio_next'] = int(bonus_ratio_next)
        st.session_state.accounts = {
            code: {'balance': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
            for code in currencies
        }
        st.session_state['누적보너스_USD'] = 0
        st.success("보너스 비율 변경 및 전체 초기화 완료!")

# 설정 > 누적보너스 한도 설정
if main_menu == "설정" and setting_menu == "누적보너스 한도 설정":
    st.subheader("누적보너스 한도 설정")
    new_limit = st.number_input("누적보너스 한도(USD)", min_value=1, value=int(st.session_state['bonus_limit_usd']), step=1000)
    if st.button("적용(전체초기화)", key="apply_bonus_limit"):
        st.session_state['bonus_limit_usd'] = int(new_limit)
        st.session_state.accounts = {
            code: {'balance': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
            for code in currencies
        }
        st.session_state['누적보너스_USD'] = 0
        st.success("누적보너스 한도 변경 및 전체 초기화 완료!")

# 설정 > 초기화
if main_menu == "설정" and setting_menu == "초기화":
    st.subheader("전체 초기화")
    if st.button("전체 계좌/보너스 리셋", key="full_reset"):
        st.session_state.accounts = {
            code: {'balance': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
            for code in currencies
        }
        st.session_state['누적보너스_USD'] = 0
        st.success("모든 계좌 정보가 초기화 되었습니다.")

if main_menu == "설정" and setting_menu == "뒤로가기":
    st.session_state['setting_menu'] = None
    st.sidebar.info("좌측 메뉴에서 '입금/출금'을 다시 선택하세요.")

# 메인화면: 통화별 현황+합산정보
accounts = st.session_state.accounts
df = pd.DataFrame(accounts).T
st.write("### 통화별 계좌 현황")

rows = []
for code in currencies.keys():
    data = accounts[code]
    d = currencies[code]['digit']
    balance = floor_to_digit(data['balance'], d)
    bonus = floor_to_digit(data['bonus'], d)
    credit = floor_to_digit(data['credit'], d)
    restricted = floor_to_digit(data['restricted'], d)
    net = floor_to_digit(balance - bonus - credit - restricted, d)
    rows.append({
        "통화": code,
        "balance": balance,
        "순수자본": net,
        "bonus": bonus,
        "credit": credit,
        "restricted": restricted
    })
st.dataframe(pd.DataFrame(rows).set_index("통화").style.format("{:.8f}"))

st.markdown(
    "<small><b>※ balance=순수자본+bonus+credit+restricted</b></small>",
    unsafe_allow_html=True
)

st.write("---")
합산기준통화 = st.selectbox("합산(환산):", list(currencies.keys()), index=0)
main_digit = currencies[합산기준통화]['digit']

def total_by_key(key):
    total = 0
    for code in currencies:
        val = floor_to_digit(accounts[code][key], currencies[code]['digit'])
        환산 = 환산금액(val, code, 합산기준통화, currencies)
        환산_floor = floor_to_digit(환산, main_digit)
        total += 환산_floor
    return total

total_balance = total_by_key('balance')
total_bonus = total_by_key('bonus')
total_credit = total_by_key('credit')
total_restricted = total_by_key('restricted')
net_asset = total_balance - total_bonus - total_credit - total_restricted

누적보너스 = st.session_state['누적보너스_USD']
bonus_limit_usd = st.session_state['bonus_limit_usd']

st.write(f"**총자산 (Total balance):** {total_balance:.{main_digit}f} {합산기준통화}  =  순수자본 + 보너스 + 크레딧 + 출금제한")
st.write(f"** - 순수자본:** {net_asset:.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈보너스:** {total_bonus:.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈크레딧:** {total_credit:.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈출금제한:** {total_restricted:.{main_digit}f} {합산기준통화}")

st.write(f"**누적보너스 (USD 기준, 지급총액):** {누적보너스:.2f} / {bonus_limit_usd} USD")

st.info(f"""
- 모든 금액(잔고, 보너스, 출금, 합산 등)은 해당 통화 digit(소수점 자리) 기준으로 rounddown(floor) 처리됩니다.
- 'balance = 순수자본 + 보너스 + credit + restricted'은 모든 통화에서 반드시 성립합니다.
- 총자산 = 순수자본 + 토탈보너스 + 토탈크레딧 + 토탈출금제한 입니다.
- '토탈보너스'는 각 통화별 현재 보너스 금액을 합산환산한 값입니다.
- '누적보너스'는 입금시점부터 지급된 모든 보너스의 USD 합계(한도체크용)입니다.
- 누적보너스 한도는 [설정 > 누적보너스 한도 설정]에서 변경 가능합니다.
- 환산 통화를 바꿔서 각 금액을 원하는 통화로 확인할 수 있습니다.
- 출금 후 전체 순수자본(USD 환산)이 10 미만이면 모든 보너스가 전액 소멸됩니다.
- **보너스 비율** (첫입금 {st.session_state['bonus_ratio_first']}%, 추가입금 {st.session_state['bonus_ratio_next']}%)은 [설정 > 보너스 비율 수정]에서 변경 가능합니다.
""")
