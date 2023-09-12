#!/bin/bash

my_dir="$(dirname "$(readlink -e "${BASH_SOURCE[0]}")")"

testno=0
failures=0

do1() {
    ((testno++))
    cat > cor.txt
    python "$my_dir"/showfloat.py "$@" &> got.txt
    if ! diff -u cor.txt got.txt > diff.txt; then
        if ((failures > 0)); then
            echo
        fi
        ((failures++))
        echo "=== Failed test $testno: showfloat $@" | sed -f color.sed
        sed -f color.sed diff.txt
    fi
    rm cor.txt got.txt diff.txt
}

tempdir="$(mktemp -d)"
pushd "$tempdir" > /dev/null

touch color.sed
# Only use color escapes if stdout is a tty.
if [ -t 1 ]; then
    # Note: which colors look good will depend on exactly how your terminal
    # displays them and what background color you use. These choices are what
    # happen to look good on my terminals. Since this is just the test script,
    # I don't provide a good way to configure it, aside from just hacking up
    # the tput calls manually.
    cat > color.sed <<END
# Failure header in bold red
/^=== /{
    s/^/$(tput setaf 1)$(tput bold)/
    s/$/$(tput sgr0)/
}
# Diff/hunk headers in green (disabled)
#/^\(---\|+++\|@@\) /{
#    s/^/$(tput setaf 2)/
#    s/$/$(tput sgr0)/
#}
# Don't treat diff header as deletion/insertion
/^\(---\|+++\)/!{
    # Deletions in yellow
    /^-/{
        s/^/$(tput setaf 3)/
        s/$/$(tput sgr0)/
    }
    # Insertions in cyan
    /^+/{
        s/^/$(tput setaf 6)/
        s/$/$(tput sgr0)/
    }
}
END
fi

finish() {
    rm color.sed
    popd > /dev/null
    rmdir "$tempdir"

    if ((failures > 0)); then
        echo
        echo "Failed $failures of $testno tests"
    else
        echo "Passed all $testno tests"
    fi
}



###############################################################################

# These tests were haphazardly thrown together by just taking some examples I'd
# tried and testing them against whatever output we already gave. Mostly they
# just verify that the output doesn't change unexpectedly.

do1 -0x1.55554p-126 <<END
### INPUT HEX: -0x1.55554p-126
Dec (approx): -1.56732431e-38
Hex (%a):     -0x1.55554p-126
int10 * ULP:  -11184800 * 2**-149
fpclassify:   FP_NORMAL
Bits (hex):   0x80aaaaa0
Bits (bin):   1 00000001 01010101010101010100000
END

do1 --exact -0x1.55554p-126 <<END
### INPUT HEX: -0x1.55554p-126
Dec (exact):  -1.5673243063780213974867730643181053945143473767500453603948457341650535301624813655507750809192657470703125e-38
Hex (%a):     -0x1.55554p-126
int10 * ULP:  -11184800 * 2**-149
fpclassify:   FP_NORMAL
Bits (hex):   0x80aaaaa0
Bits (bin):   1 00000001 01010101010101010100000
END



# Remaining tests were written intentionally.



###############################################################################
# Basic floating-point categories / edge-cases, single precision

do1 inf <<END
### INPUT DECIMAL: inf
Dec (approx): inf
Hex (%a):     inf
fpclassify:   FP_INFINITE
Bits (hex):   0x7f800000
Bits (bin):   0 11111111 00000000000000000000000
END

do1 -inf <<END
### INPUT DECIMAL: -inf
Dec (approx): -inf
Hex (%a):     -inf
fpclassify:   FP_INFINITE
Bits (hex):   0xff800000
Bits (bin):   1 11111111 00000000000000000000000
END

do1 nan <<END
### INPUT DECIMAL: nan
Dec (approx): nan
Hex (%a):     nan
fpclassify:   FP_NAN
Example bits
       (hex): 0x7fc00000
       (bin): 0 11111111 10000000000000000000000
END

do1 -nan <<END
### INPUT DECIMAL: -nan
Dec (approx): -nan
Hex (%a):     -nan
fpclassify:   FP_NAN
Example bits
       (hex): 0xffc00000
       (bin): 1 11111111 10000000000000000000000
END

