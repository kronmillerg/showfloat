#import argparse
import bigfloat

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

    signBit = 1 if bigfloat.copysign(1, value) < 0 else 0
    value = bigfloat.abs(value)

    expo = bigfloat.floor(bigfloat.log2(value))
    #print("value = {}".format(value))
    #print("bigfloat.log2(value) = {}".format(bigfloat.log2(value)))
    biasedExpo = int(expo + fltFormat.bias)
    if biasedExpo < 1:
        # Subnormal. The value stored is one less than for FLT_MIN, but the
        # represented exponent is the same; the values are continuous because
        # the leading bit changes to 0 across this threshold.
        biasedExpo = 0
        expo = 1 - fltFormat.bias

    # The mantissa as it's stored (an integer value).
    with bigfloat.Context(emax=bigfloat.getcontext().emax +
            fltFormat.usefulMantBits):
        mant = value * bigfloat.pow(2, fltFormat.usefulMantBits - expo)
    #print("value = {}, 2**(mantBits-expo) = {}".format(value, bigfloat.pow(2, usefulMantBits - expo)))
    #print("mant = {}".format(mant))
    assert mant == int(mant)
    mant = int(mant)
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
    # bigfloat precision counts the leading bit, whether stored or not
    precision = fltFormat.usefulMantBits + 1
    # bigfloat normalizes floats as [0.5..1.0) * 2**exponent, whereas IEEE
    # representations are [1.0..2.0) * 2**exponent. So emax for bigfloat is one
    # greater than the max as it would be represented in an IEEE format.
    emax = fltFormat.expOfFltMax + 1
    # Likewise for emin, but bigfloat's emin also takes into account
    # subnormals: emin is the value such that 0.5 * 2 ** emin is the smallest
    # subnormal.
    emin = fltFormat.log2OfMinSubnorm + 1
    return bigfloat.Context(precision=precision, emin=emin, emax=emax,
        subnormalize=True)

class FloatFormat(object):
    """
    Class to represent a floating-point format. The format is assumed to follow
    the same basic pattern as IEEE 754 / IEC 60559, except that the mantissa
    might store its leading bit explicitly, because Intel.
    """

    def __init__(self, expBits, mantBits, explicitLeadingBit=False):
        self.expBits = expBits
        self.mantBits = mantBits
        self.explicitLeadingBit = explicitLeadingBit

        self.usefulMantBits = mantBits
        if explicitLeadingBit:
            self.usefulMantBits -= 1

    @property
    def bias(self):
        return 2**(self.expBits - 1) - 1

    @property
    def expOfFltMax(self):
        """
        Return (unbiased) exponent of FLT_MAX, using IEEE-style normalization,
        [1..2) * 2**exp.
        """
        # Biased exponent of FLT_MAX is expBits-2 (expBits-1 is inf/nan).
        return (2**self.expBits - 2) - self.bias

    @property
    def expOfFltMin(self):
        """
        Return (unbiased) exponent of FLT_MIN, using IEEE-style normalization,
        [1..2) * 2**exp.
        """
        # Biased exponent of FLT_MIN is 1 (0 is zero/subnormal).
        return 1 - self.bias

    @property
    def log2OfMinSubnorm(self):
        # FLT_MIN is 1 in the leading bit of the significand; assuming not
        # explicitLeadingBit this is the bit one place value above the stored
        # mantissa. Shifting by the number of mantissa bits (no +/- 1) puts it
        # in the bottom bit of the mantissa, with the same exponent.
        return self.expOfFltMin - self.usefulMantBits

BINARY32 = FloatFormat( 8, 23, False)
BINARY64 = FloatFormat(11, 52, False)
INTEL80  = FloatFormat(15, 64, True)


if __name__ == "__main__":
    selfTest()
    main()

