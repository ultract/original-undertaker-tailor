/*
 * check-name: Check for correct parentheses for #elif blocks
 * check-command: undertaker -v -j dead $file
 * check-output-start
I: creating correct_parentheses_for_elif.c.B1.no_kconfig.globally.undead
I: creating correct_parentheses_for_elif.c.B2.no_kconfig.globally.dead
I: creating correct_parentheses_for_elif.c.B3.no_kconfig.globally.dead
 * check-output-end
 */

#ifdef CONFIG_A     // Force A to 1

/*
 * Without correct parentheses, the formula for B2 was:
 * B2
 * && ( B2 <-> (CONFIG_B) || (CONFIG_C) && ( ! (B1) ) )
 * && ( B1 <-> (CONFIG_A) )
 * && B00
 *
 * Through the stronger precedence of '&&' over '||' in the second line,
 * the SAT checker was only forced to set CONFIG_A to false if
 * CONFIG_C was enabled, while it is completely disregarded for CONFIG_B.
 * Thus, when checking B2, the SAT checker could set CONFIG_B and
 * CONFIG_A to true (which then fulfills the above formula, but does
 * not reflect what's in the code - CONFIG_B AND CONFIG_C are only to
 * be evaluated if CONFIG_A is not defined), leading to B2 not being
 * recognized as dead.
 */

#if defined(CONFIG_A)
// B1
#elif defined(CONFIG_B) || defined(CONFIG_C)
// B2
#else
// B3
#endif
#endif
