# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_current_pipeline`
- bundle_name: `current_pipeline`
- cases_total: 151
- succeeded: 151
- failed: 0
- top1_hit_rate: 0.9934
- topk_hit_rate: 0.9934
- execution_success_rate: 0.9536
- mean_execution_time_seconds: 4.1293
- mae: 1.235434
- rmse: 2.550448
- nrmse: 0.116406
- trimmed_mae (drop top 0.5% cases): 0.631457
- trimmed_rmse (drop top 0.5% cases): 1.433186
- trimmed_nrmse (drop top 0.5% cases): 0.111980
- decision_accuracy (loose pass rate): 0.7800

## By Case Category

### `simple`

- cases_scored: 107
- top1_hit_rate: 1.0000
- topk_hit_rate: 1.0000
- execution_success_rate: 0.9439
- mean_execution_time_seconds: 4.4394
- mae: 0.338184
- rmse: 0.962906
- nrmse: 0.046086
- trimmed_mae (drop top 0.5% cases): 0.273014
- trimmed_rmse (drop top 0.5% cases): 0.445552
- trimmed_nrmse (drop top 0.5% cases): 0.043522
- decision_accuracy (loose pass rate): 0.7664

### `complex`

- cases_scored: 44
- top1_hit_rate: 0.9773
- topk_hit_rate: 0.9773
- execution_success_rate: 0.9773
- mean_execution_time_seconds: 3.4009
- mae: 3.620228
- rmse: 6.769965
- nrmse: 0.303309
- trimmed_mae (drop top 0.5% cases): 1.432014
- trimmed_rmse (drop top 0.5% cases): 2.716924
- trimmed_nrmse (drop top 0.5% cases): 0.291855
- decision_accuracy (loose pass rate): 0.8140

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001280 | yes | yes | yes | yes | 9.2118 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001288 | yes | yes | yes | yes | 27.2194 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 30.5495 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 30.5667 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 0.1485 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 0.2955 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 0.2886 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 0.2484 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001555 | yes | yes | yes | yes | 0.1469 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 0.2407 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001563 | yes | yes | yes | yes | 0.3464 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 0.2499 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001569 | yes | yes | yes | yes | 0.1932 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 0.1525 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001571 | yes | yes | yes | yes | 0.1488 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 0.1756 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001573 | yes | yes | yes | yes | 0.1303 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 0.1726 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001575 | yes | yes | yes | yes | 0.2692 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001576 | yes | yes | yes | yes | 0.2314 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001577 | yes | yes | yes | yes | 0.3542 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001578 | yes | yes | yes | yes | 0.3260 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001579 | yes | yes | yes | yes | 0.1969 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001580 | yes | yes | yes | yes | 0.3245 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001581 | yes | yes | yes | yes | 0.2955 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001582 | yes | yes | yes | yes | 0.2126 | 0.048521 | 0.070131 | 0.019551 | yes |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 0.3290 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001584 | yes | yes | yes | yes | 0.3615 | 0.005467 | 0.010411 | 0.000237 | yes |  |
| case_bench_fmu-001586 | yes | yes | yes | yes | 0.2638 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001587 | yes | yes | yes | yes | 0.2340 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001588 | yes | yes | yes | yes | 0.2670 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001589 | yes | yes | yes | yes | 0.2401 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001590 | yes | yes | yes | yes | 0.1900 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001591 | yes | yes | yes | yes | 0.2094 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001592 | yes | yes | yes | yes | 0.2332 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 0.2056 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 0.1377 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 0.3001 | - | - | - | no |  |
| case_bench_fmu-001597 | yes | yes | yes | yes | 0.2384 | 0.003834 | 0.007104 | 0.005028 | yes |  |
| case_bench_fmu-001598 | yes | yes | yes | yes | 0.3684 | 0.012638 | 0.015612 | 0.005416 | yes |  |
| case_bench_fmu-001523 | yes | yes | yes | no | 30.4018 | - | - | - | no |  |
| case_bench_fmu-001600 | yes | yes | yes | yes | 0.4899 | 0.000000 | 0.000000 | 0.001528 | yes |  |
| case_bench_fmu-001605 | yes | yes | yes | yes | 0.6456 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001613 | yes | yes | yes | yes | 0.9914 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001621 | yes | yes | yes | yes | 0.5145 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001629 | yes | yes | yes | yes | 1.2180 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 0.2947 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 0.1741 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001665 | yes | yes | yes | yes | 0.4559 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 0.2549 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 0.2428 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 0.2187 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001754 | yes | yes | yes | yes | 0.4229 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 0.2964 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001776 | yes | yes | yes | yes | 3.0875 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 0.1895 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 0.2418 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 0.3969 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 0.2433 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002019 | yes | yes | yes | yes | 2.7817 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001524 | yes | yes | yes | no | 26.5737 | - | - | - | no |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 0.2636 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 0.1717 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 0.5022 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 0.3232 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 0.1647 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 0.1914 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 0.4419 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 0.2185 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002241 | yes | yes | yes | yes | 3.5733 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002303 | yes | yes | yes | yes | 0.2339 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 0.7306 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002305 | yes | yes | yes | yes | 0.8488 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002306 | yes | yes | yes | yes | 0.2875 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001599 | yes | yes | yes | yes | 29.0094 | 0.004166 | 0.009022 | 0.003976 | yes |  |
| case_bench_fmu-002308 | yes | yes | yes | yes | 0.6400 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002309 | yes | yes | yes | yes | 0.2097 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 24.7242 | 0.033801 | 0.042673 | 0.000984 | yes |  |
| case_bench_fmu-002311 | yes | yes | yes | yes | 0.8908 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002312 | yes | yes | yes | yes | 0.6366 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002307 | yes | yes | yes | yes | 26.7797 | 0.033801 | 0.042673 | 0.000984 | yes |  |
| case_bench_fmu-002314 | yes | yes | yes | yes | 0.7364 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002315 | yes | yes | yes | yes | 0.2924 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 54.1177 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_bench_fmu-002317 | yes | yes | yes | yes | 1.3997 | 0.014467 | 0.027770 | 0.000633 | yes |  |
| case_bench_fmu-002319 | yes | yes | yes | yes | 0.8450 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 0.3898 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002310 | yes | yes | yes | yes | 26.7036 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002322 | yes | yes | yes | yes | 0.6629 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002323 | yes | yes | yes | yes | 0.2414 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 20.9372 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002316 | yes | yes | yes | yes | 21.4497 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002321 | yes | yes | yes | yes | 22.2914 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 20.7199 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002336 | yes | yes | yes | yes | 19.7126 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002325 | yes | yes | yes | yes | 30.5429 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002341 | yes | yes | yes | yes | 0.7812 | 0.001058 | 0.051129 | 0.000466 | yes |  |
| case_bench_fmu-002342 | yes | yes | yes | yes | 0.3510 | 0.006604 | 0.014665 | 0.013089 | yes |  |
| case_bench_fmu-002343 | yes | yes | yes | yes | 0.2662 | 0.001768 | 0.002460 | 0.000856 | yes |  |
| case_bench_fmu-002344 | yes | yes | yes | yes | 0.6560 | 0.001998 | 0.003749 | 0.001646 | yes |  |
| case_bench_fmu-002345 | yes | yes | yes | yes | 0.2540 | 0.000000 | 0.000001 | 0.027639 | yes |  |
| case_bench_fmu-002349 | yes | yes | yes | no | 0.3655 | - | - | - | no |  |
| case_bench_fmu-002350 | yes | yes | yes | no | 0.1471 | - | - | - | no |  |
| case_bench_fmu-002326 | yes | yes | yes | yes | 30.3257 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002351 | yes | yes | yes | no | 0.3238 | - | - | - | no |  |
| case_bench_fmu-002352 | yes | yes | yes | no | 0.2989 | - | - | - | no |  |
| case_bench_fmu-002360 | yes | yes | yes | yes | 0.6119 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002376 | yes | yes | yes | yes | 0.4663 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002368 | yes | yes | yes | yes | 0.9337 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 0.1993 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 0.1781 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 0.4975 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 1.0504 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 0.2786 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 0.2569 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 0.1564 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 0.4640 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 0.3133 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002702 | yes | yes | yes | yes | 0.4115 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002452 | yes | yes | yes | yes | 2.4381 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002704 | yes | yes | yes | yes | 0.8164 | 2.063364 | 3.103850 | 0.570646 | yes |  |
| case_bench_fmu-002707 | yes | yes | yes | yes | 0.3857 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002710 | yes | yes | yes | yes | 0.3139 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002736 | yes | yes | yes | yes | 0.7385 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002739 | yes | yes | yes | yes | 1.0866 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002744 | yes | yes | yes | yes | 0.8496 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002746 | yes | yes | yes | yes | 0.8768 | 2.063364 | 3.103850 | 0.570646 | yes |  |
| case_bench_fmu-002749 | yes | yes | yes | yes | 0.6482 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002752 | yes | yes | yes | yes | 0.4634 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002777 | yes | yes | yes | yes | 0.7561 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002779 | yes | yes | yes | yes | 1.2247 | 2.063364 | 3.103850 | 0.570646 | yes |  |
| case_bench_fmu-002782 | yes | yes | yes | yes | 1.0854 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002785 | yes | yes | yes | yes | 0.5837 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002811 | yes | yes | yes | yes | 0.5472 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 34.2617 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002814 | yes | yes | yes | yes | 0.8062 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_dtaas_drobotti_rmqfmu | yes | yes | yes | yes | 0.5690 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_flex_cell | yes | yes | yes | yes | 0.7552 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_mass_spring_damper | yes | yes | yes | yes | 1.3955 | - | - | - | no |  |
| case_dtaas_three_tank | yes | yes | yes | yes | 0.8915 | - | - | - | yes |  |
| case_dtaas_water_tank_fi | yes | yes | yes | yes | 1.1467 | 0.421155 | 0.581271 | 0.569867 | no |  |
| case_dtaas_water_tank_fi_monitor | yes | yes | yes | yes | 2.9335 | 8.969137 | 22.232033 | 0.268658 | no |  |
| case_dtaas_mass_spring_damper_monitor | yes | yes | yes | yes | 5.7855 | 3.373463 | 12.284342 | 0.054355 | no |  |
| case_dtaas_incubator_nurv_monitor_validation | yes | yes | yes | yes | 6.9426 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_manual_002 | yes | no | no | yes | 2.3873 | 84.584142 | 156.732509 | 0.727091 | - |  |
| case_manual_003 | yes | yes | yes | yes | 0.2631 | - | - | - | no |  |
| case_manual_004 | yes | yes | yes | yes | 0.4605 | - | - | - | no |  |
| case_dtaas_water_tank_swap | yes | yes | yes | yes | 6.1969 | 0.260572 | 0.454430 | 0.287306 | no |  |
| case_manual_001 | yes | yes | yes | yes | 7.0643 | 6.473817 | 14.209262 | 0.355871 | yes |  |
| case_bench_fmu-002340 | yes | yes | yes | yes | 30.5606 | 6.855169 | 52.698386 | 0.074496 | no |  |
| case_manual_005 | yes | yes | yes | yes | 9.9141 | - | - | - | yes |  |
