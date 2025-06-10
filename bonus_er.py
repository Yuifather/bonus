import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_DOWN, getcontext

getcontext().prec = 28

# 기본 환율 테이블 (XXXUSD 페어만, bid/ask 구분)
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
all_currencies = list(default_digits.keys())

default_bonus_currency = 'JPY'
default_bonus_limit = Decimal('2000000')
default_first_bonus_currency = 'JPY'
default_first_bonus_limit = Decimal('50000')
default_bonus_ratio_first = 50
default_bonus_ratio_next = 20
default_bonus_wipe_currency = 'JPY'
default_bonus_wipe_amount = Decimal('1000')

def get_cross_rate(base, quote, direction, rates=None):
    if base == quote:
        return Decimal('1')
    if rates is None:
        rates = default_rates
    pair1 = base + 'USD'
    pair2 = quote + 'USD'
    if pair1 in rates and pair2 in rates:
        rate1 = Decimal(rates[pair1][direction])
        rate2 = Decimal(rates[pair2][direction])
        return rate1 / rate2
    pair1r = 'USD' + base
    pair2r = 'USD' + quote
    if pair1r in rates and pair2 in rates:
        rate1 = Decimal('1') / Decimal(rates[pair1r][direction])
        rate2 = Decimal(rates[pair2][direction])
        return rate1 / rate2
    if pair1 in rates and pair2r in rates:
        rate1 = Decimal(rates[pair1][direction])
        rate2 = Decimal('1') / Decimal(rates[pair2r][direction])
        return rate1 / rate2
    if pair1r in rates and pair2r in rates:
        rate1 = Decimal('1') / Decimal(rates[pair1r][direction])
        rate2 = Decimal('1') / Decimal(rates[pair2r][direction])
        return rate1 / rate2
    raise Exception(f'No cross rate for {base}/{quote}({direction})')

def floor_to_digit(val, digit):
    dval = Decimal(val)
    if digit > 0:
        quant = Decimal('1.' + '0'*digit)
    else:
        quant = Decimal('1')
    return dval.quantize(quant, rounding=ROUND_DOWN)

# 세션상태 초기화
if 'rates' not in st.session_state:
    st.session_state['rates'] = {k: {'bid': Decimal(str(v['bid'])), 'ask': Decimal(str(v['ask']))} for k, v in default_rates.items()}
if 'digits' not in st.session_state:
    st.session_state['digits'] = default_digits.copy()
