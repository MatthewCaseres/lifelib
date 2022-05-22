"""The main Space in the :mod:`~assets.BasicBonds` model.



.. rubric:: Parameters and References

(In all the sample code below,
the global variable ``Bonds`` refers to the
:mod:`~assets.BasicBonds.Bonds` space.)

Attributes:

    ql: The `QuantLib <https://www.quantlib.org/>`_ module.

    date_init: Valuation date as a string in the form of 'YYYY-MM-DD'.


    date_end: Projection end date as a string in the form of 'YYYY-MM-DD'.

    zero_curve: Zero curve at the valuation date as a pandas Series
        indexed with strings indicating various durations.
        This data is used by :func:`riskfree_curve` to create
        QuantLib's ZeroCurve object::

            >>> Bonds.zero_curve

            Duration
            1M     0.0004
            2M     0.0015
            3M     0.0026
            6M     0.0057
            1Y     0.0091
            2Y     0.0136
            3Y     0.0161
            5Y     0.0182
            7Y     0.0192
            10Y    0.0194
            20Y    0.0231
            30Y    0.0225
            Name: Rate, dtype: float64

    bond_data: Bond data as a pandas DataFrame.
        By default, a sample table generated by the
        *generate_bond_data.ipynb* notebook included in the library::

            >>> Bonds.bond_data

                     settlement_days  face_value issue_date  ...  tenor coupon_rate z_spread
            bond_id                                          ...
            1                      0      235000 2017-12-12  ...     1Y        0.07   0.0304
            2                      0      324000 2021-11-29  ...     1Y        0.08   0.0304
            3                      0      799000 2017-02-03  ...     6M        0.03   0.0155
            4                      0      679000 2017-11-19  ...     1Y        0.08   0.0229
            5                      0      397000 2018-07-01  ...     6M        0.06   0.0142
                             ...         ...        ...  ...    ...         ...      ...
            996                    0      560000 2019-02-16  ...     1Y        0.06   0.0261
            997                    0      161000 2020-03-12  ...     6M        0.05   0.0199
            998                    0      375000 2019-05-05  ...     1Y        0.03   0.0138
            999                    0      498000 2019-02-21  ...     1Y        0.03   0.0230
            1000                   0      438000 2019-03-14  ...     1Y        0.06   0.0256

            [1000 rows x 8 columns]

        The column names and their data types are as follows::

            >>> Bonds.bond_data.dtypes

            settlement_days             int64
            face_value                  int64
            issue_date         datetime64[ns]
            bond_term                   int64
            maturity_date      datetime64[ns]
            tenor                      object
            coupon_rate               float64
            z_spread                  float64
            dtype: object

"""

from modelx.serialize.jsonvalues import *

_formula = None

_bases = []

_allow_none = None

_spaces = []

# ---------------------------------------------------------------------------
# Cells

def cashflows(bond_id):
    """
    The cashflows cells returns a vector of the cashflows of the selected bond. The cashflows falling in each projection period defined by dates are aggregated.
    """

    result = [0] * t_length()
    leg = fixed_rate_bond(bond_id).cashflows()
    i = 0   # cashflow index

    for t in range(t_length()):

        while i < len(leg):

            if i > 0:
                # Check if cashflow dates are in order.
                assert leg[i-1].date() <= leg[i].date()

            if dates(t) <= leg[i].date() < dates(t+1):
                result[t] += leg[i].amount()

            elif dates(t+1) <= leg[i].date():
                break

            i += 1


    return result


def cashflows_total():
    """
    returns a vector of the aggregated cashflows of the entire bond portfolio.
    """

    result = [0] * t_length()
    for t in range(t_length()):
        for i in bond_data.index:
            result[t] += cashflows(i)[t]

    return result


def dates(t):
    """Defines projection steps
     by returning points in time as QuantLib’s Date objects.
     The valuation date is set to January 1, 2022. The length of a projection step is annual.
     """

    if t == 0:
        return ql.Date(date_init, "%Y-%m-%d")

    else:
        return dates(t-1) + ql.Period('1Y')


def discount_curve(bond_id):
    """
    Risk-free yield data is also read from a spreadsheet in the model and stored as a DataFrame named zero_curve.
    riskfree_curve constructs and returns a QuantLib’s ZeroCurve object.
    """

    spread = bond_data.loc[bond_id]['z_spread']
    spread  = ql.QuoteHandle(ql.SimpleQuote(spread))    

    return ql.ZeroSpreadedTermStructure(
        ql.YieldTermStructureHandle(riskfree_curve()), spread,
                                        ql.Compounded, ql.Annual)


