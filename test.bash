#!/bin/bash

my_dir="$(dirname "$(readlink -e "${BASH_SOURCE[0]}")")"

tempdir="$(mktemp -d)"
pushd "$tempdir" > /dev/null

testno=0
failures=0

do1() {
    ((testno++))
    cat > cor.txt
    python "$my_dir"/showfloat.py "$@" > got.txt
    if ! diff -u cor.txt got.txt > diff.txt; then
        if ((failures > 0)); then
            echo
        fi
        ((failures++))
        echo "=== Failed test $testno"
        cat diff.txt
    fi
    rm cor.txt got.txt diff.txt
}

do1 -0x1.55554p-126 <<END
### INPUT HEX: -0x1.55554p-126
Dec (approx): -1.56732431e-38
Hex (%a):     -0x1.55554p-126
int10 * ULP:  11184800 * 2**-149
fpclassify:   FP_NORMAL
Bits (hex):   0x80aaaaa0
Bits (bin):   1 00000001 01010101010101010100000
END

do1 --exact -0x1.55554p-126 <<END
### INPUT HEX: -0x1.55554p-126
Dec (exact):  -1.5673243063780213974867730643181053945143473767500453603948457341650535301624813655507750809192657470703125e-38
Hex (%a):     -0x1.55554p-126
int10 * ULP:  11184800 * 2**-149
fpclassify:   FP_NORMAL
Bits (hex):   0x80aaaaa0
Bits (bin):   1 00000001 01010101010101010100000
END

do1 0x1p-125 <<END
### INPUT HEX: 0x1p-125
Dec (approx): 2.3509887e-38
Hex (%a):     0x1p-125
int10 * ULP:  8388608 * 2**-148
fpclassify:   FP_NORMAL
Bits (hex):   0x01000000
Bits (bin):   0 00000010 00000000000000000000000
END

do1 0x1.fffffep-126 <<END
### INPUT HEX: 0x1.fffffep-126
Dec (approx): 2.35098856e-38
Hex (%a):     0x1.fffffep-126
int10 * ULP:  16777215 * 2**-149
fpclassify:   FP_NORMAL
Bits (hex):   0x00ffffff
Bits (bin):   0 00000001 11111111111111111111111
END

do1 0x1p-126 <<END
### INPUT HEX: 0x1p-126
Dec (approx): 1.17549435e-38
Hex (%a):     0x1p-126
int10 * ULP:  8388608 * 2**-149
fpclassify:   FP_NORMAL
Bits (hex):   0x00800000
Bits (bin):   0 00000001 00000000000000000000000
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

do1 0x1p-149 <<END
### INPUT HEX: 0x1p-149
Dec (approx): 1.40129846e-45
Hex (%a):     0x0.000002p-126
int10 * ULP:  1 * 2**-149
fpclassify:   FP_SUBNORMAL
Bits (hex):   0x00000001
Bits (bin):   0 00000000 00000000000000000000001
END

do1 -0 <<END
### INPUT DECIMAL: -0
Dec (approx): -0
Hex (%a):     -0x0p+0
int10 * ULP:  0 * 2**-149
fpclassify:   FP_ZERO
Bits (hex):   0x80000000
Bits (bin):   1 00000000 00000000000000000000000
END

popd > /dev/null
rmdir "$tempdir"

if ((failures > 0)); then
    echo
    echo "Failed $failures tests"
else
    echo "Passed all $testno tests"
fi