do1 0 <<END
### INPUT DECIMAL: 0
Dec (approx): 0
Hex (%a):     0x0p+0
int10 * ULP:  0 * 2**-149
fpclassify:   FP_ZERO
Bits (hex):   0x00000000
Bits (bin):   0 00000000 00000000000000000000000
END

do1 -0 <<END
### INPUT DECIMAL: -0
Dec (approx): -0
Hex (%a):     -0x0p+0
int10 * ULP:  -0 * 2**-149
fpclassify:   FP_ZERO
Bits (hex):   0x80000000
Bits (bin):   1 00000000 00000000000000000000000
END

do1 0x1p-149 <<END
### INPUT HEX: 0x1p-149
Dec (approx): 1.40129846e-45
Hex (%a):     0x0.000002p-126
int10 * ULP:  1 * 2**-149
fpclassify:   FP_SUBNORMAL
Bits (hex):   0x00000001
Bits (bin):   0 00000000 00000000000000000000001
END

do1 -5e-42 <<END
### INPUT DECIMAL: -5e-42
Dec (approx): -4.99983292e-42
Hex (%a):     -0x0.001bep-126
int10 * ULP:  -3568 * 2**-149
fpclassify:   FP_SUBNORMAL
Bits (hex):   0x80000df0
Bits (bin):   1 00000000 00000000000110111110000
END

do1 0x0.fffffep-126 <<END
### INPUT HEX: 0x0.fffffep-126
Dec (approx): 1.17549421e-38
Hex (%a):     0x0.fffffep-126
int10 * ULP:  8388607 * 2**-149
fpclassify:   FP_SUBNORMAL
Bits (hex):   0x007fffff
Bits (bin):   0 00000000 11111111111111111111111
END

do1 -0x1p-126 <<END
### INPUT HEX: -0x1p-126
Dec (approx): -1.17549435e-38
Hex (%a):     -0x1p-126
int10 * ULP:  -8388608 * 2**-149
fpclassify:   FP_NORMAL
Bits (hex):   0x80800000
Bits (bin):   1 00000001 00000000000000000000000
END

do1 4194303.75 <<END
### INPUT DECIMAL: 4194303.75
Dec (approx): 4194303.75
Hex (%a):     0x1.fffffep+21
int10 * ULP:  16777215 * 2**-2
fpclassify:   FP_NORMAL
Bits (hex):   0x4a7fffff
Bits (bin):   0 10010100 11111111111111111111111
END

do1 -4194304 <<END
### INPUT DECIMAL: -4194304
Dec (approx): -4194304
Hex (%a):     -0x1p+22
int10 * ULP:  -8388608 * 2**-1
fpclassify:   FP_NORMAL
Bits (hex):   0xca800000
Bits (bin):   1 10010101 00000000000000000000000
END

do1 1.2345e+10 <<END
### INPUT DECIMAL: 1.2345e+10
Dec (approx): 1.23449999e+10
Hex (%a):     0x1.6fe8ep+33
int10 * ULP:  12055664 * 2**10
fpclassify:   FP_NORMAL
Bits (hex):   0x5037f470
Bits (bin):   0 10100000 01101111111010001110000
END

do1 -0x1.fffffep+127 <<END
### INPUT HEX: -0x1.fffffep+127
Dec (approx): -3.40282347e+38
Hex (%a):     -0x1.fffffep+127
int10 * ULP:  -16777215 * 2**104
fpclassify:   FP_NORMAL
Bits (hex):   0xff7fffff
Bits (bin):   1 11111110 11111111111111111111111
END



###############################################################################
# Input from bits (mostly same cases from above)

do1 --bits 0 <<END
### INPUT BITS: 0
Dec (approx): 0
Hex (%a):     0x0p+0
int10 * ULP:  0 * 2**-149
fpclassify:   FP_ZERO
Bits (hex):   0x00000000
Bits (bin):   0 00000000 00000000000000000000000
END

do1 --bits 0x80000000 <<END
### INPUT BITS: 0x80000000
Dec (approx): -0
Hex (%a):     -0x0p+0
int10 * ULP:  -0 * 2**-149
fpclassify:   FP_ZERO
Bits (hex):   0x80000000
Bits (bin):   1 00000000 00000000000000000000000
END

do1 --bits 1 <<END
### INPUT BITS: 1
Dec (approx): 1.40129846e-45
Hex (%a):     0x0.000002p-126
int10 * ULP:  1 * 2**-149
fpclassify:   FP_SUBNORMAL
Bits (hex):   0x00000001
Bits (bin):   0 00000000 00000000000000000000001
END

