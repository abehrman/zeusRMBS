""" Module for producing waterfall tables based on input collateral criteria. AKA amortization table."""
import numpy as np
import pandas as pd

import prepayment_calcs as pc


class CMO:
    def __init__(self, bonds: list,
                 original_balance=400e6,
                 pass_thru_cpn=0.055,
                 wac=0.06,
                 original_maturity=360,
                 wam=358,
                 psa_speed=1.0,
                 cpr_description: object = '.2 ramp 6 for 30, 6',
                 servicing: float = None):

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
        self.collateral_waterfall = self._create_collateral_waterfall

        print('Producing CMO waterfall...')
        self.cmo_waterfalls = self._calc_seq_bond_cfs_directed_cash

        print('Merging waterfalls...')
        self.waterfall = self.collateral_waterfall.merge(self.cmo_waterfalls, left_index=True, right_index=True)

        print('Done...')

    @property
    def update_collateral_waterfall(self) -> str:
        print('Creating collateral waterfall...')
        self.collateral_waterfall = self._create_collateral_waterfall

        print('Producing CMO waterfall...')
        self.cmo_waterfalls = self._calc_seq_bond_cfs_directed_cash

        print('Merging waterfalls...')
        self.waterfall = self.collateral_waterfall.merge(self.cmo_waterfalls, left_index=True, right_index=True)

        return 'Finished updating waterfalls...'

    @property
    def update_cmo_waterfalls(self) -> str:
        print('Producing CMO waterfall...')
        self.cmo_waterfalls = self._calc_seq_bond_cfs_directed_cash

        print('Merging waterfalls...')
        self.waterfall = self.collateral_waterfall.merge(self.cmo_waterfalls, left_index=True, right_index=True)

        return 'Finished updating waterfall...can be accessed through the instance cmo_waterfalls object'

    @property
    def _create_collateral_waterfall(self):
        """ Takes collateral summary inputs based on aggregations equaling total original balance, average pass-thru-coupon,
        weighted average coupon of underlying loans, weighted average maturity of underlying loans, psa speed multiplier
        for prepayment curve, and constant prepayment rate curve description.

        CPR description is turned into a list of CPRs which are then run through the SMM function for period SMMs."""

        cpr_curve = pc.cpr_curve_creator(self.cpr_description)
        age = self.original_maturity - self.wam

        index = pd.Index(range(1, self.wam + 1), name='month')

        beg_balance = np.zeros(self.wam)
        try:
            smm = np.array([pc.smm(cpr_curve[period - 1] * self.psa_speed[period - 1]) for period in index])
        except:
            smm = np.array([pc.smm(cpr_curve[period - 1] * self.psa_speed) for period in index])

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

            # noinspection PyTypeChecker
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
                row['servicing'] = row['beginning_balance'] * self.servicing / 12

            row['cash_flow'] = row['net_interest'] + row['total_principal'] + row['servicing']

        return waterfall

    @property
    def _calc_seq_bond_cfs_directed_cash(self) -> object:
        self._bond_waterfalls = {}
        for bond in self.bonds:
            current_bond = bond['Bond']
            self._bond_waterfalls[current_bond] = pd.DataFrame(
                index=self.collateral_waterfall.index.values,
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
            # self._bond_waterfalls[current_bond].loc[1, 'Scheduled_Payment_' + current_bond] = np.nan
            self._bond_waterfalls[current_bond]['Type_' + current_bond] = _bond_type(bond)

        final_df = pd.DataFrame(index=self.collateral_waterfall.index, columns=['remaining_interest',
                                                                                'remaining_principal'])

        # for k, v in collateral_waterfall.iterrows():
        for period in self.collateral_waterfall.index.values:

            self._rem_interest_cash = np.float(self.collateral_waterfall.loc[period, 'net_interest'])
            self._rem_principal_cash = np.float(self.collateral_waterfall.loc[period, 'total_principal'])

            # set new period balances

            for i in range(len(self.bonds)):
                current_bond = self.bonds[i]['Bond']
                if period > 1:
                    new_balance = self._calc_period_beginning_balance(current_bond, period)
                    self._bond_waterfalls[current_bond].loc[period, 'Balance_' + current_bond] = new_balance

                else:
                    new_balance = self.bonds[i]['Balance']

            self._non_accrual_principal = self._calc_non_accrual_principal_balances(period)

            # pay interest

            for i in range(len(self.bonds)):
                current_bond = self.bonds[i]['Bond']
                coupon = self._bond_waterfalls[current_bond].loc[period, 'Coupon_' + current_bond]
                is_accrual = _bond_type(self.bonds[i]) == 'accrual'

                # calculate interest due and paid

                interest_due, interest_paid = self._calc_interest_payment(period,
                                                                          self._bond_waterfalls[current_bond].loc[
                                                                              period, 'Balance_' + current_bond],
                                                                          coupon,
                                                                          is_accrual)

                unpaid_interest = interest_paid - interest_due

                self._bond_waterfalls[current_bond].loc[period, 'Interest_Due_' + current_bond] = interest_due
                self._bond_waterfalls[current_bond].loc[period, 'Interest_Paid_' + current_bond] = interest_paid

                self._bond_waterfalls[current_bond].loc[period, 'Principal_' + current_bond] = unpaid_interest

                self._bond_waterfalls[current_bond].loc[period, 'Cashflow_' + current_bond] = interest_paid + \
                                                                                              unpaid_interest

                # not using...calculate period scheduled payment

                # scheduled_payment = round(-np.pmt(coupon / 12, 361 - period, new_balance), 2)

                # self._bond_waterfalls[current_bond].loc[period, 'Scheduled_Payment_' + current_bond] = scheduled_payment

            # pay principal

            for i in range(len(self.bonds)):
                current_bond = self.bonds[i]['Bond']
                if self._rem_principal_cash > 0:
                    principal_cash_flow = min(
                        np.float(self._bond_waterfalls[current_bond].loc[period, 'Balance_' + current_bond]),
                        np.float(self._rem_principal_cash))

                    self._bond_waterfalls[current_bond].loc[period, 'Principal_' + current_bond] += principal_cash_flow
                    self._bond_waterfalls[current_bond].loc[period, 'Cashflow_' + current_bond] += principal_cash_flow
                    self._rem_principal_cash -= principal_cash_flow

                else:
                    self._bond_waterfalls[current_bond].loc[period, 'Principal_' + current_bond] += 0

            final_df.loc[period, 'remaining_principal'] = self._rem_principal_cash
            final_df.loc[period, 'remaining_interest'] = self._rem_interest_cash

        for i in range(len(self.bonds)):
            current_bond = self.bonds[i]['Bond']
            final_df = final_df.merge(self._bond_waterfalls[current_bond],
                                      left_index=True,
                                      right_index=True)

        return final_df

    def _calc_non_accrual_principal_balances(self, period):
        """

        :param bond_waterfall_df: dataframe for bond waterfalls
        :return: outstanding balances of non_accrual bonds
        """

        non_accrual_principal_balances = 0

        for bond in self.bonds:
            current_bond = bond['Bond']

            if _bond_type(bond) != 'accrual':
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

        # interest_due = bond_df.loc[prior_period, 'Interest_Due_' + current_bond]
        # interest_paid = bond_df.loc[prior_period, 'Interest_Paid_' + current_bond]

        # interest_due_unpaid = interest_due - interest_paid
        principal_paid = bond_df.loc[prior_period, 'Principal_' + current_bond]

        return starting_balance - principal_paid

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
            non_accrual_rem_principal = max(self._non_accrual_principal - self._rem_principal_cash, 0)

            # redirect necessary amount of cash to pay down as much non-accrual principal as possible
            interest_cash_redirected_to_principal = min(interest_due,
                                                        non_accrual_rem_principal)

            # interest paid to accrual bond is the remaining balance after paying down non-accrual bond principal to 0
            interest_paid = interest_due - interest_cash_redirected_to_principal

        # remaining interest cash is reduced by the interest paid out
        self._rem_interest_cash -= (interest_paid + interest_cash_redirected_to_principal)
        self._rem_principal_cash += interest_cash_redirected_to_principal

        return interest_due, interest_paid

    def create_pro_rata_bonds(self, bonds):

        pro_rata_bonds = {}
        current_bond = None

        for split in bonds:
            current_bond = split['source_bond']
            for child_bond in split['child_bonds']:
                pro_rata_bonds[child_bond] = self._bond_waterfalls[current_bond].copy()
                pro_rata_bonds[child_bond].columns = pro_rata_bonds[child_bond].columns.str.replace('_' + current_bond,
                                                                                                    '_' + child_bond)
                pro_rata_bonds[child_bond].loc[:, ['Balance_' + child_bond,
                                                   'Principal_' + child_bond,
                                                   'Interest_Due_' + child_bond,
                                                   'Interest_Paid_' + child_bond,
                                                   'Cashflow_' + child_bond]] = \
                    pro_rata_bonds[child_bond].loc[:, ['Balance_' + child_bond,
                                                       'Principal_' + child_bond,
                                                       'Interest_Due_' + child_bond,
                                                       'Interest_Paid_' + child_bond,
                                                       'Cashflow_' + child_bond]].applymap(
                        lambda x: x * split['child_bonds'][child_bond])

                self.waterfall = self.waterfall.merge(pro_rata_bonds[child_bond], left_index=True, right_index=True)

        for key in pro_rata_bonds.keys():
            self._bond_waterfalls[key] = pro_rata_bonds[key]

        self.waterfall.drop(self.waterfall.columns[self.waterfall.columns.str.contains('_' + current_bond + '$')],
                            axis=1,
                            inplace=True)

    def calc_PAC_and_support(self, collateral_waterfall, lower_band=1, upper_band=3):

        """

        :param collateral_waterfall: actual waterfall for underlying collateral
        :param lower_band: psa speed for determining lower_band payment schedule
        :param upper_band: psa speed for determining upper_band payment schedule
        :return: dataframe containing waterfall for PAC and Support bonds
        """

        # create collateral waterfall at psa speed for the lower band

        lower_df = self._create_collateral_waterfall

        # create collateral waterfall at psa speed for the higher band

        upper_df = self._create_collateral_waterfall

        # copy principal paydown schedules for the two bands to a new dataframe we will work in

        pac_df = pd.DataFrame(data=[lower_df.total_principal.values,
                                    upper_df.total_principal.values],
                              ).T
        pac_df.columns = ['PAC_lower_' + str(int(lower_band * 100)), 'PAC_upper_' + str(int(upper_band * 100))]
        pac_df.index = collateral_waterfall.index

        # PAC bond principal due is the minimum of the scheduled principal payment from the lower and upper band

        pac_df['PAC_principal_due'] = pac_df.apply(
            min, axis=1)

        # Principal available to pay down PAC and Support bond is the total principal from the collateral

        pac_df['available_principal'] = collateral_waterfall.total_principal

        # PAC initial principal size is the sum of all the scheduled principal payments for the bond

        pac_initial_balance = pac_df.PAC_principal_due.sum()
        pac_new_balance = pac_initial_balance

        # Support bond initial principal size is the balance remaining from the underlying collateral and the PAC bond

        support_initial_balance = collateral_waterfall.loc[1, 'beginning_balance'] - pac_initial_balance
        support_new_balance = support_initial_balance

        pac_df.loc[1, 'PAC_balance'] = pac_initial_balance
        pac_df.loc[1, 'Support_balance'] = support_initial_balance

        pac_df['PAC_unpaid_principal'] = 0
        pac_df['PAC_principal_paid'] = 0
        pac_df['Support_principal_paid'] = 0

        for period, values in pac_df.loc[1:].iterrows():

            # iterate through periods and determine values for each row

            pac_accrued_unpaid = 0

            if period > 1:
                pac_accrued_unpaid = pac_df.loc[period - 1, 'PAC_unpaid_principal']

                # updated balances are the prior period balance less any principal payments during that period

                pac_new_balance = pac_df.loc[period - 1, 'PAC_balance'] - pac_df.loc[period - 1, 'PAC_principal_paid']
                support_new_balance = pac_df.loc[period - 1, 'Support_balance'] - pac_df.loc[
                    period - 1, 'Support_principal_paid']

                pac_df.loc[period, 'PAC_balance'] = pac_new_balance
                pac_df.loc[period, 'Support_balance'] = support_new_balance

            # current period PAC principal due is the scheduled principal for the period + any accrued unpaid principal
            # if there wasn't enough principal cash flow in earlier periods to cover the scheduled PAC principal payment

            pac_principal_due = values['PAC_principal_due'] + pac_accrued_unpaid
            principal_available = values['available_principal']

            # PAC principal payment is the min. of PAC principal due including accrued or available principal from
            # collateral, since we can not pay more principal than available from the collateral

            pac_principal_paid = min(pac_principal_due, principal_available)

            # Support bond receives remaining principal after necessary PAC payment is met

            support_principal_paid = max(min(support_new_balance, principal_available - pac_principal_paid), 0)

            pac_principal_paid += (principal_available - pac_principal_paid - support_principal_paid)

            unpaid_principal = max(pac_df.loc[:period, 'PAC_principal_due'].sum() -
                                   (pac_df.loc[:period, 'PAC_principal_paid'].sum() + pac_principal_paid), 0)

            pac_df.loc[period, ['PAC_principal_paid',
                                'PAC_unpaid_principal',
                                'Support_principal_paid']] = [pac_principal_paid,
                                                              unpaid_principal,
                                                              support_principal_paid]

        return pac_df

    @staticmethod
    def return_PAC_Support_avg_life(waterfall):
        """

        :param waterfall: dataframe containing waterfalls for PAC and Support bonds
        :return: [weighted average life PAC bond, weighted average life Support bond]
        """

        pac = (waterfall.index.values * waterfall.PAC_principal_paid).sum() / (waterfall.PAC_principal_paid.sum()) / 12

        support = (waterfall.index.values * waterfall.Support_principal_paid).sum() / (
            waterfall.Support_principal_paid.sum()) / 12

        return [pac, support]


def _bond_type(bond: dict) -> object:
    try:
        return bond['Type']
    except KeyError:
        return None


if __name__ == '__main__':
    initial_balance = 100e6  # 100 million
    net_cpn = 0.10  # 10%
    gross_cpn = 0.1065  # 10.65%
    maturity = 360  # 30 years => monthly
    servicing_fee = 0.0025  # servicing = 25bps

    bonds_no_zbond = [
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
                 pass_thru_cpn=net_cpn,
                 wac=gross_cpn,
                 wam=maturity,
                 psa_speed=1.75,
                 servicing=servicing_fee,
                 bonds=bonds_with_zbond)

    struct.waterfall.to_clipboard()
