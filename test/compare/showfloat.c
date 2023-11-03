/* Copyright 2023, Greg Kronmiller
 *
 * C implementation of (the simpler parts of) showfloat, for purposes of
 * comparing two implementations (mostly to verify the tests are correct).
 */

#include <assert.h>
#include <errno.h>
#include <float.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FLT_MIN_SUB_EXP (-149)
#define DBL_MIN_SUB_EXP (-1074)

typedef union {
    float    val;
    uint32_t bits;
} Float;

typedef union {
    double   val;
    uint64_t bits;
} Double;

void showFloat (const char *valString, bool isBits, bool exactDec);
void showDouble(const char *valString, bool isBits, bool exactDec);

const char * bitsToBin(uint64_t bits, int len);
const char *fpcls2str(int fpcls);

// Basically assert, but intended for cases that are possible based on
// arguments (just not supported)
#define assume(expr, desc) doAssume((expr), (desc), #expr, __LINE__);
void doAssume(bool success, const char *desc, const char *exprStr, int lineno);


int main(int argc, char **argv)
{
    bool isDouble = false;
    bool isBits   = false;
    bool exactDec = false;

    char *valString = NULL;

    for (int i = 1; i < argc; i++) {
        bool knownBadArg = false;

        // Not the most efficient way to do argument parsing I'm sure; I just
        // wanted something quick to implement.

        // Supported floating-point types
        if (strcmp(argv[i], "-f") == 0)
            isDouble = false;
        else if (strcmp(argv[i], "--float") == 0)
            isDouble = false;
        else if (strcmp(argv[i], "-d") == 0)
            isDouble = true;
        else if (strcmp(argv[i], "--double") == 0)
            isDouble = true;

        // Unsupported floating-point types
        else if (strcmp(argv[i], "-L") == 0)
            knownBadArg = true;
        else if (strcmp(argv[i], "--long-double") == 0)
            knownBadArg = true;
        else if (strcmp(argv[i], "--intel80") == 0)
            knownBadArg = true;
        else if (strcmp(argv[i], "-H") == 0)
            knownBadArg = true;
        else if (strcmp(argv[i], "--half") == 0)
            knownBadArg = true;
        else if (strcmp(argv[i], "--fp16") == 0)
            knownBadArg = true;

        // Bits vs. value
        else if (strcmp(argv[i], "-v") == 0)
            isBits = false;
        else if (strcmp(argv[i], "--value") == 0)
            isBits = false;
        else if (strcmp(argv[i], "-b") == 0)
            isBits = true;
        else if (strcmp(argv[i], "--bits") == 0)
            isBits = true;

        // Exact vs. approx
        else if (strcmp(argv[i], "--approx") == 0)
            exactDec = false;
        else if (strcmp(argv[i], "--exact") == 0)
            exactDec = true;

        // If we don't recognize it as an option, assume it's positional.
        else {
            if (valString != NULL) {
                printf("Error: multiple values not supported ('%s', '%s')\n",
                    valString, argv[i]);
                return 1;
            }
            valString = argv[i];
        }

        if (knownBadArg) {
            printf("Error: option '%s' not supported\n", argv[i]);
            return 1;
        }
    }
    if (valString == NULL) {
        printf("Error: no value specified\n");
        return 1;
    }

    if (isDouble)
        showDouble(valString, isBits, exactDec);
    else
        showFloat (valString, isBits, exactDec);

    return 0;
}

