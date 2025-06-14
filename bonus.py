import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_DOWN, getcontext

getcontext().prec = 28

# 환율 및 소수점, 통화 리스트 기본값
default_rates = {
    'USDUSD': {'bid': '1.0', 'ask': '1.0'},
    'EURUSD': {'bid': '1.14', 'ask': '1.14'},
    'GBPUSD': {'bid': '1.25', 'ask': '1.25'},
    'JPYUSD': {'bid': '0.007', 'ask': '0.007'},
    'BTCUSD': {'bid': '105193.5', 'ask': '105193.5'},
    'ETHUSD': {'bid': '2629.69', 'ask': '2629.69'},
    'XRPUSD': {'bid': '2.21', 'ask': '2.21'},
    'USDTUSD': {'bid': '1.0', 'ask': '1.0'},
    'USDCUSD': {'bid': '1.0', 'ask': '1.0'},
}
default_digits = {
    'USD': 2, 'EUR': 2, 'GBP': 2, 'JPY': 0,
    'BTC': 8, 'ETH': 6, 'XRP': 4, 'USDT': 2, 'USDC': 2,
}
currency_list = ['USD', 'EUR', 'GBP', 'JPY', 'BTC', 'ETH', 'XRP', 'USDT', 'USDC']

# 보너스 정책 기본값
default_bonus_limit_currency = 'JPY'      # 누적보너스 한도 통화
default_bonus_limit = Decimal('2000000')  # 누적보너스 한도(누적한도통화 기준)
default_first_bonus_currency = 'JPY'      # 최초입금 한도통화
default_first_bonus_limit = Decimal('50000') # 최초입금 보너스 한도(최초입금한도통화 기준)
default_bonus_ratio_first = 50            # 최초입금 보너스율(%)
default_bonus_ratio_next = 20             # 추가입금 보너스율(%)
default_bonus_wipe_currency = 'JPY'       # 소멸 기준 통화
default_bonus_wipe_amount = Decimal('1000')# 소멸 기준 금액(소멸통화 기준)

# 세션 상태 및 초기화
if 'rates' not in st.session_state:
    st.session_state['rates'] = {
        k: {'bid': Decimal(str(v['bid'])), 'ask': Decimal(str(v['ask']))} for k, v in default_rates.items()
    }
if 'currencies' not in st.session_state:
    st.session_state['currencies'] = {
        code: {'digit': int(default_digits[code])} for code in currency_list
    }
if 'accounts' not in st.session_state:
    st.session_state['accounts'] = {
        code: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')}
        for code in currency_list
    }
if 'first_bonus_limit' not in st.session_state:
    st.session_state['first_bonus_limit'] = {
        'currency': default_first_bonus_currency,
        'limit': Decimal(default_first_bonus_limit)
    }
if 'bonus_limit' not in st.session_state:
    st.session_state['bonus_limit'] = {
        'currency': default_bonus_limit_currency,
        'limit': Decimal(default_bonus_limit)
    }
if 'bonus_ratio_first' not in st.session_state:
    st.session_state['bonus_ratio_first'] = default_bonus_ratio_first
if 'bonus_ratio_next' not in st.session_state:
    st.session_state['bonus_ratio_next'] = default_bonus_ratio_next
if 'sum_bonus' not in st.session_state:
    st.session_state['sum_bonus'] = Decimal('0')  # 누적보너스(누적보너스한도통화 기준)
if 'sum_deposit' not in st.session_state:
    st.session_state['sum_deposit'] = {c: Decimal('0') for c in currency_list}  # 입금통화별 누적입금
if 'bonus_wipe_policy' not in st.session_state:
    st.session_state['bonus_wipe_policy'] = {
        'currency': default_bonus_wipe_currency,
        'amount': Decimal(default_bonus_wipe_amount)
    }
if 'setting_menu' not in st.session_state:
    st.session_state['setting_menu'] = None

rates = st.session_state['rates']
currencies = st.session_state['currencies']
accounts = st.session_state['accounts']

