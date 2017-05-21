""" General functions """


def bey_from_mey(mey):
    bey = 2 * ((1 + mey / 12) ** 6 - 1)


def macauley_duration(price, times, cash_flows, yld):
    return (1 / price) * ((times * cash_flows) /
                        (1 + yld/2)**(2*times)).sum()


def modified_duration(duration, yld):
    return duration / (1 + yld/2)


def effective_duration(price, delta_down_price, delta_up_price, yld_delta):
    return (-100/price) * ((delta_down_price - delta_up_price) / (2 * yld_delta))

def age_perc(age, e=30):
    return min(age/e, 1)

def burn_perc(factor, f=0.7):
    return 1 - f * (1 - factor)