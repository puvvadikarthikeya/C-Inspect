C-INSPECT SAMPLE TEST CASES

All four C source files contain at least 50 lines (including test documentation comments).

01_valid_program.c
Tests ordinary valid syntax, functions, declarations, conditions, loops and output.
Expected: no intentional static-analysis findings.

02_static_analysis_issues.c
Intentional issues:
- unused_value and unused_main_value: unused local variables
- assignment in condition: if (value = limit)
- missing return path in missing_return()
- duplicate declaration of result
- undeclared identifier grand_total
- statement after return: unreachable code
A parser may stop or suppress later findings after an earlier syntax/semantic error.

03A_history_first_submission.c and 03B_history_repeat_submission.c
Use the SAME student profile for both submissions.
First submission has undeclared identifier total_area; second has total_cost.
Expected: both should trigger the same stable diagnostic rule ID, and the recurrence/history count should increase.
This tests whether recurrence is based on rule identity rather than variable spelling.

Run each file through C-Inspect and compare actual findings against expected findings.
These are test inputs, not a claim that every listed rule is implemented.
