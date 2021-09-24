#import argparse
import bigfloat
import math

def main():
    with mkContext(BINARY32):
        value = bigfloat.BigFloat.fromhex("-0x1.55554p-126")
        s, e, m = splitSEM(value, BINARY32)
        print "{:01b} {:08b} {:023b}".format(s, e, m)

        print("")
        showFloat(value, (s, e, m), BINARY32)

        print("")
        showFloat(value, (s, e, m), BINARY32, exactDecimal=True)

        print("")
        value = bigfloat.BigFloat.fromhex("0x1p-125")
        s, e, m = splitSEM(value, BINARY32)
        showFloat(value, (s, e, m), BINARY32)

        print("")
        value = bigfloat.BigFloat.fromhex("0x1.fffffep-126")
        s, e, m = splitSEM(value, BINARY32)
        showFloat(value, (s, e, m), BINARY32)

        print("")
        value = bigfloat.BigFloat.fromhex("0x1p-126")
        s, e, m = splitSEM(value, BINARY32)
        showFloat(value, (s, e, m), BINARY32)

        print("")
        value = bigfloat.BigFloat.fromhex("0x0.fffffep-126")
        s, e, m = splitSEM(value, BINARY32)
        showFloat(value, (s, e, m), BINARY32)

        print("")
        value = bigfloat.BigFloat.fromhex("0x1p-149")
        s, e, m = splitSEM(value, BINARY32)
        showFloat(value, (s, e, m), BINARY32)

    # TODO actual impl
    pass

def selfTest():
    assert mkContext(BINARY32)  == bigfloat.single_precision
    assert mkContext(BINARY64)  == bigfloat.double_precision
    assert mkContext(HALF_PREC) == bigfloat.half_precision


# FIXME: This and some helpers need to be wrapped in:
#     with mkContext(fltFormat):
# or possibly a context with wider range but the same precision, to simplify
# some calculations that might cross over FLT_MAX and then back? Might cause
# problems on the subnormal end, though. Maybe better to only increase the
# range for individual calculations where I know it's needed.

