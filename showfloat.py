#!/usr/bin/env python

import argparse
import bigfloat
import math
import re
import sys

# bigfloat docs:
#     https://bigfloat.readthedocs.io/en/latest/reference/index.html

# TODO Cool features to implement:
#   - Special options for edge-case constants: max norm, min norm, min subnorm.
#     Check the others from float.h to see if some are useful. (Epsilon??)
#       - For that matter, if the input is one of those constants, maybe print
#         the name?
#             ### INPUT HEX: 0x1.fffffep+127
#             float.h name: FLT_MAX
#             Dec (approx): 3.40282347e+38
#             Hex (%a):     0x1.fffffep+127
#             int10 * ULP:  16777215 * 2**104
#             fpclassify:   FP_NORMAL
#             Bits (hex):   0x7f7fffff
#             Bits (bin):   0 11111110 11111111111111111111111
#         I guess in that case we should accept "FLT_MAX" as input.
#           - Which saves some weird reordering difficulties that would arise
#             if I had a --flt_max, since I'm now hacking up the args before
#             argparse gets to them.
#           - Also, I guess showfloat.py -d FLT_MAX is valid, but maybe give a
#             warning if printing a constant in a different format?
#   - Option for "print out the parameters of this floating-point format". Exp
#     bits, mant bits (stored and w/ leading?), exponents of FLT_MAX FLT_MIN
#     FLT_SUB_MIN, exponent bias.


def main():
    selfTest()

    args = parseArgs()

    first = True
    for inp in args.inputs:
        context = mkContext(args.format)
        # TODO this context should maybe be applied by some callees? Or just
        # have a top-level "process one arg" function which applies it and then
        # everyone else assumes that's the context on entry.
        with context:
            inputType = "???"
            if args.input_is_bits:
                # TODO Handle errors gracefully. Make sure the value is
                # nonnegative and not too large.
                bits = int(inp, 0)
                fltVal = FloatValue.fromBits(bits, args.format)
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
                        value = bigfloat.BigFloat(inp, context=context)
                        # bigfloat doesn't preserve the sign bit of "-nan",
                        # even though it is able to represent a NaN with the
                        # sign bit set.
                        if bigfloat.is_nan(value) and NEG_NAN_RE.match(inp):
                            value = bigfloat.copysign(value, -1)
                        inputType = "DECIMAL"
                    fltVal = FloatValue.fromValue(value, args.format)
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
            showFloat(fltVal, exactDecimal=args.exact)


NEG_NAN_RE = re.compile("\s*-\s*nan", flags=re.IGNORECASE)


