import numpy as np
import pandas as pd


class BondPricing:

    def __init__(self, bonds):
        self.bonds = bonds
        self._append_spot_rate()

    @staticmethod
    def zero_coupon_bond_price(par, ytm, time):
        """Takes par price, yield to maturity, and time to maturity
        and returns a spot price for the bond."""

        return par / (1 + ytm) ** time

    def _bond_intermediate_coupon_npv(self, coupon, frequency, periods):
        coupon_amt = coupon / frequency

        coupon_npv = 0

        for i in range(1, periods):
            # range is exclusive of the end so this will give us the first and second
            # coupons which is what we need to discount; the final coupon will be
            # evaluated with the principal payment to determine the spot rate for that
            # period.

            # determine which period we are evaluating
            period = i / frequency

            # get the spot rate for the period from dataframe
            period_spot = self.bonds.loc[self.bonds['Maturity'] ==
                                           period, 'spot_rate'].values

            discounted_value = coupon_amt / np.exp(period_spot * period)

            coupon_npv += discounted_value[0]

        return coupon_npv


    def _spot_rate(self, par, price, maturity, coupon=0, frequency=2):
        coupon_npv = 0

        if coupon != 0:
            try:
                coupon_npv = self._bond_intermediate_coupon_npv(
                    coupon,
                    frequency,
                    periods=np.int(maturity * frequency))
            except:
                coupon_npv = coupon


        # add the final coupon to final cash flow if it
        # falls on a coupon payment period

        final_flow = par + coupon / frequency if maturity % (1 / frequency) == 0 else par

        # reduce the present value cost of the bond by the present value of
        # intermediate coupon payments, if any

        final_price = price - coupon_npv

        total_interest_earned = final_flow / final_price
        spot = ((1 / maturity) * np.log(total_interest_earned))
        total_interest_earned = total_interest_earned - 1

        return spot, total_interest_earned

    def _append_spot_rate(self):
        for k, v in self.bonds.iterrows():
            self.bonds.set_value(k, 'spot_rate', self._spot_rate(v['Face'],
                                                             v['Price'],
                                                             v['Maturity'],
                                                             v['Coupon'],
                                                             v['coupon_freq'])[0])

    @staticmethod
    def spot_from_par(par_bonds):

        if par_bonds is None:
            par_bonds = pd.DataFrame([
                {'Maturity': 1., 'Yield': 7.},
                {'Maturity': 2., 'Yield': 8.},
                {'Maturity': 3., 'Yield': 9.},
                {'Maturity': 4., 'Yield': 10.},
            ])

        par_bonds.loc[0, 'spot_rate'] = bonds.loc[0, 'Yield']
        for i in np.arange(1, len(bonds)):
            result = 0
            for j in range(i):
                # print(i,j)
                print('{0:.10f} / ( 1 + {1:.10f}/100)**({2:.0f})'.format(par_bonds.loc[i, 'Yield'],
                                                                         par_bonds.loc[j, 'spot_rate'],
                                                                         j + 1))
                a = par_bonds.loc[i, 'Yield'] / (1. + par_bonds.loc[j, 'spot_rate'] / 100.) ** (j + 1.)
                result += a
            par_bonds.loc[i, 'spot_rate'] = (((100. + par_bonds.loc[i, 'Yield']) / (100. - result)) ** (
            1. / (i + 1.)) - 1.) * 100
        return par_bonds

if __name__ == "__main__":
    bonds = pd.DataFrame([
        {'Face': 100, 'Maturity': 1., 'Coupon': 0, 'Price': 100.},
        {'Face': 100, 'Maturity': 2., 'Coupon': 8, 'Price': 100.},
        {'Face': 100, 'Maturity': 3., 'Coupon': 9, 'Price': 100.},
        {'Face': 100, 'Maturity': 4., 'Coupon': 10, 'Price': 100.}
    ])

    bonds['coupon_freq'] = 1

    bonds = BondPricing(bonds).bonds