if 'accounts' not in st.session_state:
    st.session_state.accounts = {c: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')} for c in all_currencies}
if 'bonus_limit' not in st.session_state:
    st.session_state['bonus_limit'] = {'currency': default_bonus_currency, 'limit': Decimal(default_bonus_limit)}
if 'first_bonus_limit' not in st.session_state:
    st.session_state['first_bonus_limit'] = {'currency': default_first_bonus_currency, 'limit': Decimal(default_first_bonus_limit)}
if 'bonus_ratio_first' not in st.session_state:
    st.session_state['bonus_ratio_first'] = default_bonus_ratio_first
if 'bonus_ratio_next' not in st.session_state:
    st.session_state['bonus_ratio_next'] = default_bonus_ratio_next
if '누적보너스' not in st.session_state:
    st.session_state['누적보너스'] = Decimal('0')
if 'bonus_wipe_policy' not in st.session_state:
    st.session_state['bonus_wipe_policy'] = {'currency': default_bonus_wipe_currency, 'amount': Decimal(default_bonus_wipe_amount)}
if 'setting_menu' not in st.session_state:
    st.session_state['setting_menu'] = None

rates = st.session_state['rates']
digits = st.session_state['digits']
accounts = st.session_state['accounts']

main_menu = st.sidebar.radio("메뉴", ["입금/출금", "설정"], key="main_menu")
setting_menu = st.session_state['setting_menu'] if main_menu == "설정" else None

if main_menu == "설정":
    st.sidebar.write("### 설정")
    if st.sidebar.button("환율 및 소수점 수정"):
        st.session_state['setting_menu'] = "환율 및 소수점 수정"
        setting_menu = "환율 및 소수점 수정"
    if st.sidebar.button("보너스 정책/비율 수정"):
        st.session_state['setting_menu'] = "보너스 정책/비율 수정"
        setting_menu = "보너스 정책/비율 수정"
    if st.sidebar.button("누적보너스 한도 설정"):
        st.session_state['setting_menu'] = "누적보너스 한도 설정"
        setting_menu = "누적보너스 한도 설정"
    if st.sidebar.button("보너스 소멸 정책 설정"):
        st.session_state['setting_menu'] = "보너스 소멸 정책 설정"
        setting_menu = "보너스 소멸 정책 설정"
    if st.sidebar.button("초기화"):
        st.session_state['setting_menu'] = "초기화"
        setting_menu = "초기화"
    if st.sidebar.button("뒤로가기"):
        st.session_state['setting_menu'] = None
        setting_menu = None

if main_menu == "입금/출금":
    st.sidebar.header("입금/출금")
    st.session_state['setting_menu'] = None
    action = st.sidebar.radio("동작", ["입금", "출금"], key="action")
    currency = st.sidebar.selectbox("통화", all_currencies, key="currency")
    digit = digits[currency]
    amount_input = st.sidebar.number_input("금액", min_value=0.0, step=0.01, format="%.8f", key="amount")
    amount = floor_to_digit(Decimal(str(amount_input)), digit)

    if st.sidebar.button("실행", key="run_action"):
        acc = accounts[currency]
        rate = rates[currency + 'USD']['bid']
        digit = digits[currency]

        bonus_limit_info = st.session_state['bonus_limit']
        first_bonus_limit_info = st.session_state['first_bonus_limit']
        ratio_first = Decimal(st.session_state['bonus_ratio_first'])
        ratio_next = Decimal(st.session_state['bonus_ratio_next'])
        bonus_limit_currency = bonus_limit_info['currency']
        bonus_limit_value = bonus_limit_info['limit']
        first_bonus_limit_currency = first_bonus_limit_info['currency']
        first_bonus_limit_value = first_bonus_limit_info['limit']

        누적보너스 = st.session_state['누적보너스']
        remain_bonus_limit = bonus_limit_value - 누적보너스

        # 1. 입금액을 한도통화로 환산
        amount_in_limit_cur = amount * get_cross_rate(currency, bonus_limit_currency, 'bid', rates)
        # 2. 한도통화 기준, 첫입금 보너스구간(한도금액/첫입금비율*100), 초과구간계산
        max_first_bonus = first_bonus_limit_value
        first_bonus_max_deposit = max_first_bonus * Decimal('100') / ratio_first
        deposit_in_limit_cur = amount_in_limit_cur

        # 3. 각 구간별 환산
        if deposit_in_limit_cur * ratio_first / Decimal('100') <= max_first_bonus:
            bonus1 = deposit_in_limit_cur * ratio_first / Decimal('100')
            bonus2 = Decimal('0')
        else:
            bonus1 = max_first_bonus
            remain = deposit_in_limit_cur - (max_first_bonus * Decimal('100') / ratio_first)
            bonus2 = remain * ratio_next / Decimal('100') if remain > 0 else Decimal('0')
        total_bonus_in_limit_cur = bonus1 + bonus2

        apply_bonus_in_limit_cur = min(total_bonus_in_limit_cur, remain_bonus_limit)
        apply_bonus = floor_to_digit(apply_bonus_in_limit_cur * get_cross_rate(bonus_limit_currency, currency, 'ask', rates), digit)

        acc['net_capital'] = floor_to_digit(acc['net_capital'] + amount, digit)

        if action == "입금":
            if apply_bonus > Decimal('0'):
                acc['bonus'] = floor_to_digit(acc['bonus'] + apply_bonus, digit)
                bonus_for_limit = floor_to_digit(apply_bonus * get_cross_rate(currency, bonus_limit_currency, 'bid', rates), digits[bonus_limit_currency])
                st.session_state['누적보너스'] += bonus_for_limit
                st.success(f"{currency} {float(amount):,.{digit}f} 입금 및 보너스 {float(apply_bonus):,.{digit}f} 지급 (누적: {float(st.session_state['누적보너스'])} {bonus_limit_currency})")
            else:
                st.success(f"{currency} {float(amount):,.{digit}f} 입금 (보너스 한도 도달로 보너스 지급 없음)")

        elif action == "출금":
            # 1. 모든 통화의 순수자본 합산(출금통화로 환산)
            total_net_in_currency = Decimal('0')
            for code in all_currencies:
                acc0 = accounts[code]
                net0 = floor_to_digit(acc0['net_capital'], digits[code])
                total_net_in_currency += net0 * get_cross_rate(code, currency, 'bid', rates)
            출금가능 = max(Decimal('0'), acc['net_capital'])
            출금액 = min(amount, 출금가능)
            출금액 = floor_to_digit(출금액, digit)
            if 출금액 <= Decimal('0'):
                st.error("출금 가능 순수자본이 부족합니다.")
            else:
                ratio = 출금액 / total_net_in_currency if total_net_in_currency > Decimal('0') else Decimal('1')
                for code in all_currencies:
                    acc0 = accounts[code]
                    digit0 = digits[code]
                    acc0['bonus'] = floor_to_digit(acc0['bonus'] * (Decimal('1') - ratio), digit0)
                acc['net_capital'] = floor_to_digit(acc['net_capital'] - 출금액, digit)
                # 소멸 정책
                wipe_policy = st.session_state['bonus_wipe_policy']
                wipe_currency = wipe_policy['currency']
                wipe_amount = wipe_policy['amount']
                total_net_for_wipe = Decimal('0')
                for code in all_currencies:
                    acc0 = accounts[code]
                    d0 = digits[code]
                    net0 = floor_to_digit(acc0['net_capital'], d0)
                    net_in_wipe = net0 * get_cross_rate(code, wipe_currency, 'bid', rates)
                    total_net_for_wipe += net_in_wipe
                if total_net_for_wipe < wipe_amount:
                    for code in all_currencies:
                        accounts[code]['bonus'] = Decimal('0')
                st.success(f"{currency} {float(출금액):,.{digit}f} 출금 완료 (보너스 {float(ratio * 100):.2f}% 차감)")

# -------------- 설정 메뉴 구현 (환율/비율/한도/소멸)
if main_menu == "설정" and setting_menu == "환율 및 소수점 수정":
    st.subheader("환율 및 소수점 수정")
    st.write("'적용' 클릭시 전체 초기화 됩니다.")
    new_rates = {}
    new_digits = {}
    for pair in rates.keys():
        col1, col2, col3 = st.columns([1,2,1])
        col1.write(pair)
        bid = col2.text_input("", value=str(rates[pair]['bid']), key=f"bid_set_{pair}")
        ask = col3.text_input("", value=str(rates[pair]['ask']), key=f"ask_set_{pair}")
        new_rates[pair] = {'bid': Decimal(bid), 'ask': Decimal(ask)}
    for code in all_currencies:
        digits_in = st.number_input(f"{code} 소수점", min_value=0, max_value=8, value=int(digits[code]), key=f"digit_set_{code}")
        new_digits[code] = digits_in
    if st.button("적용(전체초기화)", key="apply_rate_digit"):
        st.session_state['rates'] = new_rates
        st.session_state['digits'] = new_digits
        st.session_state.accounts = {c: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')} for c in all_currencies}
        st.session_state['누적보너스'] = Decimal('0')
        st.success("환율/소수점 변경 및 전체 초기화 완료!")

if main_menu == "설정" and setting_menu == "보너스 정책/비율 수정":
    st.subheader("보너스 정책/비율 수정")
    st.write("아래 설정을 변경 후 '적용'을 누르면 전체 초기화 됩니다.")
    col1, col2 = st.columns(2)
    first_bonus_limit_currency = col1.selectbox("최초입금 한도 통화", all_currencies, index=all_currencies.index(st.session_state['first_bonus_limit']['currency']), key="first_bonus_limit_currency")
    first_bonus_limit = col1.number_input(
        f"최초입금 보너스 최대({first_bonus_limit_currency})", min_value=0.0, value=float(st.session_state['first_bonus_limit']['limit']), step=1.0, key="first_bonus_limit_input"
    )
    bonus_ratio_first = col2.number_input("첫입금 보너스(%)", min_value=0, max_value=100, value=int(st.session_state['bonus_ratio_first']), step=1, key="bonus_ratio_first_set")
    col3, col4 = st.columns(2)
    bonus_ratio_next = col3.number_input("추가입금 보너스(%)", min_value=0, max_value=100, value=int(st.session_state['bonus_ratio_next']), step=1, key="bonus_ratio_next_set")
    if st.button("적용(전체초기화)", key="apply_bonus_ratio"):
        st.session_state['first_bonus_limit'] = {"limit": Decimal(str(first_bonus_limit)), "currency": first_bonus_limit_currency}
        st.session_state['bonus_ratio_first'] = int(bonus_ratio_first)
        st.session_state['bonus_ratio_next'] = int(bonus_ratio_next)
        st.session_state.accounts = {c: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')} for c in all_currencies}
        st.session_state['누적보너스'] = Decimal('0')
        st.success("보너스 정책/비율 변경 및 전체 초기화 완료!")

if main_menu == "설정" and setting_menu == "누적보너스 한도 설정":
    st.subheader("누적보너스 한도 설정")
    bonus_limit_currency = st.selectbox("누적보너스 한도 통화", all_currencies, index=all_currencies.index(st.session_state['bonus_limit']['currency']), key="bonus_limit_currency")
    bonus_limit_value = st.number_input(
        f"누적보너스 한도 ({bonus_limit_currency})", min_value=1.0, value=float(st.session_state['bonus_limit']['limit']), step=1.0, key="bonus_limit_value"
    )
    if st.button("적용(전체초기화)", key="apply_bonus_limit"):
        st.session_state['bonus_limit'] = {"limit": Decimal(str(bonus_limit_value)), "currency": bonus_limit_currency}
        st.session_state.accounts = {c: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')} for c in all_currencies}
        st.session_state['누적보너스'] = Decimal('0')
        st.success("누적보너스 한도 변경 및 전체 초기화 완료!")

if main_menu == "설정" and setting_menu == "보너스 소멸 정책 설정":
    st.subheader("보너스 소멸 정책 설정")
    wipe_policy = st.session_state['bonus_wipe_policy']
    wipe_currency = st.selectbox("소멸 기준 통화", all_currencies, index=all_currencies.index(wipe_policy['currency']), key="bonus_wipe_currency")
    wipe_amount = st.number_input(f"소멸 기준 금액 ({wipe_currency})", min_value=0.0, value=float(wipe_policy['amount']), step=1.0, key="bonus_wipe_amount")
    if st.button("적용(전체초기화)", key="apply_bonus_wipe"):
        st.session_state['bonus_wipe_policy'] = {'currency': wipe_currency, 'amount': Decimal(str(wipe_amount))}
        st.session_state.accounts = {c: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')} for c in all_currencies}
        st.session_state['누적보너스'] = Decimal('0')
        st.success("보너스 소멸 정책 변경 및 전체 초기화 완료!")

if main_menu == "설정" and setting_menu == "초기화":
    st.subheader("전체 초기화")
    if st.button("전체 계좌/보너스 리셋", key="full_reset"):
        st.session_state.accounts = {c: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')} for c in all_currencies}
        st.session_state['누적보너스'] = Decimal('0')
        st.success("모든 계좌 정보가 초기화 되었습니다.")

# ----------- 계좌 현황/통계
st.write("### 통화별 계좌 현황")
rows = []
for code in all_currencies:
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
st.markdown(
    "<small><b>※ balance=순수자본+bonus+credit+restricted</b></small>",
    unsafe_allow_html=True
)
st.write("---")
합산기준통화 = st.selectbox("합산(환산):", all_currencies, index=0)
main_digit = digits[합산기준통화]

def total_by_key(key):
    total = Decimal('0')
    for code in all_currencies:
        if key == 'balance':
            val = floor_to_digit(accounts[code]['net_capital'] + accounts[code]['bonus'] + accounts[code]['credit'] + accounts[code]['restricted'], digits[code])
        else:
            val = floor_to_digit(accounts[code][key], digits[code])
        환산 = val * get_cross_rate(code, 합산기준통화, 'bid', rates)
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
- 출금 시 보너스를 제외한 계좌 잔액 대비 출금 금액에 해당하는 비율만큼, 보너스 잔액도 비례하여 차감
- **출금 후 전체 순수자본({wipe_policy['currency']}) 환산 기준 {wipe_policy['amount']} 미만이면 모든 보너스가 전액 소멸됩니다.**
- 보너스 정책/비율 (최초입금 최대 {st.session_state['first_bonus_limit']['limit']} {st.session_state['first_bonus_limit']['currency']}, 첫입금 {st.session_state['bonus_ratio_first']}%, 추가입금 {st.session_state['bonus_ratio_next']}%)은 [설정 > 보너스 정책/비율 수정]에서 변경 가능합니다.
''')
