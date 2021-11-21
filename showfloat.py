#!/usr/bin/env python

import argparse
import bigfloat
import math
import sys

def main():
    selfTest()

    args = parseArgs()

    first = True
    for inp in args.inputs:
        context = mkContext(args.format)
        with context:
            inputType = "???"
            if args.input_is_bits:
                raise NotImplementedError("bits input not implemented")
                inputType = "BITS"
                # TODO. Require a 0x prefix for hex here. If no 0x, then
                # (grudgingly) try to parse it as decimal, but print a warning
                # if it succeeds.
            else:
                try:
                    # Note: it's ("0x" in inp) not (inp.startswith("0x"))
                    # because there could be a negative sign in front. Nothing
                    # with a "0x" in it can be valid decimal, and fromhex is
                    # already going to check validity, so it doesn't matter
                    # that we're being overly forgiving with this check.
                    if "0x" in inp or "0X" in inp:
                        value = bigfloat.BigFloat.fromhex(inp, context=context)
                        inputType = "HEX"
                    else:
                        value = bigfloat.BigFloat.exact(inp,
                            precision=context.precision)
                        inputType = "DECIMAL"
                except ValueError:
                    print("Error: failed to parse input {!r}".format(inp))
                    sys.exit(1)
                    # TODO: Usage and exit. Can we move this parsing into
                    # parseArgs and store the parsed values in args.inputs?
                # TODO:
                #   - Error if the parse succeeded but it's out of range
                #   - Warn if hex input and it's not exact
            if not first:
                print("")
            first = False
            print("### INPUT {}: {}".format(inputType, inp))
            fltVal = FloatValue.fromValue(value, args.format)
            showFloat(fltVal, exactDecimal=args.exact)



def parseArgs():
    parser = argparse.ArgumentParser()

    parser.add_argument("inputs", nargs="*", metavar="VALUE",
                        help="values to show")

    parser.add_argument("-f", "--float", action="store_const",
                        dest="format", const=BINARY32, default=BINARY32,
                        help="single precision (IEEE binary32)")
    parser.add_argument("-d", "--double", action="store_const",
                        dest="format", const=BINARY64,
                        help="double precision (IEEE binary64)")
    parser.add_argument("-L", "--long-double", "--x87",
                        action="store_const", dest="format", const=INTEL80,
                        help="Intel 80-bit extended precision " +
                            "(x86 long double)")
    # TODO: -q, --binary128: IEEE binary128?
    # -h is already taken for --help.
    # TODO: Maybe make all the formats capital for consistency?
    parser.add_argument("-H", "--half", "--fp16", action="store_const",
                        dest="format", const=HALF_PREC,
                        help="half precision")
    parser.add_argument("-v", "--value", action="store_false", default=False,
                        dest="input_is_bits",
                        help="treat input as numerical value")
    parser.add_argument("-b", "--bits", action="store_true",
                        dest="input_is_bits",
                        help="treat input as bit representation")
    parser.add_argument("--exact", action="store_true",
                        help="print exact decimal representation")
    parser.add_argument("--approx", action="store_false", dest="exact",
                        help="print approximate decimal representation " +
                            "(sufficient to recover value)")

    # Now do the hard part of the argument parsing ourself, because argparse
    # doesn't seem to have a (documented) way to treat something like -1.2e3 as
    # a positional argument. Instead, it would interpret that as an optional
    # argument, then give an error because no such argument is defined.
    # argparse actually has a heuristic specifically for identifying negative
    # numbers; it's just not smart enough to recognize all the floating-point
    # formats this script accepts. An alternate way to implement this would be
    # by overriding parser._negative_number_matcher, but since that's not
    # documented, I'm hesitant to take that approach. See:
    #     https://docs.python.org/3/library/argparse.html#arguments-containing
    #
    # The approach here is to split arguments into two groups -- non-positional
    # args and positional args -- move all the positional args to the end, and
    # insert a "--" before them. This forces argparse to treat them as
    # positional, nevermind any leading dashes.
    nonpos_args = []
    pos_args = []
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        # If there's already a "--", stop parsing here because everything else
        # must be positional. Skip over the "--" since we're already going to
        # add that ourself.
        if arg == "--":
            pos_args.extend(sys.argv[i+1:])
            break
        is_positional = False
        if arg[0] != '-':
            is_positional = True
        # All numerical arguments must contain a _decimal_ digit. Hex arguments
        # require a 0x prefix. This is necessary to avoid a genuine ambiguity
        # with some short-form options -- if we allowed unprefixed hex, then is
        # "-f" the short form of --float, or the hex value -15?
        elif any([c.isdigit() for c in arg]):
            is_positional = True
        if is_positional:
            pos_args.append(arg)
        else:
            nonpos_args.append(arg)

    args = parser.parse_args(nonpos_args + ["--"] + pos_args)

    if not args.inputs:
        print("Must specify at least one value")
        parser.print_usage()
        sys.exit(1)

    return args


