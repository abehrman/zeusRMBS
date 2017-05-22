""" Module for producing waterfall tables based on input collateral criteria. AKA amortization table."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import prepayment_calcs as pc

def create_waterfall(original_balance=400e6, pass_thru_cpn=0.055, wac=0.06, wam=358, psa_speed=1.0,
                         cpr_description='.2 ramp 6 for 30, 6', servicing=0):
    """ Takes collateral summary inputs based on aggregations equaling total original balance, average pass-thru-coupon,
    weighted average coupon of underlying loans, weighted average maturity of underlying loans, psa speed multiplier
    for prepayment curve, and constant prepayment rate curve description.

    CPR description is turned into a list of CPRs which are then run through the SMM function for period SMMs."""

    cpr_curve = pc.cpr_curve_creator(cpr_description)
    age = 360 - wam

    index = pd.Index(range(1, wam + 1), name='month')

    beg_balance = np.zeros(wam)
    smm = np.array([pc.smm(cpr_curve[period + age - 1] * psa_speed) for period in index])

    rem_cols = pd.DataFrame({
        'mortgage_payments': np.zeros(wam),
        'net_interest': np.zeros(wam),
        'scheduled_principal': np.zeros(wam),
        'prepayments': np.zeros(wam),
        'total_principal': np.zeros(wam),
        'cash_flow': np.zeros(wam),
        'servicing': np.zeros(wam)
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

        row['mortgage_payments'] = -np.pmt(rate=wac / 12.,
                                           nper=wam - ix + 1,
                                           pv=row['beginning_balance'],
                                           fv=0.,
                                           when='end')

        row['net_interest'] = row['beginning_balance'] * pass_thru_cpn / 12.
        gross_coupon = row['beginning_balance'] * (wac / 12.)

        row['scheduled_principal'] = row['mortgage_payments'] - gross_coupon

        row['prepayments'] = row['SMM'] * (row['beginning_balance'] - row['scheduled_principal'])

        row['total_principal'] = row['scheduled_principal'] + row['prepayments']
        row['cash_flow'] = row['net_interest'] + row['total_principal']
        row['servicing'] = row['beginning_balance'] * servicing

    return waterfall

def schedule_of_ending_balances(rate, nper, pv):
    """ Returns data frame of scheduled balances and each periods scheduled balance as a %
    of the original balance"""

    df = pd.DataFrame(data=np.zeros([nper + 1, 1]), columns=['scheduled_balance'],
                      index=[np.arange(0, nper + 1)])
    df.loc[0, 'scheduled_balance'] = pv

    df['bal_percent'] = (1. - (((1. + rate / 12.) ** np.array(df.index) - 1.) /
                               ((1. + rate / 12.) ** nper - 1.)))

    df.loc[:, 'scheduled_balance'] = df['bal_percent'] * df.loc[0, 'scheduled_balance']

    return df

def schedule_of_ending_balance_percent_for_period(rate, nper, age):
    return (1. - ((((1 + rate) ** age) - 1.) /
                  (((1 + rate) ** nper) - 1.)))

def actual_balances(ending_balances, smm):
    """ Returns vector of actual balances and their fractional composition of scheuled"""
    # age = 361 - len(ending_balances)

    return ending_balances[:-1] * (1 - np.array(smm))

def arm_coupons(rate_curve,
                gross_margin,
                total_fees,
                initial_coupon,
                periodic_cap):
    df = pd.DataFrame(index=pd.Index(range(len(rate_curve))),
                      columns=['rates', 'Gross', 'Net'])
    df.rates = rate_curve
    df.loc[0, 'Gross'] = initial_coupon

    for i in range(1, df.index.max() + 1):
        if df.rates[i] + gross_margin <= df.Gross[i - 1] + periodic_cap:
            df.loc[i, 'Gross'] = df.rates[i] + gross_margin
        else:
            df.loc[i, 'Gross'] = df.Gross[i - 1] + periodic_cap

    df.loc[:, 'Net'] = df.Gross - total_fees

    return df

def example_matrix_of_balance_outstanding_by_age_and_coupon():
    coupon = list([0.06, 0.08, 0.10])
    age = list([60, 120, 180, 240, 300, 359])

    results = []
    for i in coupon:
        column = []
        for j in age:
            column.append(CMO.schedule_of_ending_balance_percent_for_period(i / 12, 360, j))
        results.append(column)

    df = pd.DataFrame(results).T
    df.columns = coupon
    df.index = age
    return df

def example_waterfalls_at_different_prepays():
    waterfall = {}

    figure, axes = plt.subplots()
    for i in range(3):
        for j in range(4):
            print(i,j)
            waterfall[i, j] = create_waterfall(original_balance=200000,
                                                  psa_speed=i + (j * 0.25),
                                                  pass_thru_cpn=0.075,
                                                  wac=0.075,
                                                  wam=360)
            waterfall[i, j].beginning_balance.plot(ax=axes)
    plt.show()

def example_arm_coupon_determinations():
    rates = [None, 8.2, 5., 5.75, 4.]
    df = CMO.arm_coupons(rates, 1.75, 0.65, 5.1, 1)

# if __name__ == "__main__":
#     cw = create_waterfall()
#
#     a = example_matrix_of_balance_outstanding_by_age_and_coupon()
#     print(a)