def showFloat(value, sem, fltFormat, exactDecimal=False):
    """
    Example format (tentative):

    Dec (approx): 1.234
    Hex (%a):     0x1.234p+0
    10exp2:       1234 * 2**-12
    ULP:          2 ** -12
    FP_CLASSIFY:  FP_NORMAL
    Bits (hex):   0x3fe12300
    Bits (bin):   0 01111111 00010010001101000000000
    """

    # TODO apply this context
    context = mkContext(fltFormat)

    # TODO add some self-checks to these:
    #   - decimal repr, evaluated in original context (round to nearest) should
    #     parse back to exact same val (unless NaN)
    #   - hex val ditto, but also in a context with greater precision and/or
    #     range
    #   - 10exp2, evaluated to greater range and equal or greater precision,
    #     should produce same value. (Needs greater range b/c of the exp2.)
    #       - Actually, scratch that. On the small end, the power mins out at
    #         min subnorm. On the large end, it's a modest integer times a
    #         power of 2 that's less than the final value. This should work
    #         with no additional range.
    #   - If finite, then min(nextUp - x, x - nextDown) should be the ulp,
    #     right? (Though I might just end up calculating it that way...)

    # Decimal value
    if exactDecimal:
        # I think a longest exact base-10 representation for a floating-point
        # format is:
        #     nextDown(2*FLT_MIN)
        #   = 2*FLT_MIN - MIN_FLT_SUBNORM
        #   = (2**(1 + usefulMantBits) - 1) * 2**log2OfMinSubnorm
        # whose decimal digits are the same as:
        #     (2**(1 + usefulMantBits) - 1) * 5**-log2OfMinSubnorm
        # In case I'm wrong, format it with twice that many digits and then
        # assert that the number of sig figs is within my bound.
        mostDigits = len(str((2**(1 + fltFormat.usefulMantBits) - 1) *
            5**-fltFormat.log2OfMinSubnorm))

        # Use %g mostly because it omits extra trailing zeros after the decimal
        # point, and that's what I want. (Since I'm using such a large
        # precision, simple values would look completely nuts otherwise.) The
        # heuristic %g uses for fixed vs. exponential notation is reasonable;
        # I might prefer exponential for large-magnitude values over a few tens
        # of digits (say 1e+100), but I don't care enough to implement
        # something myself.
        exactString = "{val:.{prec}g}".format(val=value, prec=2*mostDigits)

        # Check bound
        sigFigs = exactString.partition("e")[0]
        numSigFigs = len(sigFigs)
        if "." in sigFigs:
            numSigFigs -= 1
        assert numSigFigs <= mostDigits

        # Actually print it
        print("Dec (exact):  {}".format(exactString))
    else:
        # The C standard says that this is the number of base-10 digits
        # required to serialize all floating-point values of a given precision
        # to decimal and recover the original values unambiguously. I don't
        # have the background to prove this myself, but I'll trust the standard
        # committee.
        prec = int(math.ceil(1 +
            (1 + fltFormat.usefulMantBits)*math.log(2, 10)))
        print("Dec (approx): {val:.{prec}g}".format(val=value, prec=prec))

    # TODO skip this next part for inf/nan. Actually, maybe just special case
    # the non-bits parts for inf/nan at a higher level? May want to put the
    # parts in separate functions anyway just to save on indents once I add a
    # 'with context'.
    #   - Also, I might have to fabricate a canonical repr for NaNs.

    # Split abs(value) into (integer) mantissa times a power of 2. These are
    # the values used in 10exp2, but are also useful for hex (%a) and ULP.
    #
    # TODO: Refactor this, splitSEM, and the eventual packSEM. Maybe have a
    # class for like "analyzed value" where you can query details of both value
    # and representation? Things like stored exp, biased exp, stored mant,
    # represented mant (with leading bit regardless of format), but also value
    # and... uh. Okay, maybe the details are all of the bits/repr?
    sgn, storedExpo, storedMant = sem
    expo = storedExpo - fltFormat.bias
    if storedExpo == 0:
        expo = 1 - fltFormat.bias
    mant = storedMant
    if storedExpo > 0 and not fltFormat.explicitLeadingBit:
        mant += 2**fltFormat.mantBits
    expoForIntMant = expo - fltFormat.usefulMantBits

    # Hex (C-style "%a")
    # BigFloat's docs doesn't seem to specify how .hex() or "%a" normalizes,
    # and empirically they are different from each other and _neither_
    # normalizes the way I want! Okay, fine, I'll do it myself.

    # Enough hex digs for a leading 1 (which wastes 3 bits) and then the rest
    # of the mantissa.
    numHexDigs = ceildiv(fltFormat.totalMantBits + 3, 4)
    mantShift = (1 + 4*(numHexDigs - 1)) - fltFormat.totalMantBits
    assert 0 <= mantShift < 4
    shiftedMant = mant << mantShift
    rawHexDigs = "{digs:0{count}x}".format(digs=shiftedMant, count=numHexDigs)
    assert len(rawHexDigs) == numHexDigs
    if storedExpo > 0:
        assert rawHexDigs[0] == '1'
    # Trim 0s from the right. Python's <float>.hex() and BigFloat.hex() don't
    # do this, but at least some libc implementations do.
    while len(rawHexDigs) > 1 and rawHexDigs[-1] == '0':
        rawHexDigs = rawHexDigs[:-1]
    hexStr = ""
    if sgn:
        hexStr += '-'
    hexStr += "0x"
    hexStr += rawHexDigs[0]
    if len(rawHexDigs) > 1:
        hexStr += "."
        hexStr += rawHexDigs[1:]
    hexStr += 'p'
    if bigfloat.is_zero(value):
        # Special case: display 0 as "0x0p+0", not "0x0p-126". The latter is
        # more faithful to the representation, but the former is more friendly
        # to the user and is what %a actually does (at least the implementation
        # I know; I forget if it's required).
        hexStr += "+0"
    else:
        hexStr += "{:+d}".format(expo)
    print("Hex (%a):     {}".format(hexStr))

    # 10exp2
    print("10exp2:       {mant:d} * 2**{expo:d}" \
        .format(mant=mant, expo=expoForIntMant))

    # ULP. I guess I could skip this if I always use this as the exp2 in
    # 10exp2, but no one but me is gonna see the 10exp2 and just know "oh, that
    # power of 2 is the ULP".
    # TODO: Maybe add some explanatory text at the end and have one line?
    #     10exp2:       1234 * 2**-12  (exp2 is the ulp)
    #     10exp2:       1234 * 2**-12  (ULP = 2**-12)
    #     int10 * ULP:  1234 * 2**-12
    # Hah. That last one is kind of clever. If I'm inventing the name anyway, I
    # may as well invent a name that explains the less-obvious but useful
    # property, rather than just the basic "integer times some power of 2, but
    # who knows which one". Note in this case, 0 has to be 0 * 2**-149; I can't
    # simplify it.
    print("ULP:          2**{expo:d}" \
        .format(expo=expoForIntMant))

    # TODO unnormals / pseudo-denormals for explicitLeadingBit.
    fpcls = "** ERROR **"
    if bigfloat.is_nan(value):
        fpcls = "FP_NAN"
    elif bigfloat.is_inf(value):
        fpcls = "FP_INFINITE"
    elif bigfloat.is_zero(value):
        fpcls = "FP_ZERO"
    elif storedExpo == 0:
        fpcls = "FP_SUBNORMAL"
    else:
        fpcls = "FP_NORMAL"
    print("fpclassify:   {}".format(fpcls))

    allBits = sgn
    allBits <<= fltFormat.expBits
    allBits |= storedExpo
    allBits <<= fltFormat.mantBits
    allBits |= storedMant
    numDigs = ceildiv(1 + fltFormat.expBits + fltFormat.mantBits, 4)
    print("Bits (hex):   0x{val:0{count}x}".format(val=allBits, count=numDigs))

    print("Bits (bin):   {sgn:01b} {expo:0{expoLen}b} {mant:0{mantLen}b}" \
        .format(sgn = sgn,
                expo = storedExpo,
                expoLen = fltFormat.expBits,
                mant = storedMant,
                mantLen = fltFormat.mantBits))