def selfTest():
    assert mkContext(BINARY32)  == bigfloat.single_precision
    assert mkContext(BINARY64)  == bigfloat.double_precision
    assert mkContext(HALF_PREC) == bigfloat.half_precision



###############################################################################
# Formatting floats (and various properties of them)

# FIXME: This and some helpers need to be wrapped in:
#     with mkContext(fltFormat):
# or possibly a context with wider range but the same precision, to simplify
# some calculations that might cross over FLT_MAX and then back? Might cause
# problems on the subnormal end, though. Maybe better to only increase the
# range for individual calculations where I know it's needed.

def showFloat(fltVal, exactDecimal=False):
    """
    Example format:

    Dec (approx): 1.8125
    Hex (%a):     0x1.dp+0
    int10 * ULP:  15204352 * 2**-23
    fpclassify:   FP_NORMAL
    Bits (hex):   0x3fe80000
    Bits (bin):   0 01111111 11010000000000000000000
    """

    # TODO apply this context
    context = mkContext(fltVal.format)

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
    #       - No, that's wrong. I define ULP as the place value of the bottom
    #         bit of the mantissa, and by that definition powers of 2 are 1/2
    #         ulp from their nextDown.

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
        mostDigits = len(str((2**(1 + fltVal.format.usefulMantBits) - 1) *
            5**-fltVal.format.log2OfMinSubnorm))

        # Use %g mostly because it omits extra trailing zeros after the decimal
        # point, and that's what I want. (Since I'm using such a large
        # precision, simple values would look completely nuts otherwise.) The
        # heuristic %g uses for fixed vs. exponential notation is reasonable;
        # I might prefer exponential for large-magnitude values over a few tens
        # of digits (say 1e+100), but I don't care enough to implement
        # something myself.
        exactString = "{val:.{prec}g}".format(val=fltVal.value,
            prec=2*mostDigits)

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
            (1 + fltVal.format.usefulMantBits)*math.log(2, 10)))
        print("Dec (approx): {val:.{prec}g}".format(val=fltVal.value,
            prec=prec))

    # TODO skip this next part for inf/nan. Actually, maybe just special case
    # the non-bits parts for inf/nan at a higher level? May want to put the
    # parts in separate functions anyway just to save on indents once I add a
    # 'with context'.
    #   - Also, I might have to fabricate a canonical repr for NaNs.

    # Hex (C-style "%a")
    # BigFloat's docs doesn't seem to specify how .hex() or "%a" normalizes,
    # and empirically they are different from each other and _neither_
    # normalizes the way I want! Okay, fine, I'll do it myself.

    # Enough hex digs for a leading 1 (which wastes 3 bits) and then the rest
    # of the mantissa.
    numHexDigs = ceildiv(fltVal.format.totalMantBits + 3, 4)
    mantShift = (1 + 4*(numHexDigs - 1)) - fltVal.format.totalMantBits
    assert 0 <= mantShift < 4
    shiftedMant = fltVal.reprIntMant << mantShift
    rawHexDigs = "{digs:0{count}x}".format(digs=shiftedMant, count=numHexDigs)
    assert len(rawHexDigs) == numHexDigs
    # FIXME: Should be "if leading bit of mantissa is 1". This check is wrong
    # for unnormals and pseudo-denormals.
    if fltVal.storedExpo > 0:
        assert rawHexDigs[0] == '1'
    # Trim 0s from the right. Python's <float>.hex() and BigFloat.hex() don't
    # do this, but at least some libc implementations do.
    while len(rawHexDigs) > 1 and rawHexDigs[-1] == '0':
        rawHexDigs = rawHexDigs[:-1]
    hexStr = ""
    if fltVal.signbit:
        hexStr += '-'
    hexStr += "0x"
    hexStr += rawHexDigs[0]
    if len(rawHexDigs) > 1:
        hexStr += "."
        hexStr += rawHexDigs[1:]
    hexStr += 'p'
    if bigfloat.is_zero(fltVal.value):
        # Special case: display 0 as "0x0p+0", not "0x0p-126". The latter is
        # more faithful to the representation, but the former is more friendly
        # to the user and is what %a actually does (at least the implementation
        # I know; I forget if it's required).
        hexStr += "+0"
    else:
        hexStr += "{:+d}".format(fltVal.reprExpo)
    print("Hex (%a):     {}".format(hexStr))

    print("int10 * ULP:  {sgn}{mant:d} * 2**{expo:d}" \
        .format(sgn  = "-" if fltVal.signbit else "",
                mant = fltVal.reprIntMant,
                expo = fltVal.log2Ulp))

    # TODO unnormals / pseudo-denormals for explicitLeadingBit.
    # Note: likely source for those terms is:
    #     https://www.intel.com/content/www/us/en/architecture-and-technology/64-ia-32-architectures-software-developer-vol-1-manual.html#
    # section 8.2.2 / Table 8-3, which looks to be the source for the Wikipedia
    # article ("Extended precision") where I got the terms from.
    fpcls = "** ERROR **"
    if bigfloat.is_nan(fltVal.value):
        fpcls = "FP_NAN"
    elif bigfloat.is_inf(fltVal.value):
        fpcls = "FP_INFINITE"
    elif bigfloat.is_zero(fltVal.value):
        fpcls = "FP_ZERO"
    elif fltVal.storedExpo == 0:
        fpcls = "FP_SUBNORMAL"
    else:
        fpcls = "FP_NORMAL"
    print("fpclassify:   {}".format(fpcls))

    allBits = fltVal.signbit
    allBits <<= fltVal.format.expBits
    allBits |= fltVal.storedExpo
    allBits <<= fltVal.format.mantBits
    allBits |= fltVal.storedMant
    numDigs = ceildiv(1 + fltVal.format.expBits + fltVal.format.mantBits, 4)
    print("Bits (hex):   0x{val:0{count}x}".format(val=allBits, count=numDigs))

    print("Bits (bin):   {sgn:01b} {expo:0{expoLen}b} {mant:0{mantLen}b}" \
        .format(sgn = fltVal.signbit,
                expo = fltVal.storedExpo,
                expoLen = fltVal.format.expBits,
                mant = fltVal.storedMant,
                mantLen = fltVal.format.mantBits))