# 환율계산
def get_cross_rate(base, quote, direction, rates):
    if base == quote:
        return Decimal('1')
    pair = base + quote
    inv_pair = quote + base
    if pair in rates:
        return Decimal(str(rates[pair][direction]))
    elif inv_pair in rates:
        return Decimal('1') / Decimal(str(rates[inv_pair][direction]))
    else:
        # USD 통한 크로스환율
        if base != 'USD' and quote != 'USD':
            return (get_cross_rate(base, 'USD', direction, rates) /
                    get_cross_rate(quote, 'USD', direction, rates))
        raise ValueError(f"No cross rate for {base}/{quote}")
#소수점 처리
def floor_to_digit(val, digit):
    dval = Decimal(val)
    if digit > 0:
        quant = Decimal('1.' + '0'*digit)
    else:
        quant = Decimal('1')
    return dval.quantize(quant, rounding=ROUND_DOWN)

# 보너스 지급액 수식
def calc_bonus(
    D_dep, dep_ccy,
    limit_ccy, limit_bonus,
    first_limit_ccy, first_limit,
    ratio_first, ratio_next,
    sum_bonus, sum_deposit_dict,
    rates, currencies
):
    # 입금액을 최초입금한도통화로 환산(ASK)
    D_firstlimit = D_dep * get_cross_rate(dep_ccy, first_limit_ccy, 'ask', rates)
    # 남은 보너스 한도(누적한도통화)
    B_remain_limit = limit_bonus - sum_bonus
    if B_remain_limit <= 0:
        return Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')

    # 최초/추가 구간별 지급
    first_deposit_sum = sum_deposit_dict[dep_ccy]  # 입금통화 누적입금
    if first_deposit_sum == Decimal('0'):
        D_first_max = first_limit * Decimal('100') / Decimal(ratio_first)
        D_first = min(D_firstlimit, D_first_max)
        B_first = D_first * Decimal(ratio_first) / Decimal('100')
        D_next = max(Decimal('0'), D_firstlimit - D_first_max)
        B_next = D_next * Decimal(ratio_next) / Decimal('100')
        B_grant_firstlimit = B_first + B_next
        # 최초입금한도통화 -> 누적보너스한도통화(ASK)
        B_grant_limit = B_grant_firstlimit * get_cross_rate(first_limit_ccy, limit_ccy, 'ask', rates)
    else:
        B_grant_firstlimit = Decimal('0')
        # 전체 입금액을 최초입금한도통화로 환산 -> 누적한도통화로 환산
        B_grant_limit = D_firstlimit * Decimal(ratio_next) / Decimal('100') * get_cross_rate(first_limit_ccy, limit_ccy, 'ask', rates)

    # 누적보너스 한도 적용
    B_apply_limit = min(B_remain_limit, B_grant_limit)
    # 지급액을 입금통화로 환산(BID), 소수점 처리
    B_apply_dep = B_apply_limit * get_cross_rate(limit_ccy, dep_ccy, 'bid', rates)
    dep_digit = currencies[dep_ccy]['digit']
    B_floor_apply_dep = floor_to_digit(B_apply_dep, dep_digit)

    return B_floor_apply_dep, B_apply_limit, D_firstlimit, B_grant_limit

# UI 및 전체 로직
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
    if st.sidebar.button("보너스 소멸 정책 설정", key="bonus_wipe_btn"):
        st.session_state['setting_menu'] = "보너스 소멸 정책 설정"
        setting_menu = "보너스 소멸 정책 설정"
    if st.sidebar.button("초기화", key="reset_btn"):
        st.session_state['setting_menu'] = "초기화"
        setting_menu = "초기화"
    if st.sidebar.button("뒤로가기", key="back_btn"):
        st.session_state['setting_menu'] = None
        setting_menu = None

