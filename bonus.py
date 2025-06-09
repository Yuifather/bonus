import streamlit as st
import pandas as pd
import math

# 초기값 세팅
default_rates = {
    'USD': 1, 'EUR': 1.14, 'GBP': 1.25, 'JPY': 0.007,
    'BTC': 105193.5, 'ETH': 2629.69, 'XRP': 2.21, 'USDT': 1, 'USDC': 1,
}
default_digits = {
    'USD': 2, 'EUR': 2, 'GBP': 2, 'JPY': 0,
    'BTC': 8, 'ETH': 6, 'XRP': 4, 'USDT': 2, 'USDC': 2,
}

default_bonus_currency = 'USD'
default_bonus_limit = 20000
default_first_bonus_currency = 'USD'
default_first_bonus_limit = 500
default_bonus_ratio_first = 50
default_bonus_ratio_next = 20

# 공통 함수
def floor_to_digit(val, digit):
    p = 10 ** digit
    return math.floor(val * p) / p

def 환산금액(val, from_code, to_code, currencies):
    usd_val = val * currencies[from_code]['rate']
    return usd_val / currencies[to_code]['rate']

def round_amount(val, digit):
    return round(val + 1e-8, digit)

def round_usd(val):
    return round(val + 1e-8, 2)

# 세션상태 초기화
if 'currencies' not in st.session_state:
    st.session_state['currencies'] = {
        code: {'rate': float(default_rates[code]), 'digit': int(default_digits[code])}
        for code in default_rates
    }
