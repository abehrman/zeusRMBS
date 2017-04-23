import numpy as np
import pandas as pd

PoolAmounts = np.array([
    5e5,
    2.6e6,
    5e6,
    8e6,
    16.4e6,
    21e6,
    31e6,
    37e6,
    45e6,
    55e6,
    70e6,
    41e6,
    42e6,
    37e6,
    30.5e6,
    22e6,
    21e6,
    8e6,
    4e6,
    3e6
])

NoteRates = np.array([
    5,
    5.125,
    5.25,
    5.375,
    5.5,
    5.625,
    5.75,
    5.875,
    6,
    6.125,
    6.25,
    6.375,
    6.5,
    6.625,
    6.75,
    6.875,
    7,
    7.125,
    7.25,
    7.375
]) / 100

pool = pd.DataFrame([PoolAmounts, NoteRates]).T
pool.columns = ['Balance', 'Note_Rate']