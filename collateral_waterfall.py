import numpy as np
import pandas as pd

import prepayment_calcs as pc


def create_waterfall(original_balance=400e6, pass_thru_cpn=0.055, wac=0.06, wam=358, psa_speed=1.0,
                     cpr_description='.2 ramp 6 for 30, 6'):
    cpr_curve = pc.cpr_curve_creator(cpr_description)
    age = 360 - wam

    index = pd.Index(range(1, wam + 1), name='month')

    beg_balance = np.zeros(wam)
    smm = np.array([pc.SMM(cpr_curve[period + age - 1] * psa_speed) for period in index])

    rem_cols = pd.DataFrame({
        'mortgage_payments': np.zeros(wam),
        'net_interest': np.zeros(wam),
        'scheduled_principal': np.zeros(wam),
        'prepayments': np.zeros(wam),
        'total_principal': np.zeros(wam),
        'cash_flow': np.zeros(wam)
    }, index=index)

    waterfall = pd.DataFrame(data=[beg_balance, smm]).T
    waterfall.columns = ['beginning_balance', 'SMM']
    waterfall.index = index
    waterfall = waterfall.join(rem_cols)

    for ix, row in waterfall.iterrows():
        if ix == 1:
            row['beginning_balance'] = original_balance
        else:
            row['beginning_balance'] = waterfall['beginning_balance'].ix[ix - 1] - waterfall['total_principal'].ix[
                ix - 1]

        row['mortgage_payments'] = -np.pmt(rate=wac / 12,
                                           nper=wam - ix + 1,
                                           pv=row['beginning_balance'],
                                           fv=0,
                                           when='end')

        row['net_interest'] = row['beginning_balance'] * pass_thru_cpn / 12
        gross_coupon = row['beginning_balance'] * (wac / 12.)

        row['scheduled_principal'] = row['mortgage_payments'] - gross_coupon

        row['prepayments'] = row['SMM'] * (row['beginning_balance'] - row['scheduled_principal'])

        row['total_principal'] = row['scheduled_principal'] + row['prepayments']
        row['total_principal'] = row['scheduled_principal'] + row['prepayments']
        row['cash_flow'] = row['net_interest'] + row['total_principal']

    return waterfall


def calculate_balance(previous_balance, reductions=0):
    return previous_balance - reductions


if __name__ == "__main__":
    a = create_waterfall()
    print(a.head())
