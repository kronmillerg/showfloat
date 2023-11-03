# Show Float

A program for converting floating-point values between different
representations (such as decimal, hex, and the underlying bit pattern).

Example usage:

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

For a list of command-line options, run with `--help`.
