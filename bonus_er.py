import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_DOWN, getcontext

getcontext().prec = 28

default_rates = {
    'USDUSD': {'bid': '1', 'ask': '1'},
    'EURUSD': {'bid': '1.14', 'ask': '1.14'},
    'GBPUSD': {'bid': '1.25', 'ask': '1.25'},
    'JPYUSD': {'bid': '0.007', 'ask': '0.007'},
    'BTCUSD': {'bid': '105193.5', 'ask': '105193.5'},
    'ETHUSD': {'bid': '2629.69', 'ask': '2629.69'},
    'XRPUSD': {'bid': '2.21', 'ask': '2.21'},
    'USDTUSD': {'bid': '1', 'ask': '1'},
    'USDCUSD': {'bid': '1', 'ask': '1'},
}
default_digits = {
    'USD': 2, 'EUR': 2, 'GBP': 2, 'JPY': 0,
    'BTC': 8, 'ETH': 6, 'XRP': 4, 'USDT': 2, 'USDC': 2,
}
CURRENCY_LIST = ['USD', 'EUR', 'GBP', 'JPY', 'BTC', 'ETH', 'XRP', 'USDT', 'USDC']

default_bonus_currency = 'JPY'
default_bonus_limit = Decimal('2000000')
default_first_bonus_currency = 'JPY'
default_first_bonus_limit = Decimal('50000')
default_bonus_ratio_first = 50
default_bonus_ratio_next = 20
default_bonus_wipe_currency = 'JPY'
default_bonus_wipe_amount = Decimal('1000')

def floor_to_digit(val, digit):
    dval = Decimal(val)
    if digit > 0:
        quant = Decimal('1.' + '0'*digit)
    else:
        quant = Decimal('1')
    return dval.quantize(quant, rounding=ROUND_DOWN)

def get_cross_rate(base, quote, direction, rates):
    if base == quote:
        return Decimal('1')
    pair = base + quote
    rev_pair = quote + base
    if pair in rates:
        return Decimal(str(rates[pair][direction]))
    elif rev_pair in rates:
        return Decimal('1') / Decimal(str(rates[rev_pair][direction]))
    # USD 크로스
    if base != 'USD' and quote != 'USD':
        base_usd = get_cross_rate(base, 'USD', direction, rates)
        usd_quote = get_cross_rate('USD', quote, direction, rates)
        return base_usd * usd_quote
    raise Exception(f"No rate for {base}/{quote} ({direction})")

def 환산금액(val, from_code, to_code, rates):
    return val * get_cross_rate(from_code, to_code, 'bid', rates)

# 세션상태 초기화
if 'rates' not in st.session_state:
    st.session_state['rates'] = default_rates.copy()
if 'digits' not in st.session_state:
    st.session_state['digits'] = default_digits.copy()
if 'accounts' not in st.session_state:
    st.session_state['accounts'] = {
        code: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')}
        for code in CURRENCY_LIST
    }
if 'bonus_limit' not in st.session_state:
    st.session_state['bonus_limit'] = {
        'currency': default_bonus_currency,
        'limit': Decimal(default_bonus_limit)
    }
if 'first_bonus_limit' not in st.session_state:
    st.session_state['first_bonus_limit'] = {
        'currency': default_first_bonus_currency,
        'limit': Decimal(default_first_bonus_limit)
    }
if 'bonus_ratio_first' not in st.session_state:
    st.session_state['bonus_ratio_first'] = default_bonus_ratio_first
if 'bonus_ratio_next' not in st.session_state:
    st.session_state['bonus_ratio_next'] = default_bonus_ratio_next
if '누적보너스' not in st.session_state:
    st.session_state['누적보너스'] = Decimal('0')
if 'bonus_wipe_policy' not in st.session_state:
    st.session_state['bonus_wipe_policy'] = {
        'currency': default_bonus_wipe_currency,
        'amount': Decimal(default_bonus_wipe_amount)
    }
