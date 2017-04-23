class collateral_single:
    def __init__(self,
                 amort_type,  # fixed or adjustable rate mortgage (ARM)
                 age,
                 origination_balance,
                 current_balance,
                 gross_rate,
                 fees,  # dictionary of fees
                 prepay_penalties,  # dictionary of prepay penalties
                 original_amort_term,
                 average_loan_size,
                 settlement_date

                 ):
        amort_types = {
            'fixed': 0,
            'ARM': 1
        }

        try:
            self.amort_type = amort_types[amort_type]
        except:
            print("invalid amort_type")
            raise ValueError

        self.age = age
        self.origination_balance = origination_balance
        self.current_balance = current_balance
        self.gross_rate = gross_rate
        self.fees = fees
        self.prepay_penalties = prepay_penalties
        self.original_amort_term = original_amort_term
        self.average_loan_size = average_loan_size
        self.settlement_date = settlement_date
