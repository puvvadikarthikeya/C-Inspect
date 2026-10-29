#include <stdio.h>
int add(int a, int b) { return a + b; }
int subtract(int a, int b) { return a - b; }
int multiply(int a, int b) { return a * b; }
int is_even(int n) { if (n % 2 == 0) return 1; return 0; }
int main(void) {
    int a = 12;
    int b = 4;
    int sum = add(a, b);
    int difference = subtract(a, b);
    int product = multiply(a, b);
    int value = 7;
    int even_status = is_even(value);
    printf("First number: %d\n", a);
    printf("Second number: %d\n", b);
    printf("Sum: %d\n", sum);
    printf("Difference: %d\n", difference);
    printf("Product: %d\n", product);
    printf("Value: %d\n", value);
    if (even_status == 1) {
        printf("The value is even.\n");
    } else {
        printf("The value is odd.\n");
    }
    int counter = 0;
    int total = 0;
    while (counter < 5) {
        total = total + counter;
        counter = counter + 1;
    }
    printf("Loop total: %d\n", total);
    for (int index = 1; index <= 3; index = index + 1) {
        printf("Index: %d\n", index);
    }
    if (sum > product) {
        printf("Sum is greater than product.\n");
    } else {
        printf("Sum is not greater than product.\n");
    }
    int second_total = add(total, sum);
    printf("Second total: %d\n", second_total);
    int check = second_total > 0;
    if (check) printf("Positive result.\n");
    int final_value = subtract(second_total, difference);
    printf("Final value: %d\n", final_value);
    return 0;
}

/* Additional review checkpoints:
   Check that line numbers in diagnostics match the source.
   Check that severity labels are consistent.
   Check that each diagnostic has a stable rule identifier.
   Check that repeated submissions are stored separately.
   Check that history queries use the selected student profile.
   Check that valid code does not receive unrelated errors.
   These comments are test documentation, not executable statements.
*/