if 'setting_menu' not in st.session_state:
    st.session_state['setting_menu'] = None

rates = st.session_state['rates']
digits = st.session_state['digits']

# 메뉴
main_menu = st.sidebar.radio("메뉴", ["입금/출금", "설정"], key="main_menu")
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
    if st.sidebar.button("보너스 소멸 정책 설정", key="bonus_wipe_btn"):
        st.session_state['setting_menu'] = "보너스 소멸 정책 설정"
        setting_menu = "보너스 소멸 정책 설정"
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
    currency = st.sidebar.selectbox("통화", CURRENCY_LIST, key="currency")
    digit = digits[currency]
    amount_input = st.sidebar.number_input("금액", min_value=0.0, step=0.01, format="%.8f", key="amount")
    amount = floor_to_digit(Decimal(str(amount_input)), digit)

    if st.sidebar.button("실행", key="run_action"):
        acc = st.session_state['accounts'][currency]
        bonus_limit_info = st.session_state['bonus_limit']
        first_bonus_limit_info = st.session_state['first_bonus_limit']
        bonus_ratio_first = st.session_state['bonus_ratio_first']
        bonus_ratio_next = st.session_state['bonus_ratio_next']
        bonus_limit_currency = bonus_limit_info['currency']
        bonus_limit_value = Decimal(bonus_limit_info['limit'])
        first_bonus_limit_currency = first_bonus_limit_info['currency']
        first_bonus_limit_value = Decimal(first_bonus_limit_info['limit'])
        누적보너스 = st.session_state['누적보너스']
        remain_bonus_limit = bonus_limit_value - 누적보너스

        # 1. 첫입금 한도(입금통화 기준) 계산
        first_limit_in_deposit_currency = floor_to_digit(
            환산금액(first_bonus_limit_value, first_bonus_limit_currency, currency, rates), digit
        )

        bonus = Decimal('0')
        bonus_first = Decimal('0')
        bonus_next = Decimal('0')
        if amount <= Decimal('0'):
            st.error("입금액이 없습니다.")
        else:
            # 1. 첫입금 한도까지 1구간 비율
            first_part = min(amount, first_limit_in_deposit_currency)
            if first_part > 0:
                bonus_first = floor_to_digit(first_part * Decimal(bonus_ratio_first) / Decimal(100), digit)
            # 2. 한도 초과분은 2구간 비율
            second_part = max(amount - first_limit_in_deposit_currency, Decimal('0'))
            if second_part > 0:
                bonus_next = floor_to_digit(second_part * Decimal(bonus_ratio_next) / Decimal(100), digit)
            bonus = bonus_first + bonus_next

            # 누적보너스 한도 적용 (보너스 전체를 한도통화로 환산해서 체크)
            bonus_in_limit_currency = 환산금액(bonus, currency, bonus_limit_currency, rates)
            if remain_bonus_limit <= Decimal('0'):
                apply_bonus_in_limit_currency = Decimal('0')
            elif bonus_in_limit_currency > remain_bonus_limit:
                apply_bonus_in_limit_currency = remain_bonus_limit
            else:
                apply_bonus_in_limit_currency = bonus_in_limit_currency

            # 실제 지급할 보너스 (입금통화로 환산)
            apply_bonus = floor_to_digit(
                환산금액(apply_bonus_in_limit_currency, bonus_limit_currency, currency, rates),
                digit
            )

            acc['net_capital'] = floor_to_digit(acc['net_capital'] + amount, digit)
            if apply_bonus > Decimal('0'):
                acc['bonus'] = floor_to_digit(acc['bonus'] + apply_bonus, digit)
                # 지급된 보너스를 누적보너스(한도통화)로 누적
                bonus_for_limit = 환산금액(apply_bonus, currency, bonus_limit_currency, rates)
                bonus_for_limit = floor_to_digit(bonus_for_limit, digits[bonus_limit_currency])
                st.session_state['누적보너스'] += bonus_for_limit
                st.success(f"{currency} {float(amount):,.{digit}f} 입금 및 보너스 {float(apply_bonus):,.{digit}f} 지급 (누적: {float(st.session_state['누적보너스'])} {bonus_limit_currency})")
            else:
                st.success(f"{currency} {float(amount):,.{digit}f} 입금 (보너스 한도 도달로 보너스 지급 없음)")

