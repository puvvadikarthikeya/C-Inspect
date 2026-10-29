#include <stdio.h>
int calculate_total(int price, int quantity) {
    int total = price * quantity;
    int unused_value = 99;
    return total;
}
int check_limit(int value) {
    int limit = 10;
    if (value = limit) {
        printf("Limit matched.\n");
    }
    return value;
}
int missing_return(int input) {
    if (input > 0) {
        printf("Positive input.\n");
    }
    /* Intentionally missing a return on all paths. */
}
int main(void) {
    int price = 20;
    int quantity = 3;
    int result = calculate_total(price, quantity);
    printf("Calculated total: %d\n", result);
    int result = 15; /* Duplicate declaration in the same scope. */
    printf("Second result: %d\n", result);
    int limit_result = check_limit(10);
    printf("Limit result: %d\n", limit_result);
    printf("Unknown total: %d\n", grand_total);
    int unused_main_value = 123;
    printf("Program continues.\n");
    return 0;
    printf("This statement is unreachable.\n");
}

/* Additional review checkpoints:
   Check that line numbers in diagnostics match the source.
   Check that severity labels are consistent.
   Check that each diagnostic has a stable rule identifier.
   Check that repeated submissions are stored separately.
   Check that history queries use the selected student profile.
   Check that valid code does not receive unrelated errors.
   Check that multiple diagnostics can be shown together.
   Check that analysis can run again after the source is edited.
   Check that the displayed message explains the detected issue.
   Check that syntax failures do not crash the analyzer.
   Check that the interface remains responsive during analysis.
   Check that stored findings can be retrieved after restarting.
   Check that compiler output is separate from static diagnostics.
   Check that the test is repeated after a clean database is used.
   Check that the same rule can be recognized across submissions.
   Check that changing the student profile isolates the history.
   Check that the expected result is recorded for this test case.
   These comments are test documentation, not executable statements.
*/