def fixed_rate_bond(bond_id):
    """returns a QuantLib’s FixedRateBond object representing a bond specified by the given bond ID."""

    settlement_days = bond_data.loc[bond_id]['settlement_days']
    face_value = bond_data.loc[bond_id]['face_value']
    coupons = [bond_data.loc[bond_id]['coupon_rate']]


    bond = ql.FixedRateBond(
        int(settlement_days), 
        float(face_value), 
        schedule(bond_id), 
        coupons, 
        ql.Actual360(), # DayCount
        ql.Unadjusted)

    # Set discount curve
    bondEngine = ql.DiscountingBondEngine(
        ql.YieldTermStructureHandle(discount_curve(bond_id)))
    bond.setPricingEngine(bondEngine)

    return bond


def redemptions(bond_id):


    result = [0] * t_length()
    leg = fixed_rate_bond(bond_id).redemptions()
    i = 0   # cashflow index

    for t in range(t_length()):

        while i < len(leg):

            if dates(t) <= leg[i].date() < dates(t+1):
                result[t] += leg[i].amount()

            elif dates(t+1) <= leg[i].date():
                break

            i += 1


    return result


def redemptions_total():

    result = [0] * t_length()
    for t in range(t_length()):
        for i in bond_data.index:
            result[t] += redemptions(i)[t]

    return result


def riskfree_curve():
    """
    Risk-free yield data is also read from a spreadsheet in the model and stored as a DataFrame named zero_curve.
    riskfree_curve constructs and returns a QuantLib’s ZeroCurve object.
    """

    ql.Settings.instance().evaluationDate = dates(0)

    spot_dates = [dates(0)] + list(dates(0) + ql.Period(dur) for dur in zero_curve.index)
    spot_rates = [0] + list(zero_curve)

    return ql.ZeroCurve(
        spot_dates, 
        spot_rates, 
        ql.Actual360(),     # dayCount
        ql.UnitedStates(),    # calendar
        ql.Linear(),          # Interpolator
        ql.Compounded,      # compounding
        ql.Annual           # frequency
        )


def schedule(bond_id):

    d = bond_data.loc[bond_id]['issue_date']
    issue_date = ql.Date(d.day, d.month, d.year)

    d = bond_data.loc[bond_id]['maturity_date']
    maturity_date = ql.Date(d.day, d.month, d.year)

    tenor  = ql.Period(
        ql.Semiannual if bond_data.loc[bond_id]['tenor'] == '6Y' else ql.Annual)


    return ql.Schedule(
        issue_date, 
        maturity_date, 
        tenor, 
        ql.UnitedStates(),               # calendar
        ql.Unadjusted,                   # convention
        ql.Unadjusted ,                 # terminationDateConvention
        ql.DateGeneration.Backward,     # rule
        False   # endOfMonth
        )


def t_length():

    d_end = ql.Date(date_end, "%Y-%m-%d")

    t = 0
    while True:
        if dates(t) < d_end:
            t += 1
        else:
            return t


def z_spread_recalc(bond_id):
    """
    z_spread_recalc is for checking the calculation of the market value of a selected bond,
    by reproducing the z-spread from the market value and the risk free curve.
    """

    return ql.BondFunctions.zSpread(
        fixed_rate_bond(bond_id), 
        fixed_rate_bond(bond_id).cleanPrice(), 
        riskfree_curve(),
        ql.Thirty360(), ql.Compounded, ql.Annual)


def market_values():
    """
    market_values returns a list of the market values of the bonds.
    The market value of each bond is calculated using
    the cleanPrice method by discounting the cashflows of the bond by the risk-free rates plus the bond’s credit spread.
    """

    bond = fixed_rate_bond

    return list(
        bond(i).notional() * bond(i).cleanPrice() / 100 
        for i in bond_data.index)


# ---------------------------------------------------------------------------
# References

date_end = "2053-01-01"

date_init = "2022-01-01"

bond_data = ("DataSpec", 1615158375376, 1615210441168)

ql = ("Module", "QuantLib")

zero_curve = ("DataSpec", 1615238101120, 1615209110256)