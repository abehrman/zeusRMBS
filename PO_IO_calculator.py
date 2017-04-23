from PoolCohorts import pool

base_servicing = 0.0025  # 25 bps
trustee_fee = 0.00009  # .9 basis points
security_coupon = 5.75 / 100  # 5.75%

pool['net_note_rate'] = pool.Note_Rate - base_servicing - trustee_fee
pool['diff_nn_cpn'] = pool.net_note_rate - security_coupon
pool['net_contr_to_WAC'] = [max(0, diff) for diff in pool.diff_nn_cpn]
pool['po_percent'] = [max(0.0, (security_coupon - rate) / security_coupon) for rate in pool.net_note_rate]
pool['po_balance'] = pool.po_percent * pool.Balance
pool['io_face'] = pool.Balance[pool.diff_nn_cpn > 0]
pool.fillna(0, inplace=True)

print("""
Total Pool: ${0:,.0f}
PO balance: ${1:,.0f}
IO face:    ${2:,.0f}""".format(pool.Balance.sum(), pool.po_balance.sum(), pool.io_face.sum()))
