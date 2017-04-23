from PoolCohorts import pool


def calc_po_and_io(df=pool, base_servicing=0.0025, trustee_fee=0.00009, security_coupon=0.0575, print_summary=False):
    df['net_note_rate'] = pool.Note_Rate - base_servicing - trustee_fee
    df['diff_nn_cpn'] = pool.net_note_rate - security_coupon
    df['net_contr_to_WAC'] = [max(0, diff) for diff in pool.diff_nn_cpn]
    df['po_percent'] = [max(0.0, (security_coupon - rate) / security_coupon) for rate in pool.net_note_rate]
    df['po_balance'] = pool.po_percent * pool.Balance
    df['io_face'] = pool.Balance[pool.diff_nn_cpn > 0]
    df.fillna(0, inplace=True)

    if print_summary:
        print("""
            Total Pool: ${0:,.0f}
            PO balance: ${1:,.0f}
            IO face:    ${2:,.0f}""".format(pool.Balance.sum(), pool.po_balance.sum(), pool.io_face.sum()))

    return df


if __name__ == "__main__":
    calc_po_and_io(print_summary=True)
