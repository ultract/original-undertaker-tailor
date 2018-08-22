/*
 * check-name: don't segfault on call on non-existing file
 * check-exit-value: 1
 * check-command: undertaker extra_long_non_existing_file
 * check-error-start
E: failed to open file: `extra_long_non_existing_file'
 * check-error-end
 */