def ceildiv(x, y):
    return (x + y - 1) // y

def splitSEM(value, fltFormat):

    signBit = 1 if bigfloat.copysign(1, value) < 0 else 0
    value = bigfloat.abs(value)

    # FIXME! log2(value) might round UP to an integer! This actually happens
    # for max subnorm in single precision. Per Python's math.log (double
    # precision):
    #     log2(0x0.fffffep-126) = -0x1.f800000b8aa3cp+6
    # which is a couple hex digits off from being representably less than
    # -0x1.f8p+6 (aka -126).
    #
    # HACK! Double the precision and hope this is enough.
    # TODO: Figure out how much we actually need to guarantee this in general
    # (or find a different method than log2... surely there is some more direct
    # way to query this?... or else maybe just try scaling it by the exp we
    # compute and check if it's off by 1 :thinking:).
    with bigfloat.extra_precision(bigfloat.getcontext().precision):
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

        # TODO shorter name?
        # Or make it 3 values: storedMantBits, totalMantBits, trailingMantBits,
        # so I'm forced to actually specify each time?
        self.usefulMantBits = mantBits
        if explicitLeadingBit:
            self.usefulMantBits -= 1

    @property
    def bias(self):
        return 2**(self.expBits - 1) - 1

    @property
    def totalMantBits(self):
        return self.usefulMantBits + 1

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

BINARY32  = FloatFormat( 8, 23, False)
BINARY64  = FloatFormat(11, 52, False)
INTEL80   = FloatFormat(15, 64, True)
HALF_PREC = FloatFormat( 5, 10, False)


if __name__ == "__main__":
    selfTest()
    main()