void showFloat (const char *valString, bool isBits, bool exactDec)
{
    Float u = {0};

    char *end = NULL;
    const char *inputType = NULL;
    if (isBits) {
        inputType = "BITS";

        errno = 0;
        u.bits = strtoul(valString, &end, 0);
        assume(*valString != '\0' && *end == '\0' && errno == 0,
                "failed to parse bits");
    } else {
        // Just use the same heuristic the Python currently uses. If "0x" or
        // "0X" is anywhere in the string, assume it's hex.
        if (strstr(valString, "0x") || strstr(valString, "0X"))
            inputType = "HEX";
        else
            inputType = "DECIMAL";

        errno = 0;
        u.val = strtof(valString, &end);
        // Don't check errno here because it's set for subnormal result.
        assume(*valString != '\0' && *end == '\0' /* && errno == 0 */,
                "failed to parse value");
    }

    // These almost work, but because they get upcast to double in printf, they
    // get normalized differently than what showfloat.py does and the test
    // expects. Should be able to test double subnormals though, I hope...
    assume(fpclassify(u.val) != FP_SUBNORMAL,
        "float subnormals not supported");

    printf("### INPUT %s: %s\n", inputType, valString);
    if (exactDec)
        printf("Dec (exact):  %.999g\n", u.val);
    else
        printf("Dec (approx): %.*g\n", (int)FLT_DECIMAL_DIG, u.val);
    printf("Hex (%%a):     %a\n", u.val);

    int exp = 0;
    float mant = frexpf(u.val, &exp);
    mant = scalbnf(mant, FLT_MANT_DIG);
    exp -= FLT_MANT_DIG;
    if (exp < FLT_MIN_SUB_EXP) {
        mant = scalbnf(mant, exp - FLT_MIN_SUB_EXP);
        exp  = FLT_MIN_SUB_EXP;
    }
    if (mant == 0.0f)
        exp  = FLT_MIN_SUB_EXP;

    if (!isnan(u.val)) {
        float dummy;
        assert(modff(mant, &dummy) == 0.0f);
    }

    // An isfinite check here is enough to work on infinities
    if (isfinite(u.val))
        printf("int10 * ULP:  %.0f * 2**%d\n", mant, exp);
    printf("fpclassify:   %s\n", fpcls2str(fpclassify(u.val)));
    printf("Bits (hex):   0x%08lx\n", (unsigned long)u.bits);

    const char *binBits = bitsToBin(u.bits, 32);
    printf("Bits (bin):   %.1s %.8s %.23s\n", binBits, binBits+1, binBits+9);
}

// Sorry about the copy-paste...
void showDouble(const char *valString, bool isBits, bool exactDec)
{
    Double u = {0};

    char *end = NULL;
    const char *inputType = NULL;
    if (isBits) {
        inputType = "BITS";

        errno = 0;
        u.bits = strtoull(valString, &end, 0);
        assume(*valString != '\0' && *end == '\0' && errno == 0,
                "failed to parse bits");
    } else {
        // Just use the same heuristic the Python currently uses. If "0x" or
        // "0X" is anywhere in the string, assume it's hex.
        if (strstr(valString, "0x") || strstr(valString, "0X"))
            inputType = "HEX";
        else
            inputType = "DECIMAL";

        errno = 0;
        u.val = strtod(valString, &end);
        // Don't check errno here because it's set for subnormal result.
        assume(*valString != '\0' && *end == '\0' /* && errno == 0 */,
                "failed to parse value");
    }

    printf("### INPUT %s: %s\n", inputType, valString);
    if (exactDec)
        printf("Dec (exact):  %.9999g\n", u.val);
    else
        printf("Dec (approx): %.*g\n", (int)DBL_DECIMAL_DIG, u.val);
    printf("Hex (%%a):     %a\n", u.val);

    int exp = 0;
    double mant = frexp(u.val, &exp);
    mant = scalbn(mant, DBL_MANT_DIG);
    exp -= DBL_MANT_DIG;
    if (exp < DBL_MIN_SUB_EXP) {
        mant = scalbn(mant, exp - DBL_MIN_SUB_EXP);
        exp  = DBL_MIN_SUB_EXP;
    }
    if (mant == 0.0)
        exp  = DBL_MIN_SUB_EXP;

    if (!isnan(u.val)) {
        double dummy;
        assert(modf(mant, &dummy) == 0.0);
    }

    // An isfinite check here is enough to work on infinities
    if (isfinite(u.val))
        printf("int10 * ULP:  %.0f * 2**%d\n", mant, exp);
    printf("fpclassify:   %s\n", fpcls2str(fpclassify(u.val)));
    printf("Bits (hex):   0x%016llx\n", (unsigned long long)u.bits);

    const char *binBits = bitsToBin(u.bits, 64);
    printf("Bits (bin):   %.1s %.11s %.52s\n", binBits, binBits+1, binBits+12);
}

// Returns pointer to static buffer, invalidated on next call!
const char * bitsToBin(uint64_t bits, int len)
{
    static char buf[64];
    assert(len <= 64);

    memset(buf, 0, sizeof(buf));
    int i = 64;
    while (len-- > 0) {
        buf[--i] = (bits & 1) ? '1' : '0';
        bits >>= 1;
    }

    return buf+i;
}

const char *fpcls2str(int fpcls)
{
    switch (fpcls) {
        case FP_ZERO      : return "FP_ZERO";
        case FP_SUBNORMAL : return "FP_SUBNORMAL";
        case FP_NORMAL    : return "FP_NORMAL";
        case FP_INFINITE  : return "FP_INFINITE";
        case FP_NAN       : return "FP_NAN";
        default: assert(false);
    }
}

void doAssume(bool success, const char *desc, const char *exprStr, int lineno)
{
    if (!success) {
        printf("Unsupported situation: %s (line %d, failed check '%s')\n",
                desc, lineno, exprStr);
        exit(1);
    }
}
