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
        echo "=== Failed test $testno: showfloat $@"
        cat diff.txt
    fi
    rm cor.txt got.txt diff.txt
}

tempdir="$(mktemp -d)"
pushd "$tempdir" > /dev/null

finish() {
    popd > /dev/null
    rmdir "$tempdir"

    if ((failures > 0)); then
        echo
        echo "Failed $failures tests"
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


# These tests were written intentionally. Hopefully someday all the tests will
# be below this line.

do1 --bits 0x4b16b43f <<END
### INPUT BITS: 0x4b16b43f
Dec (approx): 9876543
Hex (%a):     0x1.2d687ep+23
int10 * ULP:  9876543 * 2**0
fpclassify:   FP_NORMAL
Bits (hex):   0x4b16b43f
Bits (bin):   0 10010110 00101101011010000111111
END



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

# TODO other categories:
#   - Input from bits
#   - Types: double precision, half, Intel80
#   - Massive exact-decimal cases
#   - Special weird explicit-leading-bit cases (unnormal + pseudo-*)
#   - Semi-bad inputs (especially unrepresentable hex, but also over/underflow
#     and decimal rounding edge cases)
#       - Renormalizing hex, and generally misnormalized cases
#   - Maybe completely bad inputs? Like "junk".



###############################################################################

finish