# 계좌 현황 및 합산정보
accounts = st.session_state['accounts']
st.write("### 통화별 계좌 현황")
rows = []
for code in CURRENCY_LIST:
    data = accounts[code]
    d = digits[code]
    net_capital = floor_to_digit(data['net_capital'], d)
    bonus = floor_to_digit(data['bonus'], d)
    credit = floor_to_digit(data['credit'], d)
    restricted = floor_to_digit(data['restricted'], d)
    balance = floor_to_digit(net_capital + bonus + credit + restricted, d)
    rows.append({
        "통화": code,
        "balance": float(balance),
        "순수자본": float(net_capital),
        "bonus": float(bonus),
        "credit": float(credit),
        "restricted": float(restricted)
    })
st.dataframe(pd.DataFrame(rows).set_index("통화").style.format("{:.8f}"))
st.markdown("<small><b>※ balance=순수자본+bonus+credit+restricted</b></small>", unsafe_allow_html=True)
st.write("---")
합산기준통화 = st.selectbox("합산(환산):", CURRENCY_LIST, index=0)
main_digit = digits[합산기준통화]

def total_by_key(key):
    total = Decimal('0')
    for code in CURRENCY_LIST:
        if key == 'balance':
            val = floor_to_digit(accounts[code]['net_capital'] + accounts[code]['bonus'] + accounts[code]['credit'] + accounts[code]['restricted'], digits[code])
        else:
            val = floor_to_digit(accounts[code][key], digits[code])
        환산 = 환산금액(val, code, 합산기준통화, rates)
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
bonus_limit_value = bonus_limit_info['limit']
누적보너스 = st.session_state['누적보너스']
wipe_policy = st.session_state['bonus_wipe_policy']

st.write(f"**총자산 (Total balance):** {float(total_balance):,.{main_digit}f} {합산기준통화}  =  순수자본 + 보너스 + 크레딧 + 출금제한")
st.write(f"** - 순수자본:** {float(net_asset):,.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈보너스:** {float(total_bonus):,.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈크레딧:** {float(total_credit):,.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈출금제한:** {float(total_restricted):,.{main_digit}f} {합산기준통화}")

st.write(f"**누적보너스 ({bonus_limit_currency} 기준, 지급총액):** {float(누적보너스):,.{digits[bonus_limit_currency]}f} / {float(bonus_limit_value):,.{digits[bonus_limit_currency]}f} {bonus_limit_currency}")

st.info(f'''
- 신규 고객의 최초 입금에 한해, 입금 금액의 {st.session_state['bonus_ratio_first']}%를 보너스로 지급. 단, 최초 입금에 대한 보너스는 최대 {st.session_state['first_bonus_limit']['limit']} {st.session_state['first_bonus_limit']['currency']}를 한도로 함.
- 최초 입금 시 한도를 넘는 입금 차액 또는 추가 입금에 대해서는 입금 금액의 {st.session_state['bonus_ratio_next']}%를 보너스로 지급
- balance = 순수자본 + 보너스 + credit + restricted
- 총자산 = 순수자본 + 토탈보너스 + 토탈크레딧 + 토탈출금제한
- '토탈보너스'는 각 통화별 현재 보너스 금액을 합산환산한 값입니다.
- '누적보너스'는 입금시점부터 지급된 모든 보너스의 한도통화 합계(한도체크용)입니다.
- 누적보너스 한도는 [설정 > 누적보너스 한도 설정]에서 변경 가능합니다.
- 환산 통화를 바꿔서 각 금액을 원하는 통화로 확인할 수 있습니다.
''')
