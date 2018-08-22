#ifndef _FLIPPER_H_
#define _FLIPPER_H_

/* Container type for bit field */
#define FLIPPER_ARRAY_TYPE char


#if IS_ENABLED(CONFIG_FLIPPER_TRACE)
#if !(defined __ASSEMBLY__) && (defined __KERNEL__) && !(defined BOOT_COMPRESSED_MISC_H)          \
    && !(defined DISABLE_BRANCH_PROFILING)

/* Number of entries */
#define FLIPPER_ENTRIES CONFIG_FLIPPER_TRACE_ENTRIES

/* Dissabling FLIPPER_ONE_ENTRY_PER_INDEX increases the number of operations
   (only 1 instead of 3 ops) but saves memory - it just needs a
   sizeof(FLIPPER_ARRAY_TYPE)-th bytes (compared to FLIPPER_ENTRIES bytes).
   Your choice! */
#if IS_ENABLED(CONFIG_FLIPPER_TRACE_ONE_ENTRY_PER_INDEX)
#define FLIPPER_ONE_ENTRY_PER_INDEX 1
#endif

/* sets the first 16 bits to 0x4242 (if enabled) */
#if IS_ENABLED(CONFIG_FLIPPER_TRACE_MAGIC_VALUES)
#define FLIPPER_MAGIC_VALUES 1
#endif

/*** NO NEED TO CHANGE SOMETHING BELOW ***/

#ifdef FLIPPER_ONE_ENTRY_PER_INDEX

#define FLIPPER_BITS_PER_INDEX 1
#define FLIPPER_ARRAY_SIZE FLIPPER_ENTRIES
#define FLIPPER_ENTRY_VALUE ((FLIPPER_ARRAY_TYPE)((1 << (sizeof(FLIPPER_ARRAY_TYPE) * 8)) - 1))
#define SET_FLIPPER_BIT(x) (flipper_bitfield[(x)] = FLIPPER_ENTRY_VALUE)
#define TEST_FLIPPER_BIT(x) ((flipper_bitfield[(x)] ^ FLIPPER_ENTRY_VALUE) == 0x0)

#else  // FLIPPER_ONE_ENTRY_PER_INDEX

#define FLIPPER_BITS_PER_INDEX (sizeof(FLIPPER_ARRAY_TYPE) * 8)
#define FLIPPER_ARRAY_SIZE                                                                        \
    ((FLIPPER_ENTRIES / FLIPPER_BITS_PER_INDEX)                                                   \
     + (FLIPPER_ENTRIES % FLIPPER_BITS_PER_INDEX == 0 ? 0 : 1))
#define FLIPPER_BIT_VALUE(x) (1 << ((x) % FLIPPER_BITS_PER_INDEX))
#define SET_FLIPPER_BIT(x) (flipper_bitfield[(x) / FLIPPER_BITS_PER_INDEX] |= FLIPPER_BIT_VALUE(x))
#define TEST_FLIPPER_BIT(x)                                                                       \
    ((flipper_bitfield[(x) / FLIPPER_BITS_PER_INDEX] & FLIPPER_BIT_VALUE(x)) != 0)

#endif  // end FLIPPER_ONE_ENTRY_PER_INDEX

extern FLIPPER_ARRAY_TYPE flipper_bitfield[FLIPPER_ARRAY_SIZE];

#else  // if !(defined __ASSEMBLY__) && (defined __KERNEL__) && ...

#define SET_FLIPPER_BIT(x)
#define TEST_FLIPPER_BIT(x)

#endif  // if !(defined __ASSEMBLY__) && (defined __KERNEL__) && ...

#else  // IS_ENABLED(CONFIG_FLIPPER_TRACE)

#define FLIPPER_ENTRIES 1
#define FLIPPER_MAGIC_VALUES 0
#define SET_FLIPPER_BIT(x) 0
#define TEST_FLIPPER_BIT(x) 0

#endif  // IS_ENABLED(CONFIG_FLIPPER_TRACE)
#endif  // _FLIPPER_H_
