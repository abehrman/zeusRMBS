""" General functions """


def bey_from_mey(mey):
    """

    :param mey: monthly bond yield
    :return: bond equivalent yield
    """

    bey = 2 * ((1 + mey / 12) ** 6 - 1)


def macauley_duration(price, times, cash_flows, yld):
    return (1 / price) * ((times * cash_flows) /
                        (1 + yld/2)**(2*times)).sum()


def modified_duration(duration, yld):
    return duration / (1 + yld/2)


def effective_duration(price, delta_down_price, delta_up_price, yld_delta):
    return (-100/price) * ((delta_down_price - delta_up_price) / (2 * yld_delta))


def floater_rates(floater_size=.75,
                  inverse_size=.25,
                  available_coupon=0.09,
                  margin=0.01,
                  rate=0.):

    """

    :param floater_size: size of floater bond principal
    :param inverse_size: size of inverse floater bond principal
    :param available_coupon: coupon available from underlying collateral
    :param margin: floater margin to index rate, usually LIBOR or CMT
    :param rate: rate of LIBOR or CMT to evaluate payment levels
    :return: coupon payment levels for 'floater', and 'inverse floater'
    """

    leverage = floater_size / inverse_size
    floater_rate = min(rate + margin, available_coupon + (1 / leverage * available_coupon))

    inverse_rate = max((available_coupon + leverage * (available_coupon - floater_rate)), 0)

    return floater_rate, inverse_rate