do1 --bits 0x7fffff <<END
### INPUT BITS: 0x7fffff
Dec (approx): 1.17549421e-38
Hex (%a):     0x0.fffffep-126
int10 * ULP:  8388607 * 2**-149
fpclassify:   FP_SUBNORMAL
Bits (hex):   0x007fffff
Bits (bin):   0 00000000 11111111111111111111111
END

do1 --bits 0x80800000 <<END
### INPUT BITS: 0x80800000
Dec (approx): -1.17549435e-38
Hex (%a):     -0x1p-126
int10 * ULP:  -8388608 * 2**-149
fpclassify:   FP_NORMAL
Bits (hex):   0x80800000
Bits (bin):   1 00000001 00000000000000000000000
END

# Just some arbitrary hex value, not a duplicate with the previous group of
# cases
do1 --bits 0x12345678 <<END
### INPUT BITS: 0x12345678
Dec (approx): 5.69045661e-28
Hex (%a):     0x1.68acfp-91
int10 * ULP:  11818616 * 2**-114
fpclassify:   FP_NORMAL
Bits (hex):   0x12345678
Bits (bin):   0 00100100 01101000101011001111000
END

do1 --bits 0x4a7fffff <<END
### INPUT BITS: 0x4a7fffff
Dec (approx): 4194303.75
Hex (%a):     0x1.fffffep+21
int10 * ULP:  16777215 * 2**-2
fpclassify:   FP_NORMAL
Bits (hex):   0x4a7fffff
Bits (bin):   0 10010100 11111111111111111111111
END

do1 --bits 0xca800000 <<END
### INPUT BITS: 0xca800000
Dec (approx): -4194304
Hex (%a):     -0x1p+22
int10 * ULP:  -8388608 * 2**-1
fpclassify:   FP_NORMAL
Bits (hex):   0xca800000
Bits (bin):   1 10010101 00000000000000000000000
END

do1 --bits 0xff7fffff <<END
### INPUT BITS: 0xff7fffff
Dec (approx): -3.40282347e+38
Hex (%a):     -0x1.fffffep+127
int10 * ULP:  -16777215 * 2**104
fpclassify:   FP_NORMAL
Bits (hex):   0xff7fffff
Bits (bin):   1 11111110 11111111111111111111111
END

do1 --bits 0x7f800000 <<END
### INPUT BITS: 0x7f800000
Dec (approx): inf
Hex (%a):     inf
fpclassify:   FP_INFINITE
Bits (hex):   0x7f800000
Bits (bin):   0 11111111 00000000000000000000000
END

do1 --bits 0xff800000 <<END
### INPUT BITS: 0xff800000
Dec (approx): -inf
Hex (%a):     -inf
fpclassify:   FP_INFINITE
Bits (hex):   0xff800000
Bits (bin):   1 11111111 00000000000000000000000
END

# The canonical NaN (per the convention this script uses, anyway).
# Since it was specified by bits, it should NOT show as "example bits".
do1 --bits 0x7fc00000 <<END
### INPUT BITS: 0x7fc00000
Dec (approx): nan
Hex (%a):     nan
fpclassify:   FP_NAN
Bits (hex):   0x7fc00000
Bits (bin):   0 11111111 10000000000000000000000
END

# Non-canonical NaNs
do1 --bits 0x7f801230 <<END
### INPUT BITS: 0x7f801230
Dec (approx): nan
Hex (%a):     nan
fpclassify:   FP_NAN
Bits (hex):   0x7f801230
Bits (bin):   0 11111111 00000000001001000110000
END

do1 --bits 0xff800001 <<END
### INPUT BITS: 0xff800001
Dec (approx): -nan
Hex (%a):     -nan
fpclassify:   FP_NAN
Bits (hex):   0xff800001
Bits (bin):   1 11111111 00000000000000000000001
END



###############################################################################

# TODO other categories:
#   - Types: double precision, half, Intel80
#   - Massive exact-decimal cases
#   - Special weird explicit-leading-bit cases (unnormal + pseudo-*)
#   - Semi-bad inputs (especially unrepresentable hex, but also over/underflow
#     and decimal rounding edge cases)
#       - Renormalizing hex, and generally misnormalized cases
#   - Maybe completely bad inputs? Like "junk".



###############################################################################

finish

