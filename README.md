# Show Float

A program for converting floating-point values between different
representations (such as decimal, hex, and the underlying bit pattern).

## Setup

Depends on the Python [bigfloat](https://pypi.org/project/bigfloat/) package,
which in turn depends on [GNU MPFR](https://www.mpfr.org/).

Also, disclaimer: I've only tested this with Python 2, so assume it doesn't
work with Python 3.

## Usage

Basic usage is `python showfloat.py VALUE`. For example:

```
$ python showfloat.py 1.5
### INPUT DECIMAL: 1.5
Dec (approx): 1.5
Hex (%a):     0x1.8p+0
int10 * ULP:  12582912 * 2**-23
fpclassify:   FP_NORMAL
Bits (hex):   0x3fc00000
Bits (bin):   0 01111111 10000000000000000000000
```

You can specify the type in which `VALUE` is stored using `--float` (default),
`--double`, `--long-double`, or `--half`.

You can specify whether the input is a value (like 1.5) or a bit pattern
(0x3fc00000 in the above example) using `--value` (default) or `--bits`.

## Reading the output

The output formats are as follows:

*   `Dec` - Decimal, similar to C `printf`'s `%g` (it uses the same heuristic
    for choosing whether to use exponential form).
    *   With `--approx` (the default), prints only enough digits so that
        parsing them back at the same precision would give the original
        value.[^1]
    *   With `--exact`, prints the full decimal representation in all its
        glory. Be warned, for very large or very small values, this could be
        hundreds of digits long.
*   `Hex (%a)` - Hex float format: exponential notation with a hexadecimal
    significand times a power of 2, with the exponent written in decimal. Same
    as C `printf`'s `%a` specifier.
*   `int10 * ULP` - a decimal integer times a power of 2, written like
    `x * 2**y`. The power of 2 is always the one encoded in the exponent field,
    and the mantissa is scaled accordingly -- hence in the above example, 1.5
    is "12582912 * 2**-23", not "3 * 2**-1". This gives 2 useful pieces of
    information:
    *   The whole expression is suitable for copying into a calculator /
        computation software which can handle high-precision values but doesn't
        understand hexadecimal. It exactly represents the input value using
        only integers.
    *   The power of 2 represents the ULP of the value in question. This is the
        spacing between consecutive representable values at this magnitude.[^2]
*   `fpclassify` - The name of the constant that C's
    [fpclassify](https://linux.die.net/man/3/fpclassify) would return for this
    value. One of: `FP_ZERO`, `FP_SUBNORMAL`, `FP_NORMAL`, `FP_INFINITE`,
    `FP_NAN`.
*   `Bits (hex)` - The bit pattern used to represent the value (in IEEE
    format), expressed as a hexadecimal integer. Useful if you're doing
    type-punning shenanigans.
*   `Bits (bin)` - The same bit pattern, expressed in binary with spaces
    separating the 3 fields (sign, exponent, mantissa).

[^1]: More precisely, prints a fixed number of significant digits which is
enough so that every value in the type can be recovered. Does not dynamically
calculate how many digits are needed for each individual value.  This is
probably slightly more than necessary for some normal values, and definitely is
for some subnormals.

[^2]: I define the ULP as the place value of the least significant bit of the
mantissa, so for exact powers of 2, it's the distance to the nearest
representable value moving away from zero but not the nearest value toward
zero.
