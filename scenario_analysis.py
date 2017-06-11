""" Functions for evaluating scenario environments """

import numpy as np
import pandas as pd

def calc_reinvestments(interest_flows,
                       principal_flows,
                       reinvestment_rate,
                       periods=None):

    if periods is None:
        periods = np.arange(0,len(interest_flows))

    first_period = np.min(periods)
    last_period = np.max(periods)

    returns = (1 + reinvestment_rate) ** \
              (last_period - periods)

    interest_returns = interest_flows[first_period:last_period + 1] * returns
    principal_returns = principal_flows[first_period:last_period + 1] * returns

    return returns, interest_returns, principal_returns
