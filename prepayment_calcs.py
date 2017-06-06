""" Functions for calculating prepayment features such as 

single monthly mortality (SMM) => $SMM = 1 - (1 - CPR)^(1/12)$

constant prepayment rate (CPR) => $CPR = 1 - ((1 - SMM)^12)$

PSA benchmark => PSA = $month * 0.002 if month <= 30 else 6$

Also contains function to produce CPR curves based on text descriptions, i.e. PSA benchmark = '0.2 ramp 6 for 30, 6'"""

import numpy as np
import pandas as pd
from bokeh.io import output_file


def smm(cpr):
    return 1 - (1 - cpr) ** (1 / 12)


def cpr(smm):
    return 1 - ((1 - smm) ** 12)


def psa(month):
    return month * 0.002 if month <= 30 else .06


def cpr_curve_creator(description='.2 ramp 6 for 30, 6'):
    """ Produces a 360 period CPR curve described by a text input string. Acceptable input is of the form
    '<start cpr> ramp <end cpr> for <duration>'.
    
    Periods are separated by commas ','
    
    Only <start cpr> is required. If no <duration> is provided, the final instruction will carry to 360 periods, i.e. 
    '6' as the input will produce a CPR curve of 6 through period 360; 
    
    To produce 100 PSA, the input string is '.2 ramp 6 for 30, 6'
    
    Returns PSA by default
    """

    periods = str(description).split(',')
    nperiods = 360
    end_period = False

    cpr_curve = []

    current_period = 1

    for period in periods:
        start_cpr = 0
        end_cpr = 0
        period_duration = 0
        cpr_increment = 0
        period_curve = None

        if period == periods[-1]:
            end_period = True

        period_duration = nperiods + current_period
        words = period.strip().split(' ')

        for i in range(len(words)):
            if i == 0:
                start_cpr = float(words[i]) / 100.
                end_cpr = float(words[i]) / 100.
            elif words[i] == 'ramp':
                end_cpr = float(words[i + 1]) / 100.
            elif words[i] == 'for':
                period_duration = float(words[i + 1])

        period_curve = np.linspace(start_cpr, end_cpr, period_duration)

        cpr_curve.extend(list(period_curve))
        current_period += period_duration

    return cpr_curve


def prepayment_curve_from_passive_active_composition(fast_smm, fast_amount, slow_smm, slow_amount, periods):
    """ Produces a CPR curve from a heterogenous composition of a pool fast/active prepayers and slow/passive prepayers.
    Inputs are speed of prepayment for each group and their starting composition"""

    df = pd.DataFrame(0, index=np.arange(periods), columns=['fast_amount', 'fast_smm', 'slow_amount', 'slow_smm',
                                                            'pool_smm', 'pool_cpr'])

    df.loc[0, 'fast_amount'] = fast_amount
    df['fast_smm'] = fast_smm

    df.loc[0, 'slow_amount'] = slow_amount
    df['slow_smm'] = slow_smm

    df.loc[0, 'pool_smm'] = (df.loc[0, 'fast_amount'] * df.loc[0, 'fast_smm']) + \
                            (df.loc[0, 'slow_amount'] * df.loc[0, 'slow_smm'])

    for i in range(1, len(df.index)):
        df.loc[i, 'fast_amount'] = df.loc[i - 1, 'fast_amount'] * ((1 - df.loc[i - 1, 'fast_smm']) /
                                                                   (1 - df.loc[i - 1, 'pool_smm']))

        df.loc[i, 'slow_amount'] = df.loc[i - 1, 'slow_amount'] * ((1 - df.loc[i - 1, 'slow_smm']) /
                                                                   (1 - df.loc[i - 1, 'pool_smm']))

        df.loc[i, 'pool_smm'] = (df.loc[i, 'fast_amount'] * df.loc[i, 'fast_smm']) + \
                                (df.loc[i, 'slow_amount'] * df.loc[i, 'slow_smm'])

    df['pool_cpr'] = df['pool_smm'].apply(cpr)

    return df


def age_perc(age, e=30):
    '''
    Calculate age factor for prepayment speed determination
    :param age: current month of seasoning
    :param e: age divisor, max age, i.e. if e = 30 and current month >= 30 then 1
    :return: percent seasoning factor for prepayment calc
    '''
    return min(age / e, 1)


def burn_perc(factor, f=0.7):
    '''
    Calculates factor input for prepayment speed determination of the amount of burnout
    return 1 - f * (1 - factor)
    '''

if __name__ == '__main__':
    # output_file('psa.html')
    # # hover = HoverTool(tooltips=[
    # #     ('Mortgage Age', '$x'),
    # #     ('Annual CPR', '$y')
    # # ])
    # # p = figure(title="PSA speeds", tools=[hover])
    # # periods = range(1, 361)
    # #
    # # for mult in np.linspace(0.5, 1.5, num=3):
    # #     x = []
    # #     y = []
    # #
    # #     for period in periods:
    # #         x.append(period)
    # #         y.append(PSA(period) * mult)
    # #     p.line(x, y, name='PSA-{0:.2f}'.format(mult))
    # # show(p)
    # a = cpr_curve_creator('.2 ramp 6 for 30, 6')
    # print(len(a))
    # # p = figure()
    # # p.circle(range(1, 361),
    # #          cpr_curve_creator('0 for 20, .2 ramp 6 for 30, 9 for 15, 9 ramp 8 for 35, 2 ramp 7 for 70, 6'))
    # # show(p)

    a = cpr_curve_creator('.2 ramp 6 for 30, 6')
    print(a)