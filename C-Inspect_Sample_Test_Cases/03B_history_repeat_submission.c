#include <stdio.h>
int calculate_area(int width, int height) {
    int area = width * height;
    return area;
}
int main(void) {
    int width = 6;
    int height = 9;
    int area = calculate_area(width, height);
    printf("Width: %d\n", width);
    printf("Height: %d\n", height);
    printf("Area: %d\n", area);
    int perimeter = 2 * (width + height);
    printf("Perimeter: %d\n", perimeter);
    int extra_value = 42;
    printf("Extra value: %d\n", extra_value);
    int first_check = area > 0;
    int second_check = perimeter > 0;
    if (first_check) {
        printf("Area is positive.\n");
    }
    if (second_check) {
        printf("Perimeter is positive.\n");
    }
    printf("Intentional error: %d\n", total_cost);
    int step = 0;
    int accumulator = 0;
    while (step < 4) {
        accumulator = accumulator + step;
        step = step + 1;
    }
    printf("Accumulator: %d\n", accumulator);
    printf("Submission 2 complete.\n");
    return 0;
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
