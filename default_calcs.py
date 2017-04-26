""" Functions for evaluating loan and pool defaults """
import numpy as np
import scipy.stats as stats


def hazard(beginning_balance, period_defaults):
    """Returns the % of loans that defaulted in a period based on the periods original balance"""

    return float(period_defaults) / float(beginning_balance)


def default_rate_normal_dist(x, p, pi):
    """ calculate periodic default rate where
    
    x = common risk factor
    
    p = correlation of Asset values
    
    pi = probability of default for Assets
    
    default rate = d = N[ (N.inv(pi) - x*sqrt(p)) / sqrt(1-p) ]
    
    assuming the distribution of common risk factors is normally distributed"""

    return stats.norm.cdf(
        (stats.norm.ppf(pi) - (x * np.sqrt(p))) /
        np.sqrt(1 - p))


def inv_default_rate_normal_dist(pi, p, default_rate):
    """ returns the cumulative probability function for w where
    
    1 - CDF = w = N[ (N.inv(pi) - sqrt(1-p) * N.inv(d)) / sqrt(p) ]
    
    assuming the distribution of common risk factors is normally distributed"""
    result = []
    return [stats.norm.cdf(
        (stats.norm.ppf(pi) - (np.sqrt(1 - p) * stats.norm.ppf(d))) /
        np.sqrt(p)) for d in default_rate]


def default_rate(x, p, pi, M):
    """ calculate periodic default rate where

    x = common risk factor

    p = correlation of Asset values

    pi = probability of default for Assets
    
    M = distribution of common risk factors

    default rate = d = M[ (N.inv(pi) - x*sqrt(p)) / sqrt(1-p) ]

    """

    return stats.norm.cdf(
        (M(pi) - (x * np.sqrt(p))) /
        (np.sqrt(1 - p)))