def parseArgs():
    parser = argparse.ArgumentParser()

    # Note: be careful adding short forms -i, -n, -a here, since that creates
    # an ambiguity with the positional arguments -inf and -nan. It's bad enough
    # that we have a -f.
    # TODO: Maybe get rid of -f? If float is the default, we don't really need
    # a short way to specify it.

    parser.add_argument("inputs", nargs="*", metavar="VALUE",
                        help="values to show")

    parser.add_argument("-f", "--float", action="store_const",
                        dest="format", const=BINARY32, default=BINARY32,
                        help="single precision (IEEE binary32)")
    parser.add_argument("-d", "--double", action="store_const",
                        dest="format", const=BINARY64,
                        help="double precision (IEEE binary64)")
    parser.add_argument("-L", "--long-double", "--intel80",
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

    # Now sort out positional from non-positional arguments ourself, because
    # the rules are too bizarre for argparse to handle on its own. Positional
    # arguments can have a negative sign in front, in which case they'll look
    # like optional arguments. Argparse has a heuristic specifically for
    # identifying negative numbers, so it can handle simple cases like -123.
    # See:
    #     https://docs.python.org/3/library/argparse.html#arguments-containing
    # But once you get into exponential notation or (especially) hex float
    # formats, argparse's negative-number regex doesn't match all the formats
    # we want to accept. Even worse, we accept "-inf" and "-nan" as positional
    # arguments, even though they consist only of letters! In retrospect, maybe
    # having short-form arguments to this script was a mistake (especially -f).
    #
    # My approach is to partition the arguments into non-positionals and
    # positionals, insert a "--" between them, and then pass them into
    # argparse. An alternative way to do this would be to override
    # parser._negative_number_matcher, but since that's not documented, I'm
    # hesitant to take that approach.
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
        # No dashes -> always positional
        if arg[0] != '-':
            is_positional = True
        # Two dashes -> long form option, always non-positional
        elif arg.startswith("--"):
            is_positional = False
        # One dash -> either short form option or negative positional arg. Take
        # a closer look and try to guess which one it is.
        # All numerical arguments must contain a _decimal_ digit. Hex arguments
        # require a 0x prefix. This is necessary to avoid a genuine ambiguity
        # with some short-form options -- if we allowed unprefixed hex, then is
        # "-f" the short form of --float, or the hex value -15?
        elif any([c.isdigit() for c in arg]):
            is_positional = True
        elif "inf" in arg.lower():
            is_positional = True
        elif "nan" in arg.lower():
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

    # TODO add some self-checks to these (but probably not in this function):
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

    with mkContext(fltVal.format):
        decStr = formatDecimal(fltVal, exactDecimal)
        if exactDecimal:
            print("Dec (exact):  {}".format(decStr))
        else:
            print("Dec (approx): {}".format(decStr))

        print(    "Hex (%a):     {}".format(formatHex(fltVal)))

        if bigfloat.is_finite(fltVal.value):
            print("int10 * ULP:  {sgn}{mant:d} * 2**{expo:d}" \
                .format(sgn  = "-" if fltVal.signbit else "",
                        mant = fltVal.reprIntMant,
                        expo = fltVal.log2Ulp))

        print(    "fpclassify:   {}".format(getFpClassifyStr(fltVal)))

        if fltVal.otherBitsPossible:
            print("Example bits")
            print("       (hex): {}".format(formatBitsAsHex(fltVal)))
            print("       (bin): {}".format(formatBitsAsBin(fltVal)))
        else:
            print("Bits (hex):   {}".format(formatBitsAsHex(fltVal)))
            print("Bits (bin):   {}".format(formatBitsAsBin(fltVal)))

def formatDecimal(fltVal, exact):
    if not bigfloat.is_finite(fltVal.value):
        return formatInfNan(fltVal)

    if exact:
        # I think a longest exact base-10 representation for a floating-point
        # format is:
        #     nextDown(2*FLT_MIN)
        #   = 2*FLT_MIN - MIN_FLT_SUBNORM
        #   = (2**(1 + trailingMantBits) - 1) * 2**log2OfMinSubnorm
        # whose decimal digits are the same as:
        #     (2**(1 + trailingMantBits) - 1) * 5**-log2OfMinSubnorm
        # In case I'm wrong, format it with twice that many digits and then
        # assert that the number of sig figs is within my bound.
        mostDigits = len(str((2**(1 + fltVal.format.trailingMantBits) - 1) *
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

        return exactString
    else:
        # The C standard says that this is the number of base-10 digits
        # required to serialize all floating-point values of a given precision
        # to decimal and recover the original values unambiguously. I don't
        # have the background to prove this myself, but I'll trust the standard
        # committee.
        prec = int(math.ceil(1 +
            (1 + fltVal.format.trailingMantBits)*math.log(2, 10)))
        return "{val:.{prec}g}".format(val=fltVal.value, prec=prec)

def formatHex(fltVal):
    """
    Format fltVal as a C-style hex float ("%a"), normalized so that:
      - If fltVal is normal, the digit left of the radix point is 1.
      - If fltVal is subnormal, the displayed exponent is the same as for the
        smallest normal value.
    """

    # This normalization matches the libc implementations I'm familiar with,
    # and is the one I find most intuitive. Unfortunately, empirically neither
    # BigFloat.hex() nor its "{:a}" formatting logic normalizes in this manner
    # (even just for normals), so we have to implement it manually.
    # Fortunately, converting a float to a hex string is pretty simple, since
    # we can get the digits by formatting the mantissa as an integer (ignoring
    # the exponent entirely).

    if not bigfloat.is_finite(fltVal.value):
        return formatInfNan(fltVal)

    # Shift the mantissa so its leading bit is the lsb of a hex digit.
    numHexDigs = ceildiv(fltVal.format.totalMantBits + 3, 4)
    mantShift = (1 + 4*(numHexDigs - 1)) - fltVal.format.totalMantBits
    assert 0 <= mantShift < 4
    shiftedMant = fltVal.reprIntMant << mantShift

    rawHexDigs = "{digs:0{count}x}".format(digs=shiftedMant, count=numHexDigs)
    assert len(rawHexDigs) == numHexDigs
    assert rawHexDigs[0] == str(fltVal.mantLeadingBit)

    # Trim 0s from the right. Python's <float>.hex() and BigFloat.hex() don't
    # do this, but at least some libc implementations do.
    while len(rawHexDigs) > 1 and rawHexDigs[-1] == '0':
        rawHexDigs = rawHexDigs[:-1]

    # Assemble the string.
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
        assert rawHexDigs == "0"
        hexStr += "+0"
    else:
        hexStr += "{:+d}".format(fltVal.reprExpo)
    return hexStr

def formatInfNan(fltVal):
    signchar = "-" if fltVal.signbit else ""
    if bigfloat.is_nan(fltVal.value):
        return signchar + "nan"
    elif bigfloat.is_inf(fltVal.value):
        return signchar + "inf"
    else:
        assert False

def getFpClassifyStr(fltVal):
    # TODO unnormals / pseudo-denormals for explicitLeadingBit.
    # Note: likely source for those terms is [Intel SDM:BA], section 8.2.2 /
    # Table 8-3, which looks to be the source for the Wikipedia article
    # ("Extended precision") where I got the terms from.
    if bigfloat.is_nan(fltVal.value):
        return "FP_NAN"
    elif bigfloat.is_inf(fltVal.value):
        return "FP_INFINITE"
    elif bigfloat.is_zero(fltVal.value):
        return "FP_ZERO"
    elif fltVal.storedExpo == 0:
        return "FP_SUBNORMAL"
    else:
        return "FP_NORMAL"

def formatBitsAsHex(fltVal):
    allBits = fltVal.signbit
    allBits <<= fltVal.format.expBits
    allBits |= fltVal.storedExpo
    allBits <<= fltVal.format.storedMantBits
    allBits |= fltVal.storedMant
    numDigs = ceildiv(1 + fltVal.format.expBits + fltVal.format.storedMantBits,
        4)
    return "0x{val:0{count}x}".format(val=allBits, count=numDigs)

def formatBitsAsBin(fltVal):
    return "{sgn:01b} {expo:0{expoLen}b} {mant:0{mantLen}b}" \
        .format(sgn     = fltVal.signbit,
                expo    = fltVal.storedExpo,
                expoLen = fltVal.format.expBits,
                mant    = fltVal.storedMant,
                mantLen = fltVal.format.storedMantBits)



###############################################################################
# Converting between value and (sign, expo, mant)

class FloatValue(object):
    def __init__(self, fltFormat, value, sign, expo, mant,
            otherBitsPossible=False, **kwargs):
        self.format            = fltFormat
        self.value             = value
        self.signbit           = sign
        self.storedExpo        = expo
        self.storedMant        = mant
        self.otherBitsPossible = otherBitsPossible
        super(FloatValue, self).__init__(**kwargs)

        if bigfloat.is_finite(self.value):
            assert self.sign * self.reprIntMant * \
                bigfloat.exp2(self.log2Ulp) == self.value
        # TODO other self-tests?

    @classmethod
    def fromValue(cls, value, fltFormat, **kwargs):
        sign, expo, mant = valToSEM(value, fltFormat)
        if bigfloat.is_nan(value):
            kwargs["otherBitsPossible"] = True
        return cls(fltFormat, value, sign, expo, mant, **kwargs)

    @classmethod
    def fromBits(cls, bits, fltFormat, **kwargs):
        mant = bits & ((1 << fltFormat.storedMantBits) - 1)
        bits >>= fltFormat.storedMantBits
        expo = bits & ((1 << fltFormat.expBits) - 1)
        bits >>= fltFormat.expBits
        sign = bits
        assert sign == 0 or sign == 1

        value = bitsToVal(sign, expo, mant, fltFormat)
        return cls(fltFormat, value, sign, expo, mant, **kwargs)

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
        assert bigfloat.is_finite(self.value)
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
        assert bigfloat.is_finite(self.value)
        ret = self.reprExpo - self.format.trailingMantBits
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
        assert bigfloat.is_finite(self.value)
        ret = self.storedMant
        if self.storedExpo != 0 and not self.format.explicitLeadingBit:
            ret += 2**self.format.trailingMantBits
        return ret

    @property
    def mantLeadingBit(self):
        assert bigfloat.is_finite(self.value)
        ret = self.reprIntMant >> self.format.trailingMantBits
        if not self.format.explicitLeadingBit:
            if self.storedExpo == 0:
                assert ret == 0
            else:
                assert ret == 1
        return ret

def valToSEM(value, fltFormat):
    signBit = 1 if bigfloat.copysign(1, value) < 0 else 0
    value = bigfloat.abs(value)

    if not bigfloat.is_finite(value):
        expo = fltFormat.storedExpInfNan
        mant = 0
        # Many NaN representations are possible; we just have to pick one. On
        # at least some targets, the canonical NaN has a 1 at the top of the
        # mantissa and 0s below it; not sure how common this is but it seems as
        # good a convention as any.
        if bigfloat.is_nan(value):
            mant += 2**(fltFormat.trailingMantBits - 1)
        # [Intel SDM:BA] The Intel format uses a leading bit of 1 for both inf
        # and NaN; a NaN has at least one 1 in the trailing bits. (So the
        # interpretation is the same as what a normal IEEE-style format would
        # do if the leading bit were implicit). Since that's the only
        # explicitLeadingBit format we support, use that rule here.
        if fltFormat.explicitLeadingBit:
            mant += 2**fltFormat.trailingMantBits
        return (signBit, expo, mant)
    elif bigfloat.is_zero(value):
        return (signBit, 0, 0)

    # log2(value) might be within half an ulp below an integer. An example is
    # max subnorm in single precision. Per Python's math.log (double
    # precision):
    #     log2(0x0.fffffep-126) = -0x1.f800000b8aa3cp+6
    # To avoid rounding up in that case, set the rounding mode toward negative
    # infinity.
    with bigfloat.RoundTowardNegative:
        expo = bigfloat.floor(bigfloat.log2(value))
    biasedExpo = int(expo + fltFormat.bias)
    if biasedExpo < 1:
        # Subnormal. The value stored is one less than for FLT_MIN, but the
        # represented exponent is the same; the values are continuous because
        # the leading bit changes to 0 across this threshold.
        biasedExpo = 0
        expo = 1 - fltFormat.bias

    # The mantissa as it's stored (an integer value).
    with bigfloat.Context(emax=bigfloat.getcontext().emax +
            fltFormat.trailingMantBits):
        mant = value * bigfloat.pow(2, fltFormat.trailingMantBits - expo)
    assert mant == int(mant)
    mant = int(mant)
    leadingMantBitPlaceValue = 2**fltFormat.trailingMantBits
    if biasedExpo > 0 and not fltFormat.explicitLeadingBit:
        # The leading bit is implicitly 1 but not stored in the representation;
        # clear it for the sake of reporting the mantissa.
        mant -= 2**fltFormat.trailingMantBits
        assert 0 <= mant < leadingMantBitPlaceValue
    elif biasedExpo > 0:
        assert leadingMantBitPlaceValue <= mant < 2 * leadingMantBitPlaceValue
    else:
        assert 0 <= mant < leadingMantBitPlaceValue

    return (signBit, biasedExpo, mant)

def bitsToVal(signBit, storedExpo, storedMant, fltFormat):
    sign = (-1) ** signBit

    if storedExpo == fltFormat.storedExpInfNan:
        # Ignore explicit leading bit for purposes of determining inf vs. nan.
        # See [Intel SDM:BA], tables 4-3 and 8-3. If the leading bit is not
        # set, then it's a pseudo-NaN or pseudo-infinity; that will be handled
        # elsewhere.
        trailingMant = storedMant
        if fltFormat.explicitLeadingBit:
            trailingMant &= ((1 << fltFormat.trailingMantBits) - 1)
        if trailingMant == 0:
            return bigfloat.copysign(bigfloat.BigFloat("inf"), sign)
        else:
            return bigfloat.copysign(bigfloat.BigFloat("nan"), sign)

    intMant = storedMant
    if not fltFormat.explicitLeadingBit and storedExpo != 0:
        # Add implicit leading mantissa bit
        intMant += (1 << fltFormat.trailingMantBits)

    log2Ulp = storedExpo - fltFormat.bias - fltFormat.trailingMantBits
    if storedExpo == 0:
        log2Ulp += 1
        assert log2Ulp == fltFormat.log2OfMinSubnorm

    return sign * bigfloat.BigFloat(intMant) * bigfloat.exp2(log2Ulp)

###############################################################################
# Float formats - basics

class FloatFormat(object):
    """
    Class to represent a floating-point format. The format is assumed to follow
    the same basic pattern as IEEE 754 / IEC 60559, except that the mantissa
    might store its leading bit explicitly, because Intel.
    """

    def __init__(self, expBits, storedMantBits, explicitLeadingBit=False,
                **kwargs):
        self.expBits = expBits
        self.storedMantBits = storedMantBits
        self.explicitLeadingBit = explicitLeadingBit

        # TODO shorter name?
        # Or make it 3 values: storedMantBits, totalMantBits, trailingMantBits,
        # so I'm forced to actually specify each time?
        self.trailingMantBits = storedMantBits
        if explicitLeadingBit:
            self.trailingMantBits -= 1

        super(FloatFormat, self).__init__(**kwargs)

    @property
    def bias(self):
        return 2**(self.expBits - 1) - 1

    @property
    def totalMantBits(self):
        return self.trailingMantBits + 1

    @property
    def storedExpInfNan(self):
        return 2**self.expBits - 1

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
        return self.expOfFltMin - self.trailingMantBits

# TODO member function/property?
def mkContext(fltFormat):
    # bigfloat precision counts the leading bit, whether stored or not
    precision = fltFormat.trailingMantBits + 1
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

# References:
#   - [Intel SDM:BA] Intel 64 and IA-32 Architectures Software Developer's
#     Manual, Volume 1: Basic Architecture. Available online at:
#         https://www.intel.com/content/www/us/en/architecture-and-technology/64-ia-32-architectures-software-developer-vol-1-manual.html

if __name__ == "__main__":
    main()