if 'accounts' not in st.session_state:
    st.session_state.accounts = {
        code: {'net_capital': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
        for code in default_rates
    }
if 'bonus_limit' not in st.session_state:
    st.session_state['bonus_limit'] = {
        'currency': default_bonus_currency,
        'limit': float(default_bonus_limit)
    }
if 'first_bonus_limit' not in st.session_state:
    st.session_state['first_bonus_limit'] = {
        'currency': default_first_bonus_currency,
        'limit': float(default_first_bonus_limit)
    }
if 'bonus_ratio_first' not in st.session_state:
    st.session_state['bonus_ratio_first'] = default_bonus_ratio_first
if 'bonus_ratio_next' not in st.session_state:
    st.session_state['bonus_ratio_next'] = default_bonus_ratio_next
if '누적보너스' not in st.session_state:
    st.session_state['누적보너스'] = {code: 0.0 for code in default_rates}
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
    if st.sidebar.button("보너스 정책/비율 수정", key="bonus_ratio_btn"):
        st.session_state['setting_menu'] = "보너스 정책/비율 수정"
        setting_menu = "보너스 정책/비율 수정"
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

        bonus_limit_info = st.session_state['bonus_limit']
        first_bonus_limit_info = st.session_state['first_bonus_limit']
        bonus_ratio_first = st.session_state['bonus_ratio_first']
        bonus_ratio_next = st.session_state['bonus_ratio_next']

        # 각 한도통화 기준
        bonus_limit_currency = bonus_limit_info['currency']
        bonus_limit_value = float(bonus_limit_info['limit'])
        first_bonus_limit_currency = first_bonus_limit_info['currency']
        first_bonus_limit_value = float(first_bonus_limit_info['limit'])

        누적보너스 = st.session_state['누적보너스'][bonus_limit_currency]
        remain_bonus_limit = round_amount(bonus_limit_value - 누적보너스, currencies[bonus_limit_currency]['digit'])

        # 입금통화 기준으로 환산
        first_limit = first_bonus_limit_value * currencies[currency]['rate'] / currencies[first_bonus_limit_currency]['rate']
        bonus_limit_local = bonus_limit_value * currencies[currency]['rate'] / currencies[bonus_limit_currency]['rate']

        if action == "입금":
            amount = floor_to_digit(amount, digit)

            if 누적보너스 == 0:
                # 첫 입금
                fifty_amt = min(amount, first_limit)
                excess_amt = max(0, amount - first_limit)
                raw_bonus = fifty_amt * (bonus_ratio_first / 100) + excess_amt * (bonus_ratio_next / 100)
            else:
                raw_bonus = amount * (bonus_ratio_next / 100)

            # 한도통화로 환산
            raw_bonus_in_limit_currency = raw_bonus * currencies[bonus_limit_currency]['rate'] / currencies[currency]['rate']

            if remain_bonus_limit <= 0:
                apply_bonus_in_limit_currency = 0
            elif raw_bonus_in_limit_currency > remain_bonus_limit:
                apply_bonus_in_limit_currency = remain_bonus_limit
            else:
                apply_bonus_in_limit_currency = raw_bonus_in_limit_currency

            # 입금통화로 환산 및 소수점 처리
            apply_bonus = floor_to_digit(apply_bonus_in_limit_currency * currencies[currency]['rate'] / currencies[bonus_limit_currency]['rate'], digit)

            acc['net_capital'] = floor_to_digit(acc['net_capital'] + amount, digit)

            if apply_bonus > 0:
                acc['bonus'] = floor_to_digit(acc['bonus'] + apply_bonus, digit)
                # 한도통화 기준 누적보너스 갱신
                st.session_state['누적보너스'][bonus_limit_currency] += floor_to_digit(apply_bonus * currencies[bonus_limit_currency]['rate'] / currencies[currency]['rate'], currencies[bonus_limit_currency]['digit'])
                st.success(f"{currency} {amount} 입금 및 보너스 {apply_bonus} 지급")
            else:
                st.success(f"{currency} {amount} 입금 (보너스 한도 도달로 보너스 지급 없음)")

        elif action == "출금":
            total_net_in_currency = 0
            for code in currencies:
                acc0 = st.session_state.accounts[code]
                net0 = floor_to_digit(acc0['net_capital'], currencies[code]['digit'])
                total_net_in_currency += net0 * currencies[code]['rate'] / currencies[currency]['rate']
            출금가능 = max(0, acc['net_capital'])
            출금액 = min(amount, 출금가능)
            출금액 = floor_to_digit(출금액, digit)
            출금액_in_currency = 출금액
            if 출금액 <= 0:
                st.error("출금 가능 순수자본이 부족합니다.")
            else:
                ratio = 출금액_in_currency / total_net_in_currency if total_net_in_currency > 0 else 1
                for code in currencies:
                    acc0 = st.session_state.accounts[code]
                    digit0 = currencies[code]['digit']
                    acc0['bonus'] = floor_to_digit(acc0['bonus'] * (1 - ratio), digit0)
                acc['net_capital'] = floor_to_digit(acc['net_capital'] - 출금액, digit)
                total_net_after = 0
                for code in currencies:
                    acc0 = st.session_state.accounts[code]
                    d0 = currencies[code]['digit']
                    net0 = floor_to_digit(acc0['net_capital'], d0)
                    total_net_after += net0 * currencies[code]['rate']
                if total_net_after < 10:
                    for code in currencies:
                        st.session_state.accounts[code]['bonus'] = 0
                st.success(f"{currency} {출금액} 출금 완료 (보너스 {ratio:.2%} 차감)")

# 환율 및 소수점 수정
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
            code: {'net_capital': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
            for code in currencies
        }
        st.session_state['누적보너스'] = {code: 0.0 for code in currencies}
        st.success("환율/소수점 변경 및 전체 초기화 완료!")

# 보너스 정책/비율 수정
if main_menu == "설정" and setting_menu == "보너스 정책/비율 수정":
    st.subheader("보너스 정책/비율 수정")
    st.write("아래 설정을 변경 후 '적용'을 누르면 전체 초기화 됩니다.")
    col1, col2 = st.columns(2)
    first_bonus_limit_currency = col1.selectbox("최초입금 한도 통화", list(currencies.keys()), index=list(currencies.keys()).index(st.session_state['first_bonus_limit']['currency']), key="first_bonus_limit_currency")
    first_bonus_limit = col1.number_input(
        f"최초입금 보너스 최대({first_bonus_limit_currency})", min_value=0.0, value=float(st.session_state['first_bonus_limit']['limit']), step=1.0, key="first_bonus_limit_input"
    )
    bonus_ratio_first = col2.number_input("첫입금 보너스(%)", min_value=0, max_value=100, value=int(st.session_state['bonus_ratio_first']), step=1, key="bonus_ratio_first_set")
    col3, col4 = st.columns(2)
    bonus_ratio_next = col3.number_input("추가입금 보너스(%)", min_value=0, max_value=100, value=int(st.session_state['bonus_ratio_next']), step=1, key="bonus_ratio_next_set")
    if st.button("적용(전체초기화)", key="apply_bonus_ratio"):
        st.session_state['first_bonus_limit'] = {"limit": first_bonus_limit, "currency": first_bonus_limit_currency}
        st.session_state['bonus_ratio_first'] = int(bonus_ratio_first)
        st.session_state['bonus_ratio_next'] = int(bonus_ratio_next)
        st.session_state.accounts = {
            code: {'net_capital': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
            for code in currencies
        }
        st.session_state['누적보너스'] = {code: 0.0 for code in currencies}
        st.success("보너스 정책/비율 변경 및 전체 초기화 완료!")

# 누적보너스 한도 설정
if main_menu == "설정" and setting_menu == "누적보너스 한도 설정":
    st.subheader("누적보너스 한도 설정")
    bonus_limit_currency = st.selectbox("누적보너스 한도 통화", list(currencies.keys()), index=list(currencies.keys()).index(st.session_state['bonus_limit']['currency']), key="bonus_limit_currency")
    bonus_limit_value = st.number_input(
        f"누적보너스 한도 ({bonus_limit_currency})", min_value=1.0, value=float(st.session_state['bonus_limit']['limit']), step=1.0, key="bonus_limit_value"
    )
    if st.button("적용(전체초기화)", key="apply_bonus_limit"):
        st.session_state['bonus_limit'] = {"limit": bonus_limit_value, "currency": bonus_limit_currency}
        st.session_state.accounts = {
            code: {'net_capital': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
            for code in currencies
        }
        st.session_state['누적보너스'] = {code: 0.0 for code in currencies}
        st.success("누적보너스 한도 변경 및 전체 초기화 완료!")

# 초기화
if main_menu == "설정" and setting_menu == "초기화":
    st.subheader("전체 초기화")
    if st.button("전체 계좌/보너스 리셋", key="full_reset"):
        st.session_state.accounts = {
            code: {'net_capital': 0, 'bonus': 0, 'credit': 0, 'restricted': 0}
            for code in currencies
        }
        st.session_state['누적보너스'] = {code: 0.0 for code in currencies}
        st.success("모든 계좌 정보가 초기화 되었습니다.")

if main_menu == "설정" and setting_menu == "뒤로가기":
    st.session_state['setting_menu'] = None
    st.sidebar.info("좌측 메뉴에서 '입금/출금'을 다시 선택하세요.")

# 계좌 현황 및 합산정보
accounts = st.session_state.accounts
df = pd.DataFrame(accounts).T
st.write("### 통화별 계좌 현황")
rows = []
for code in currencies.keys():
    data = accounts[code]
    d = currencies[code]['digit']
    net_capital = floor_to_digit(data['net_capital'], d)
    bonus = floor_to_digit(data['bonus'], d)
    credit = floor_to_digit(data['credit'], d)
    restricted = floor_to_digit(data['restricted'], d)
    balance = floor_to_digit(net_capital + bonus + credit + restricted, d)
    rows.append({
        "통화": code,
        "balance": balance,
        "순수자본": net_capital,
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
        if key == 'balance':
            val = floor_to_digit(accounts[code]['net_capital'] + accounts[code]['bonus'] + accounts[code]['credit'] + accounts[code]['restricted'], currencies[code]['digit'])
        else:
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

bonus_limit_info = st.session_state['bonus_limit']
first_bonus_limit_info = st.session_state['first_bonus_limit']
bonus_limit_currency = bonus_limit_info['currency']
bonus_limit_value = float(bonus_limit_info['limit'])
누적보너스 = st.session_state['누적보너스'][bonus_limit_currency]

st.write(f"**총자산 (Total balance):** {total_balance:.{main_digit}f} {합산기준통화}  =  순수자본 + 보너스 + 크레딧 + 출금제한")
st.write(f"** - 순수자본:** {net_asset:.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈보너스:** {total_bonus:.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈크레딧:** {total_credit:.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈출금제한:** {total_restricted:.{main_digit}f} {합산기준통화}")

st.write(f"**누적보너스 ({bonus_limit_currency} 기준, 지급총액):** {누적보너스:.{currencies[bonus_limit_currency]['digit']}f} / {bonus_limit_value} {bonus_limit_currency}")

st.info(f"""
- 신규 고객의 최초 입금에 한해, 입금 금액의 {st.session_state['bonus_ratio_first']}%를 보너스로 지급. 단, 최초 입금에 대한 보너스는 최대 {st.session_state['first_bonus_limit']['limit']} {st.session_state['first_bonus_limit']['currency']}를 한도로 함.
- 최초 입금 시 한도를 넘는 입금 차액 또는 추가 입금에 대해서는 입금 금액의 {st.session_state['bonus_ratio_next']}%를 보너스로 지급
- balance = 순수자본 + 보너스 + credit + restricted
- 총자산 = 순수자본 + 토탈보너스 + 토탈크레딧 + 토탈출금제한
- '토탈보너스'는 각 통화별 현재 보너스 금액을 합산환산한 값입니다.
- '누적보너스'는 입금시점부터 지급된 모든 보너스의 한도통화 합계(한도체크용)입니다.
- 누적보너스 한도는 [설정 > 누적보너스 한도 설정]에서 변경 가능합니다.
- 환산 통화를 바꿔서 각 금액을 원하는 통화로 확인할 수 있습니다.
- 출금 시 보너스를 제외한 계좌 잔액 대비 출금 금액에 해당하는 비율만큼, 보너스 잔액도 비례하여 차감
- 출금 후 전체 순수자본(USD 환산)이 10 미만이면 모든 보너스가 전액 소멸됩니다.
- 보너스 정책/비율 (최초입금 최대 {st.session_state['first_bonus_limit']['limit']} {st.session_state['first_bonus_limit']['currency']}, 첫입금 {st.session_state['bonus_ratio_first']}%, 추가입금 {st.session_state['bonus_ratio_next']}%)은 [설정 > 보너스 정책/비율 수정]에서 변경 가능합니다.
""")