# 설정 각 메뉴별 세부 UI
if main_menu == "설정" and setting_menu == "환율 및 소수점 수정":
    st.subheader("환율 및 소수점 수정")
    st.write("'적용' 클릭시 전체 초기화 됩니다.")
    new_rates = {}
    new_digits = {}
    st.write("통화쌍 / 환율(bid/ask)")
    for pair in rates.keys():
        col1, col2, col3 = st.columns([2, 2, 2])
        col1.write(pair)
        bid = col2.number_input(
            f"{pair} bid", min_value=0.000001, step=0.000001, value=float(rates[pair]['bid']), key=f"rate_set_{pair}_bid", format="%.6f"
        )
        ask = col3.number_input(
            f"{pair} ask", min_value=0.000001, step=0.000001, value=float(rates[pair]['ask']), key=f"rate_set_{pair}_ask", format="%.6f"
        )
        new_rates[pair] = {'bid': Decimal(str(bid)), 'ask': Decimal(str(ask))}
    for code in currencies.keys():
        d = st.number_input(
            f"{code} 소수점", min_value=0, max_value=8, step=1, value=int(currencies[code]['digit']), key=f"digit_set_{code}"
        )
        new_digits[code] = int(d)
    if st.button("적용(전체초기화)", key="apply_rate_digit"):
        st.session_state['rates'] = new_rates
        st.session_state['currencies'] = {
            code: {'digit': new_digits[code]} for code in currency_list
        }
        st.session_state['accounts'] = {
            code: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')}
            for code in currency_list
        }
        st.session_state['sum_bonus'] = Decimal('0')
        st.session_state['sum_deposit'] = {c: Decimal('0') for c in currency_list}
        st.success("환율/소수점 변경 및 전체 초기화 완료!")

if main_menu == "설정" and setting_menu == "보너스 정책/비율 수정":
    st.subheader("보너스 정책/비율 수정")
    st.write("아래 설정을 변경 후 '적용'을 누르면 전체 초기화 됩니다.")
    col1, col2 = st.columns(2)
    first_bonus_limit_currency = col1.selectbox("최초입금 한도 통화", currency_list, index=currency_list.index(st.session_state['first_bonus_limit']['currency']), key="first_bonus_limit_currency")
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
        st.session_state['accounts'] = {
            code: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')}
            for code in currency_list
        }
        st.session_state['sum_bonus'] = Decimal('0')
        st.session_state['sum_deposit'] = {c: Decimal('0') for c in currency_list}
        st.success("보너스 정책/비율 변경 및 전체 초기화 완료!")

if main_menu == "설정" and setting_menu == "누적보너스 한도 설정":
    st.subheader("누적보너스 한도 설정")
    bonus_limit_currency = st.selectbox("누적보너스 한도 통화", currency_list, index=currency_list.index(st.session_state['bonus_limit']['currency']), key="bonus_limit_currency")
    bonus_limit_value = st.number_input(
        f"누적보너스 한도 ({bonus_limit_currency})", min_value=1.0, value=float(st.session_state['bonus_limit']['limit']), step=1.0, key="bonus_limit_value"
    )
    if st.button("적용(전체초기화)", key="apply_bonus_limit"):
        st.session_state['bonus_limit'] = {"limit": Decimal(str(bonus_limit_value)), "currency": bonus_limit_currency}
        st.session_state['accounts'] = {
            code: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')}
            for code in currency_list
        }
        st.session_state['sum_bonus'] = Decimal('0')
        st.session_state['sum_deposit'] = {c: Decimal('0') for c in currency_list}
        st.success("누적보너스 한도 변경 및 전체 초기화 완료!")

if main_menu == "설정" and setting_menu == "보너스 소멸 정책 설정":
    st.subheader("보너스 소멸 정책 설정")
    wipe_policy = st.session_state['bonus_wipe_policy']
    wipe_currency = st.selectbox("소멸 기준 통화", currency_list, index=currency_list.index(wipe_policy['currency']), key="bonus_wipe_currency")
    wipe_amount = st.number_input(f"소멸 기준 금액 ({wipe_currency})", min_value=0.0, value=float(wipe_policy['amount']), step=1.0, key="bonus_wipe_amount")
    if st.button("적용(전체초기화)", key="apply_bonus_wipe"):
        st.session_state['bonus_wipe_policy'] = {'currency': wipe_currency, 'amount': Decimal(str(wipe_amount))}
        st.session_state['accounts'] = {
            code: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')}
            for code in currency_list
        }
        st.session_state['sum_bonus'] = Decimal('0')
        st.session_state['sum_deposit'] = {c: Decimal('0') for c in currency_list}
        st.success("보너스 소멸 정책 변경 및 전체 초기화 완료!")

