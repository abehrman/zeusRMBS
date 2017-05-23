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
        self._bond_waterfalls = {}
        for bond in bonds:
            current_bond = bond['Bond']
            self._bond_waterfalls[current_bond] = pd.DataFrame(
                index=collateral_waterfall.index.values,
                columns=['Bond_' + current_bond,
                         'Coupon_' + current_bond,
                         'Balance_' + current_bond,
                         'Principal_' + current_bond,
                         'Interest_Due_' + current_bond,
                         'Interest_Paid_' + current_bond,
                         'Cashflow_' + current_bond,
                         'Type_' + current_bond])
            self._bond_waterfalls[current_bond]['Bond_' + current_bond] = current_bond
            self._bond_waterfalls[current_bond]['Coupon_' + current_bond] = bond['Coupon']
            self._bond_waterfalls[current_bond].loc[1, 'Balance_' + current_bond] = bond['Balance']
            #self._bond_waterfalls[current_bond].loc[1, 'Scheduled_Payment_' + current_bond] = np.nan
            self._bond_waterfalls[current_bond]['Type_' + current_bond] = self._bond_type(bond)


        final_df = pd.DataFrame(index=collateral_waterfall.index, columns=['remaining_interest',
                                                                           'remaining_principal'])

        # for k, v in collateral_waterfall.iterrows():
        for period in collateral_waterfall.index.values:


            self._rem_interest_cash = np.float(collateral_waterfall.loc[period, 'net_interest'])
            self._rem_principal_cash = np.float(collateral_waterfall.loc[period, 'total_principal'])

            # set new period balances

            for i in range(len(bonds)):
                current_bond = bonds[i]['Bond']
                if period > 1:
                    new_balance = self._calc_period_beginning_balance(current_bond, period)
                    self._bond_waterfalls[current_bond].loc[period, 'Balance_' + current_bond] = new_balance

                else:
                    new_balance = bonds[i]['Balance']

            self._non_accrual_principal = self._calc_non_accrual_principal_balances(period)

            # pay interest

            for i in range(len(bonds)):
                current_bond = bonds[i]['Bond']
                coupon = self._bond_waterfalls[current_bond].loc[period, 'Coupon_' + current_bond]
                is_accrual = self._bond_type(bonds[i]) == 'accrual'

                # calculate interest due and paid

                interest_due, interest_paid = self._calc_interest_payment(period,
                                                                          self._bond_waterfalls[current_bond].loc[
                                                                              period, 'Balance_' + current_bond],
                                                                          coupon,
                                                                          is_accrual)

                self._bond_waterfalls[current_bond].loc[period, 'Interest_Due_' + current_bond] = interest_due
                self._bond_waterfalls[current_bond].loc[period, 'Interest_Paid_' + current_bond] = interest_paid

                self._bond_waterfalls[current_bond].loc[period, 'Cashflow_' + current_bond] = interest_paid

                # not using...calculate period scheduled payment

                #scheduled_payment = round(-np.pmt(coupon / 12, 361 - period, new_balance), 2)

                #self._bond_waterfalls[current_bond].loc[period, 'Scheduled_Payment_' + current_bond] = scheduled_payment


            # pay principal

            # TODO: principal pay down not showing in Z-bond dataframe
            
            for i in range(len(bonds)):
                current_bond = bonds[i]['Bond']
                if self._rem_principal_cash > 0:
                    principal_cash_flow = min(
                        np.float(self._bond_waterfalls[current_bond].loc[period, 'Balance_' + current_bond]),
                        np.float(self._rem_principal_cash))

                    self._bond_waterfalls[current_bond].loc[period, 'Principal_' + current_bond] = principal_cash_flow
                    self._bond_waterfalls[current_bond].loc[period, 'Cashflow_' + current_bond] += principal_cash_flow
                    self._rem_principal_cash -= principal_cash_flow

                else:
                    self._bond_waterfalls[current_bond].loc[period, 'Principal_' + current_bond] = 0

            final_df.loc[period, 'remaining_principal'] = self._rem_principal_cash
            final_df.loc[period, 'remaining_interest'] = self._rem_interest_cash

        for i in range(len(bonds)):
            current_bond = bonds[i]['Bond']
            final_df = final_df.merge(self._bond_waterfalls[current_bond],
                                      left_index=True,
                                      right_index=True)

        return final_df

    @staticmethod
    def _bond_type(bond):
        try:
            return bond['Type']
        except KeyError:
            return None


    def _calc_non_accrual_principal_balances(self, period):
        """

        :param bond_waterfall_df: dataframe for bond waterfalls
        :return: outstanding balances of non_accrual bonds
        """

        non_accrual_principal_balances = 0

        for bond in self.bonds:
            current_bond = bond['Bond']

            if self._bond_type(bond) != 'accrual':
                non_accrual_principal_balances += self._bond_waterfalls[current_bond].loc[period,
                                                                                          'Balance_' + current_bond]

        return non_accrual_principal_balances


    def _calc_period_beginning_balance(self, current_bond, period):

        """
        :param bond_df: dataframe for current bond
        :param current_bond: designation (i.e. 'A', 'B', 'Z') for bond being evaluated
        :param period: current period in waterfall
        :param is_accrual: boolean, is the bond of type 'accrual'
        :return:Calculate current period beginning principal = prior period principal - principal pay down
        (calculated as total period cash flow less interest paid)
        """

        # all values below are taken from the priod period in the waterfall
        prior_period = period - 1

        bond_df = self._bond_waterfalls[current_bond]

        starting_balance = bond_df.loc[prior_period, 'Balance_' + current_bond]

        interest_due = bond_df.loc[prior_period, 'Interest_Due_' + current_bond]
        interest_paid = bond_df.loc[prior_period, 'Interest_Paid_' + current_bond]

        interest_due_unpaid = interest_due - interest_paid
        principal_paid = bond_df.loc[prior_period, 'Principal_' + current_bond]

        return  starting_balance + interest_due_unpaid - principal_paid


    def _calc_interest_payment(self, period, balance, coupon, is_accrual):
        """

        :param bond_df: dataframe for current bond
        :param period: int, current period in waterfall
        :param current_bond: str, bond identifier (i.e. 'A', 'B', 'Z')
        :param cash_available: float, cash available for interest payment
        :param is_accrual: boolean, is the bond being evaluated of type accrual
        :return: floats, the amount of interest due and the interest payment as a two values => due, payment
        """

        interest_due = balance * (coupon / 12)
        interest_cash_redirected_to_principal = 0

        if is_accrual == False:
            interest_paid = min(interest_due, self._rem_interest_cash)

        else:

            # calculate non-accrual bond principal balance not completely covered by available cash for principal
            non_accrual_rem_principal = self._non_accrual_principal - self._rem_principal_cash

            # redirect necessary amount of cash to pay down as much non-accrual principal as possible
            interest_cash_redirected_to_principal = min(interest_due,
                                                                    non_accrual_rem_principal)

            # interest paid to accrual bond is the remaining balance after paying down non-accrual bond principal to 0
            interest_paid = interest_due - interest_cash_redirected_to_principal


        # remaining interest cash is reduced by the interest paid out
        self._rem_interest_cash -= (interest_paid + interest_cash_redirected_to_principal)
        self._rem_principal_cash += interest_cash_redirected_to_principal

        return interest_due, interest_paid

if __name__ == '__main__':
    initial_balance = 100e6  # 100 million
    net_coupon = 0.10  # 10%
    gross_coupon = 0.1065  # 10.65%
    maturity = 360  # 30 years => monthly
    servicing = 0.0  # servicing = 25bps

    bonds = [
        {'Bond': 'A',
         'Balance': 30e6,
         'Coupon': 0.07},

        {'Bond': 'B',
         'Balance': 40e6,
         'Coupon': 0.09},

        {'Bond': 'C',
         'Balance': 30e6,
         'Coupon': 0.10}
    ]

    bonds_with_zbond = [
        {'Bond': 'A',
         'Balance': 30e6,
         'Coupon': 0.07},

        {'Bond': 'B',
         'Balance': 40e6,
         'Coupon': 0.09},

        {'Bond': 'Z',
         'Balance': 30e6,
         'Coupon': 0.10,
         'Type': 'accrual'}
    ]


    struct = CMO(original_balance=initial_balance,
                     pass_thru_cpn=net_coupon,
                     wac=gross_coupon,
                     wam=maturity,
                     psa_speed=1.75,
                     servicing=servicing,
                     bonds=bonds_with_zbond)

    struct.waterfall.to_clipboard()