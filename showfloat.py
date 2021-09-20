import argparse
import bigfloat
import collections

# Assumed to follow the same basic pattern as IEEE 754 / IEC 60559, except that
# the mantissa might store its leading bit explicitly, because Intel.
FloatFormat = collections.namedtuple("FloatFormat",
    ["expBits", "mantBits", "explicitLeadingBit"])

BINARY32 = FloatFormat( 8, 23, False)
BINARY64 = FloatFormat(11, 52, False)
INTEL80  = FloatFormat(15, 64, True)

def main():
    with mkContext(BINARY32):
        value = bigfloat.BigFloat.fromhex("-0x1.55554p-126")
        s, e, m = splitSEM(value, BINARY32)
        print "{:01b} {:08b} {:023b}".format(s, e, m)

    # TODO actual impl
    pass

def selfTest():
    assert mkContext(BINARY32) == bigfloat.single_precision
    assert mkContext(BINARY64) == bigfloat.double_precision



def splitSEM(value, fltFormat):
    # TODO:
    #with mkContext(fltFormat):
    # Or maybe all this in the wider-ranged context used below for scaling
    # mant? (Also, TODO does that context need to decrease emin as well?)
    bias = getBias(fltFormat)

    signBit = 1 if bigfloat.copysign(1, value) < 0 else 0
    value = bigfloat.abs(value)

    expo = bigfloat.floor(bigfloat.log2(value))
    #print("value = {}".format(value))
    #print("bigfloat.log2(value) = {}".format(bigfloat.log2(value)))
    biasedExpo = int(expo + bias)
    if biasedExpo < 1:
        # Subnormal. The value stored is one less than for FLT_MIN, but the
        # represented exponent is the same; the values are continuous because
        # the leading bit changes to 0 across this threshold.
        biasedExpo = 0
        expo = 1 - bias

    usefulMantBits = fltFormat.mantBits
    if fltFormat.explicitLeadingBit:
        usefulMantBits -= 1
    # The mantissa as it's stored (an integer value).
    with bigfloat.Context(emax=bigfloat.getcontext().emax + usefulMantBits):
        mant = value * bigfloat.pow(2, usefulMantBits - expo)
    #print("value = {}, 2**(mantBits-expo) = {}".format(value, bigfloat.pow(2, usefulMantBits - expo)))
    #print("mant = {}".format(mant))
    assert mant == int(mant)
    mant = int(mant)
    # TODO: Maybe ignore explicitLeadingBit here and push that oddity onto the
    # printing code? And make FloatFormat.mantBits actually be usefulMantBits,
    # so it's 63 for INTEL80.
    if biasedExpo > 0 and not fltFormat.explicitLeadingBit:
        # The leading bit is implicitly 1 but not stored in the representation;
        # clear it for the sake of reporting the mantissa.
        mant -= 2**fltFormat.mantBits
        assert 0 <= mant < 2**fltFormat.mantBits
    elif biasedExpo > 0:
        assert 2**fltFormat.mantBits <= mant < 2 * 2**fltFormat.mantBits
    else:
        assert 0 <= mant < 2**fltFormat.mantBits

    return (signBit, biasedExpo, mant)

def mkContext(fltFormat):
    precision = fltFormat.mantBits
    if not fltFormat.explicitLeadingBit:
        # bigfloat precision counts the leading bit, whether stored or not
        precision += 1
    bias = getBias(fltFormat)
    # These are the min and max exponent as I think about them, though it
    # doesn't match bigfloat's emin/emax or C's FLT_MIN_EXP/FLT_MAX_EXP. Take
    # the lowest and highest values that would be stored in the exponent field
    # (1 and 2**expBits - 2, since 0 is subnormal and 2**expBits-1 is inf/nan)
    # and subtract the bias.
    expOfFltMin = 1 - bias
    expOfFltMax = (2**fltFormat.expBits - 2) - bias
    # bigfloat normalizes floats as [0.5..1.0) * 2**exponent, whereas IEEE
    # representations are [1.0..2.0) * 2**exponent. So emax for bigfloat is one
    # greater than the max as it would be represented in an IEEE format.
    emax = expOfFltMax + 1
    # For emin, the same applies, but bigfloat's emin also takes into account
    # subnormals: emin is the value such that 0.5 * 2 ** emin is the smallest
    # subnormal. So add 1 for differing normalizations and subtract mantBits
    # for subnormals.
    emin = expOfFltMin + 1 - fltFormat.mantBits
    return bigfloat.Context(precision=precision, emin=emin, emax=emax,
        subnormalize=True)

def getBias(fltFormat):
    return 2**(fltFormat.expBits - 1) - 1


if __name__ == "__main__":
    selfTest()
    main()