###############################################################################
# Converting between value and (sign, expo, mant)

class FloatValue(object):
    def __init__(self, fltFormat, value, sign, expo, mant, **kwargs):
        self.format     = fltFormat
        self.value      = value
        self.signbit    = sign
        self.storedExpo = expo
        self.storedMant = mant
        super(FloatValue, self).__init__(**kwargs)

        assert self.sign * self.reprIntMant * bigfloat.exp2(self.log2Ulp) == \
            self.value
        # TODO other self-tests?

    @classmethod
    def fromValue(cls, value, fltFormat, **kwargs):
        sign, expo, mant = splitSEM(value, fltFormat)
        return cls(fltFormat, value, sign, expo, mant, **kwargs)

    #@classmethod
    #def fromSEM(cls, sign, expo, mant, fltFormat, **kwargs):
    #    value = packSEM(sign, expo, mant, fltFormat)
    #    return cls(fltFormat, value, sign, expo, mant, **kwargs)

    @property
    def sign(self):
        return (-1) ** self.signbit

    @property
    def reprExpo(self):
        """
        Exponent when mantissa is normalized so the highest representable bit
        is in the 1s place. This is the same for subnormals as for FLT_MIN --
        it is the exponent "represented" by the given value, not a simple
        floor(log2(value)).
        """
        ret = self.storedExpo - self.format.bias
        if self.storedExpo == 0:
            ret += 1
        return ret

    @property
    def log2Ulp(self):
        """
        The log2 of the ulp of this value. For purposes of this script, the ulp
        of a (finite) floating-point value is the place value of its least
        significant bit. This is more or less equivalent to:
            nextUp(abs(x)) - abs(x)
        except that it's well-defined when x is FLT_MAX. Note that it's NOT
        always the same as:
            abs(x) - nextDown(abs(x))
        in particular not for powers of 2.
        """
        ret = self.reprExpo - self.format.usefulMantBits
        if self.storedExpo == 0:
            assert ret == self.format.log2OfMinSubnorm
        # TODO: Other self-checks related to this actually being the ULP:
        #   - nextUp (if finite) is actually that distance away
        #   - nextDown is also that distance away, unless we're 0 or pow of 2?
        #   - Maybe try actually XORing the mantissa by 1 and repacking it,
        #     check that abs(the difference) is the ulp?
        return ret

    @property
    def reprIntMant(self):
        ret = self.storedMant
        if self.storedExpo != 0 and not self.format.explicitLeadingBit:
            ret += 2**self.format.mantBits
        return ret