if main_menu == "설정" and setting_menu == "초기화":
    st.subheader("전체 초기화")
    if st.button("전체 계좌/보너스 리셋", key="full_reset"):
        st.session_state['accounts'] = {
            code: {'net_capital': Decimal('0'), 'bonus': Decimal('0'), 'credit': Decimal('0'), 'restricted': Decimal('0')}
            for code in currency_list
        }
        st.session_state['sum_bonus'] = Decimal('0')
        st.session_state['sum_deposit'] = {c: Decimal('0') for c in currency_list}
        st.success("모든 계좌 정보가 초기화 되었습니다.")

if main_menu == "설정" and setting_menu == "뒤로가기":
    st.session_state['setting_menu'] = None
    st.sidebar.info("좌측 메뉴에서 '입금/출금'을 다시 선택하세요.")

# 입금/출금 처리
if main_menu == "입금/출금":
    st.sidebar.header("입금/출금")
    st.session_state['setting_menu'] = None
    action = st.sidebar.radio("동작", ["입금", "출금"], key="action")
    currency = st.sidebar.selectbox("통화", currency_list, key="currency")
    digit = currencies[currency]['digit']
    amount_input = st.sidebar.number_input("금액", min_value=0.0, step=0.01, format="%.8f", key="amount")
    amount = floor_to_digit(Decimal(str(amount_input)), digit)
    if st.sidebar.button("실행", key="run_action"):
        acc = st.session_state['accounts'][currency]
        # 정책 변수
        bonus_limit_info = st.session_state['bonus_limit']
        first_bonus_limit_info = st.session_state['first_bonus_limit']
        ratio_first = st.session_state['bonus_ratio_first']
        ratio_next = st.session_state['bonus_ratio_next']
        limit_ccy = bonus_limit_info['currency']
        limit_bonus = bonus_limit_info['limit']
        first_limit_ccy = first_bonus_limit_info['currency']
        first_limit = first_bonus_limit_info['limit']
        sum_bonus = st.session_state['sum_bonus']
        sum_deposit_dict = st.session_state['sum_deposit']

        if action == "입금":
            B_floor_apply_dep, B_apply_limit, D_firstlimit, B_grant_limit = calc_bonus(
                amount, currency,
                limit_ccy, limit_bonus,
                first_limit_ccy, first_limit,
                ratio_first, ratio_next,
                sum_bonus, sum_deposit_dict,
                rates, currencies
            )
            acc['net_capital'] = floor_to_digit(acc['net_capital'] + amount, digit)
            if B_floor_apply_dep > Decimal('0'):
                acc['bonus'] = floor_to_digit(acc['bonus'] + B_floor_apply_dep, digit)
                # 누적보너스 갱신 (입금통화 → 누적한도통화 ASK)
                sum_bonus_inc = B_floor_apply_dep * get_cross_rate(currency, limit_ccy, 'ask', rates)
                sum_bonus_inc = floor_to_digit(sum_bonus_inc, currencies[limit_ccy]['digit'])
                st.session_state['sum_bonus'] += sum_bonus_inc
                st.success(f"{currency} {float(amount):,.{digit}f} 입금 및 보너스 {float(B_floor_apply_dep):,.{digit}f} 지급 (누적: {float(st.session_state['sum_bonus'])} {limit_ccy})")
            else:
                st.success(f"{currency} {float(amount):,.{digit}f} 입금 (보너스 한도 도달로 지급 없음)")
            st.session_state['sum_deposit'][currency] += amount

        elif action == "출금":
            출금가능 = max(Decimal('0'), acc['net_capital'])
            출금액 = min(amount, 출금가능)
            출금액 = floor_to_digit(출금액, digit)
            if 출금액 <= Decimal('0'):
                st.error("출금 가능 순수자본이 부족합니다.")
            else:
                # 출금 시 전체 순수자본 총합(출금통화 기준, BID)
                total_net_in_currency = Decimal('0')
                for code in currency_list:
                    acc0 = st.session_state['accounts'][code]
                    net0 = floor_to_digit(acc0['net_capital'], currencies[code]['digit'])
                    total_net_in_currency += net0 * get_cross_rate(code, currency, 'bid', rates)
                ratio = 출금액 / total_net_in_currency if total_net_in_currency > Decimal('0') else Decimal('1')
                for code in currency_list:
                    acc0 = st.session_state['accounts'][code]
                    digit0 = currencies[code]['digit']
                    acc0['bonus'] = floor_to_digit(acc0['bonus'] * (Decimal('1') - ratio), digit0)
                acc['net_capital'] = floor_to_digit(acc['net_capital'] - 출금액, digit)
                # 보너스 소멸 정책
                wipe_policy = st.session_state['bonus_wipe_policy']
                wipe_currency = wipe_policy['currency']
                wipe_amount = wipe_policy['amount']
                total_net_for_wipe = Decimal('0')
                for code in currency_list:
                    acc0 = st.session_state['accounts'][code]
                    d0 = currencies[code]['digit']
                    net0 = floor_to_digit(acc0['net_capital'], d0)
                    net_in_wipe = net0 * get_cross_rate(code, wipe_currency, 'bid', rates)
                    total_net_for_wipe += net_in_wipe
                if total_net_for_wipe < wipe_amount:
                    for code in currency_list:
                        st.session_state['accounts'][code]['bonus'] = Decimal('0')
                st.success(f"{currency} {float(출금액):,.{digit}f} 출금 완료 (보너스 {float(ratio * 100):.2f}% 차감)")

