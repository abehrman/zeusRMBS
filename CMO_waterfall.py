""" Module for producing waterfall tables based on input collateral criteria. AKA amortization table."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import prepayment_calcs as pc

class CMO():

    def __init__(self,original_balance=400e6, pass_thru_cpn=0.055, wac=0.06, original_maturity=360, wam=358, psa_speed=1.0,
                         cpr_description='.2 ramp 6 for 30, 6', servicing=None, bonds=[]):

        print('Initializing...')
        self.original_balance = original_balance
        self.pass_thru_cpn = pass_thru_cpn
        self.wac = wac
        self.original_maturity = original_maturity
        self.wam = wam
        self.psa_speed = psa_speed
        self.cpr_description = cpr_description
        self.servicing = servicing
        self.bonds = bonds

        print('Creating collateral waterfall...')
        self.collateral_waterfall = self.create_collateral_waterfall()

        print('Producing CMO waterfall...')
        self.cmo_waterfalls = self.calc_seq_bond_cfs_directed_cash(self.collateral_waterfall, self.bonds)

        print('Merging waterfalls...')
        self.waterfall = self.collateral_waterfall.merge(self.cmo_waterfalls, left_index=True, right_index=True)

        print('Done...')

    def create_collateral_waterfall(self):
        """ Takes collateral summary inputs based on aggregations equaling total original balance, average pass-thru-coupon,
        weighted average coupon of underlying loans, weighted average maturity of underlying loans, psa speed multiplier
        for prepayment curve, and constant prepayment rate curve description.

        CPR description is turned into a list of CPRs which are then run through the SMM function for period SMMs."""

        cpr_curve = pc.cpr_curve_creator(self.cpr_description)
        age = self.original_maturity - self.wam

        index = pd.Index(range(1, self.wam + 1), name='month')

        beg_balance = np.zeros(self.wam)
        smm = np.array([pc.smm(cpr_curve[period + age - 1] * self.psa_speed) for period in index])

        rem_cols = pd.DataFrame({
            'mortgage_payments': np.zeros(self.wam),
            'net_interest': np.zeros(self.wam),
            'scheduled_principal': np.zeros(self.wam),
            'prepayments': np.zeros(self.wam),
            'total_principal': np.zeros(self.wam),
            'cash_flow': np.zeros(self.wam),
            'servicing': np.zeros(self.wam)
        }, index=index)

        waterfall = pd.DataFrame(data=[beg_balance, smm]).T
        waterfall.columns = ['beginning_balance', 'SMM']
        waterfall.index = index
        waterfall = waterfall.join(rem_cols)

        for ix, row in waterfall.iterrows():
            if ix == 1:
                row['beginning_balance'] = self.original_balance
            else:
                row['beginning_balance'] = waterfall['beginning_balance'].ix[ix - 1] - waterfall['total_principal'].ix[
                    ix - 1]

            row['mortgage_payments'] = -np.pmt(rate=self.wac / 12.,
                                               nper=self.wam - ix + 1,
                                               pv=row['beginning_balance'],
                                               fv=0.,
                                               when='end')

            row['net_interest'] = row['beginning_balance'] * self.pass_thru_cpn / 12.
            gross_coupon = row['beginning_balance'] * (self.wac / 12.)

            row['scheduled_principal'] = row['mortgage_payments'] - gross_coupon

            row['prepayments'] = row['SMM'] * (row['beginning_balance'] - row['scheduled_principal'])

            row['total_principal'] = row['scheduled_principal'] + row['prepayments']

            if self.servicing is None:
                row['servicing'] = row['mortgage_payments'] - (row['net_interest'] + row['total_principal'])
            else:
                row['servicing'] = row['beginning_balance'] * self.servicing

            row['cash_flow'] = row['net_interest'] + row['total_principal'] + row['servicing']


        return waterfall


    def calc_seq_bond_cfs(self, collateral_waterfall, bonds):
        bond_waterfalls = {}
        for bond in bonds:
            current_bond = bond['Bond']
            bond_waterfalls[current_bond] = pd.DataFrame(
                index=collateral_waterfall.index.values,
                columns=['Bond_' + current_bond,
                         'Coupon_' + current_bond,
                         'Balance_' + current_bond,
                         'Principal_' + current_bond,
                         'Interest_' + current_bond,
                         'Cashflow_' + current_bond])
            bond_waterfalls[current_bond]['Bond_' + current_bond] = current_bond
            bond_waterfalls[current_bond]['Coupon_' + current_bond] = bond['Coupon']
            bond_waterfalls[current_bond].loc[1, 'Balance_' + current_bond] = bond['Balance']
            bond_waterfalls[current_bond].loc[1, 'Scheduled_Payment_' + current_bond] = np.nan

        final_df = pd.DataFrame(index=collateral_waterfall.index, columns=['remaining_cash'])

        # for k, v in collateral_waterfall.iterrows():
        for k in collateral_waterfall.index.values:
            rem_cash = np.float(collateral_waterfall.loc[k, 'cash_flow'])
            # pay interest

            for i in range(len(bonds)):

                current_bond = bonds[i]['Bond']

                if k > 1:
                    bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond] = \
                        bond_waterfalls[current_bond].loc[k - 1, 'Balance_' + current_bond] - \
                        (bond_waterfalls[current_bond].loc[k - 1, 'Cashflow_' + current_bond] - \
                         bond_waterfalls[current_bond].loc[k - 1, 'Interest_' + current_bond])

                bond_waterfalls[current_bond].loc[k, 'Interest_' + current_bond] = round(-np.ipmt(
                    bond_waterfalls[current_bond].loc[k, 'Coupon_' + current_bond] / 12,
                    1,
                    361 - k,
                    bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond]), 2)

                bond_waterfalls[current_bond].loc[k, 'Scheduled_Payment_' + current_bond] = round(-np.pmt(
                    bond_waterfalls[current_bond].loc[k, 'Coupon_' + current_bond] / 12,
                    361 - k,
                    bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond]), 2)

                interest_cash_flow = min(
                    np.float(bond_waterfalls[current_bond].loc[k, 'Interest_' + current_bond]),
                    np.float(rem_cash))

                bond_waterfalls[current_bond].loc[k, 'Cashflow_' + current_bond] = interest_cash_flow

                rem_cash -= interest_cash_flow

            # pay principal
            for i in range(len(bonds)):
                current_bond = bonds[i]['Bond']

                principal_cash_flow = min(
                    np.float(bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond]),
                    np.float(rem_cash))

                bond_waterfalls[current_bond].loc[k, 'Principal_' + current_bond] = principal_cash_flow
                bond_waterfalls[current_bond].loc[k, 'Cashflow_' + current_bond] += principal_cash_flow
                rem_cash -= principal_cash_flow

            final_df.loc[k, 'remaining_cash'] = rem_cash

        for i in range(len(bonds)):
            current_bond = bonds[i]['Bond']
            final_df = final_df.merge(bond_waterfalls[current_bond],
                                      left_index=True,
                                      right_index=True)

        return final_df

    def calc_seq_bond_cfs_directed_cash(self, collateral_waterfall, bonds):
        bond_waterfalls = {}
        for bond in bonds:
            current_bond = bond['Bond']
            bond_waterfalls[current_bond] = pd.DataFrame(
                index=collateral_waterfall.index.values,
                columns=['Bond_' + current_bond,
                         'Coupon_' + current_bond,
                         'Balance_' + current_bond,
                         'Principal_' + current_bond,
                         'Interest_' + current_bond,
                         'Cashflow_' + current_bond,
                         'Type_' + current_bond])
            bond_waterfalls[current_bond]['Bond_' + current_bond] = current_bond
            bond_waterfalls[current_bond]['Coupon_' + current_bond] = bond['Coupon']
            bond_waterfalls[current_bond].loc[1, 'Balance_' + current_bond] = bond['Balance']
            bond_waterfalls[current_bond].loc[1, 'Scheduled_Payment_' + current_bond] = np.nan

            try:
                bond_waterfalls[current_bond]['Type_' + current_bond] = bond['Type']
            except KeyError:
                bond_waterfalls[current_bond]['Type_' + current_bond] = None

        final_df = pd.DataFrame(index=collateral_waterfall.index, columns=['remaining_interest',
                                                                           'remaining_principal'])

        # for k, v in collateral_waterfall.iterrows():
        for k in collateral_waterfall.index.values:
            rem_interest_cash = np.float(collateral_waterfall.loc[k, 'net_interest'])
            rem_principal_cash = np.float(collateral_waterfall.loc[k, 'total_principal'])
            # pay interest

            for i in range(len(bonds)):

                current_bond = bonds[i]['Bond']

                # Calculate current period beginning principal = prior period principal - principal pay down
                # (calculated as total period cash flow less interest paid)

                if k > 1:


                    # add prior period interest to accrual bond principal
                    try:
                        if bonds[i]['Type'] == 'accrual' and \
                                        rem_interest_cash != np.float(collateral_waterfall.loc[k, 'net_interest']):
                            bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond] = \
                                bond_waterfalls[current_bond].loc[k - 1, 'Balance_' + current_bond] + \
                                bond_waterfalls[current_bond].loc[k - 1, 'Interest_' + current_bond]

                        else:
                            bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond] = \
                                bond_waterfalls[current_bond].loc[k - 1, 'Balance_' + current_bond] - \
                                (bond_waterfalls[current_bond].loc[k - 1, 'Cashflow_' + current_bond] - \
                                 bond_waterfalls[current_bond].loc[k - 1, 'Interest_' + current_bond])

                    except KeyError:
                        bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond] = \
                            bond_waterfalls[current_bond].loc[k - 1, 'Balance_' + current_bond] - \
                            (bond_waterfalls[current_bond].loc[k - 1, 'Cashflow_' + current_bond] - \
                             bond_waterfalls[current_bond].loc[k - 1, 'Interest_' + current_bond])

                # calculate interest due for period

                #bond_waterfalls[current_bond].loc[k, 'Interest_' + current_bond] = round(-np.ipmt(
                #     bond_waterfalls[current_bond].loc[k, 'Coupon_' + current_bond] / 12,
                #     1,
                #     361 - k,
                #     bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond]), 2)

                bond_waterfalls[current_bond].loc[k, 'Interest_' + current_bond] = \
                    (bond_waterfalls[current_bond].loc[k, 'Coupon_' + current_bond] / 12) * \
                    bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond]


                # calculate scheduled payment for period

                bond_waterfalls[current_bond].loc[k, 'Scheduled_Payment_' + current_bond] = round(-np.pmt(
                    bond_waterfalls[current_bond].loc[k, 'Coupon_' + current_bond] / 12,
                    361 - k,
                    bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond]), 2)

                # interest payment cannot be greater than available interest

                interest_cash_flow = min(
                    np.float(bond_waterfalls[current_bond].loc[k, 'Interest_' + current_bond]),
                    np.float(rem_interest_cash))

                # redirect accrual bond interest cash flows to pay down other bond principal quicker
                try:
                    if bonds[i]['Type'] == 'accrual' and \
                            rem_interest_cash != np.float(collateral_waterfall.loc[k, 'net_interest']):
                        bond_waterfalls[current_bond].loc[k, 'Cashflow_' + current_bond] = 0
                        rem_principal_cash += interest_cash_flow  # add accrual tranche interest to principal available

                    # for non-accrual bonds, pay interest cashflow
                    else:
                        bond_waterfalls[current_bond].loc[k, 'Cashflow_' + current_bond] = interest_cash_flow
                except KeyError:
                        bond_waterfalls[current_bond].loc[k, 'Cashflow_' + current_bond] = interest_cash_flow

                rem_interest_cash -= interest_cash_flow

            # pay principal
            for i in range(len(bonds)):
                current_bond = bonds[i]['Bond']

                principal_cash_flow = min(
                    np.float(bond_waterfalls[current_bond].loc[k, 'Balance_' + current_bond]),
                    np.float(rem_principal_cash))

                bond_waterfalls[current_bond].loc[k, 'Principal_' + current_bond] = principal_cash_flow
                bond_waterfalls[current_bond].loc[k, 'Cashflow_' + current_bond] += principal_cash_flow
                rem_principal_cash -= principal_cash_flow

            final_df.loc[k, 'remaining_principal'] = rem_principal_cash
            final_df.loc[k, 'remaining_interest'] = rem_interest_cash

        for i in range(len(bonds)):
            current_bond = bonds[i]['Bond']
            final_df = final_df.merge(bond_waterfalls[current_bond],
                                      left_index=True,
                                      right_index=True)

        return final_df