def splitSEM(value, fltFormat):

    signBit = 1 if bigfloat.copysign(1, value) < 0 else 0
    value = bigfloat.abs(value)

    # log2(value) might be within half an ulp below an integer. An example is
    # max subnorm in single precision. Per Python's math.log (double
    # precision):
    #     log2(0x0.fffffep-126) = -0x1.f800000b8aa3cp+6
    # To avoid rounding up in that case, set the rounding mode toward negative
    # infinity.
    if bigfloat.is_zero(value):
        # TODO combine with subnormal code below
        biasedExpo = 0
        expo = 1 - fltFormat.bias
    else:
        with bigfloat.RoundTowardNegative:
            expo = bigfloat.floor(bigfloat.log2(value))
        # TODO logging.debug for all of these, option to enable.
        #print("value = {}".format(value))
        #print("bigfloat.log2(value) = {}".format(bigfloat.log2(value)))
        biasedExpo = int(expo + fltFormat.bias)
        if biasedExpo < 1:
            # Subnormal. The value stored is one less than for FLT_MIN, but the
            # represented exponent is the same; the values are continuous
            # because the leading bit changes to 0 across this threshold.
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

###############################################################################
# Float formats - basics

class FloatFormat(object):
    """
    Class to represent a floating-point format. The format is assumed to follow
    the same basic pattern as IEEE 754 / IEC 60559, except that the mantissa
    might store its leading bit explicitly, because Intel.
    """

    def __init__(self, expBits, mantBits, explicitLeadingBit=False, **kwargs):
        self.expBits = expBits
        self.mantBits = mantBits
        self.explicitLeadingBit = explicitLeadingBit

        # TODO shorter name?
        # Or make it 3 values: storedMantBits, totalMantBits, trailingMantBits,
        # so I'm forced to actually specify each time?
        self.usefulMantBits = mantBits
        if explicitLeadingBit:
            self.usefulMantBits -= 1

        super(FloatFormat, self).__init__(**kwargs)

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

# TODO member function/property?
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

BINARY32  = FloatFormat( 8, 23, False)
BINARY64  = FloatFormat(11, 52, False)
INTEL80   = FloatFormat(15, 64, True)
HALF_PREC = FloatFormat( 5, 10, False)

###############################################################################
# Util / misc

def ceildiv(x, y):
    return (x + y - 1) // y

if __name__ == "__main__":
    main()