# 계좌 현황 및 합산
accounts = st.session_state['accounts']
st.write("### 통화별 계좌 현황")
rows = []
for code in currency_list:
    data = accounts[code]
    d = currencies[code]['digit']
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
합산기준통화 = st.selectbox("합산(환산):", currency_list, index=0)
main_digit = currencies[합산기준통화]['digit']

def total_by_key(key):
    total = Decimal('0')
    for code in currency_list:
        if key == 'balance':
            val = floor_to_digit(accounts[code]['net_capital'] + accounts[code]['bonus'] + accounts[code]['credit'] + accounts[code]['restricted'], currencies[code]['digit'])
        else:
            val = floor_to_digit(accounts[code][key], currencies[code]['digit'])
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
sum_bonus = st.session_state['sum_bonus']
wipe_policy = st.session_state['bonus_wipe_policy']

st.write(f"**총자산 (Total balance):** {float(total_balance):,.{main_digit}f} {합산기준통화}  =  순수자본 + 보너스 + 크레딧 + 출금제한")
st.write(f"** - 순수자본:** {float(net_asset):,.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈보너스:** {float(total_bonus):,.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈크레딧:** {float(total_credit):,.{main_digit}f} {합산기준통화}")
st.write(f"** - 토탈출금제한:** {float(total_restricted):,.{main_digit}f} {합산기준통화}")
st.write(f"**누적보너스 ({bonus_limit_currency} 기준, 지급총액):** {float(sum_bonus):,.{currencies[bonus_limit_currency]['digit']}f} / {float(bonus_limit_value):,.{currencies[bonus_limit_currency]['digit']}f} {bonus_limit_currency}")

st.info(f'''
- 신규 고객의 최초 입금에 한해, 입금 금액의 {st.session_state['bonus_ratio_first']}%를 보너스로 지급. 단, 최초 입금에 대한 보너스는 최대 {st.session_state['first_bonus_limit']['limit']} {st.session_state['first_bonus_limit']['currency']}를 한도로 함.
- 최초 입금 시 보너스 한도를 넘는 입금 차액(한도 초과분) 또는 추가 입금에 대해서는 입금 금액의 {st.session_state['bonus_ratio_next']}%를 보너스로 지급
- 고객 1인의 보너스 누적 한도는 {st.session_state['bonus_limit']['limit']} {st.session_state['bonus_limit']['currency']}로 제한
- balance = 순수자본 + 보너스 + credit + restricted
- 총자산 = 순수자본 + 토탈보너스 + 토탈크레딧 + 토탈출금제한
- 출금 시 보너스를 제외한 계좌 잔액 대비 출금 금액에 해당하는 비율만큼, 보너스 잔액도 비례하여 차감
- 출금 후 전체 순수자본({wipe_policy['currency']}) 환산 기준 {wipe_policy['amount']} 미만이면 모든 보너스가 전액 소멸됩니다.
''')
