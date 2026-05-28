# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_ablation_stage1_heuristic_neighborhood`
- bundle_name: `ablation_stage1_heuristic_neighborhood`
- cases_total: 151
- succeeded: 144
- failed: 7
- top1_hit_rate: 0.8194
- topk_hit_rate: 0.8194
- execution_success_rate: 0.9444
- mean_execution_time_seconds: 6.2078
- mae: 4.197433
- rmse: 5.854870
- nrmse: 0.272361
- trimmed_mae (drop top 0.5% cases): 3.838727
- trimmed_rmse (drop top 0.5% cases): 5.125562
- trimmed_nrmse (drop top 0.5% cases): 0.266764
- decision_accuracy (loose pass rate): 0.6383

## By Case Category

### `simple`

- cases_scored: 101
- top1_hit_rate: 0.8218
- topk_hit_rate: 0.8218
- execution_success_rate: 0.9307
- mean_execution_time_seconds: 4.4308
- mae: 4.537532
- rmse: 5.778358
- nrmse: 0.216100
- trimmed_mae (drop top 0.5% cases): 4.119198
- trimmed_rmse (drop top 0.5% cases): 4.973355
- trimmed_nrmse (drop top 0.5% cases): 0.207671
- decision_accuracy (loose pass rate): 0.6040

### `complex`

- cases_scored: 43
- top1_hit_rate: 0.8140
- topk_hit_rate: 0.8140
- execution_success_rate: 0.9767
- mean_execution_time_seconds: 10.1851
- mae: 3.333395
- rmse: 6.049250
- nrmse: 0.415297
- trimmed_mae (drop top 0.5% cases): 2.014067
- trimmed_rmse (drop top 0.5% cases): 3.421038
- trimmed_nrmse (drop top 0.5% cases): 0.399055
- decision_accuracy (loose pass rate): 0.7250

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001288 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001280 | yes | yes | yes | yes | 3.2797 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 3.5137 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001523 | yes | yes | yes | no | 2.5500 | - | - | - | no |  |
| case_bench_fmu-001524 | yes | yes | yes | no | 2.1638 | - | - | - | no |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 2.2007 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 2.2282 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 6.5960 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 2.2339 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 2.0169 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001563 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001555 | yes | yes | yes | yes | 2.8941 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001569 | yes | yes | yes | yes | 2.4895 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 3.6365 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 3.0971 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 6.2781 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001571 | yes | yes | yes | yes | 1.7893 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001575 | yes | yes | yes | yes | 1.3817 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001572 | yes | no | no | yes | 5.0780 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001573 | yes | no | no | yes | 5.8358 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001577 | yes | yes | yes | yes | 1.5450 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001574 | yes | no | no | yes | 5.9632 | 43.442641 | 43.442641 | 1.000000 | no |  |
| case_bench_fmu-001576 | yes | no | no | yes | 4.6283 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001579 | yes | yes | yes | yes | 1.7609 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001578 | yes | yes | yes | yes | 1.8524 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001580 | yes | yes | yes | yes | 1.6608 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001581 | yes | yes | yes | yes | 1.8762 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001582 | yes | yes | yes | yes | 1.8522 | 0.048521 | 0.070131 | 0.019551 | yes |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 2.0054 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001584 | yes | yes | yes | yes | 1.9046 | 0.005467 | 0.010411 | 0.000237 | yes |  |
| case_bench_fmu-001586 | yes | yes | yes | yes | 1.7148 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001588 | yes | yes | yes | yes | 1.8998 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001589 | yes | yes | yes | yes | 1.7016 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001591 | yes | yes | yes | yes | 1.2698 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001592 | yes | yes | yes | yes | 1.3146 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 1.4409 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001587 | yes | no | no | yes | 4.9496 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001590 | yes | no | no | yes | 4.3831 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 1.4952 | - | - | - | no |  |
| case_bench_fmu-001597 | yes | yes | yes | yes | 1.4563 | 0.003834 | 0.007104 | 0.005028 | yes |  |
| case_bench_fmu-001598 | yes | yes | yes | yes | 1.5360 | 0.012638 | 0.015612 | 0.005416 | yes |  |
| case_bench_fmu-001594 | yes | no | no | yes | 5.4427 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001600 | yes | yes | yes | yes | 1.3246 | 0.000000 | 0.000000 | 0.001528 | yes |  |
| case_bench_fmu-001605 | yes | yes | yes | yes | 2.0904 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001613 | yes | yes | yes | yes | 2.6882 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001621 | yes | no | no | no | 2.1442 | - | - | - | no |  |
| case_bench_fmu-001629 | yes | yes | yes | yes | 3.0404 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 2.1160 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001665 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001669 | yes | yes | yes | yes | 2.8745 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 5.4827 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 2.5088 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001754 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001758 | yes | yes | yes | yes | 2.4879 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 5.1394 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 1.0799 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 0.9235 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 1.3465 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001776 | yes | yes | yes | yes | 4.8073 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 0.9479 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002019 | yes | yes | yes | yes | 4.5326 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002241 | yes | yes | yes | yes | 4.7415 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 1.8148 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 1.5704 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 1.3295 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 1.5956 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 1.1153 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 1.1591 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001599 | yes | yes | yes | yes | 32.7488 | 0.004166 | 0.009022 | 0.003976 | yes |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 1.4644 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 1.7274 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002302 | yes | no | no | yes | 5.3714 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002303 | yes | no | no | yes | 5.6075 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002305 | yes | no | no | yes | 5.2311 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002306 | yes | no | no | yes | 4.9818 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002308 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-002304 | yes | no | no | yes | 16.8943 | 43.364979 | 43.364979 | 1.000000 | no |  |
| case_bench_fmu-002309 | yes | no | no | yes | 4.6982 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002311 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-002312 | yes | yes | yes | yes | 1.4501 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 57.8719 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_bench_fmu-002314 | yes | yes | yes | yes | 1.8085 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002307 | yes | no | no | yes | 16.0066 | 43.364979 | 43.364979 | 1.000000 | no |  |
| case_bench_fmu-002315 | yes | yes | yes | yes | 1.9859 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002317 | yes | yes | yes | yes | 1.4832 | 0.014467 | 0.027770 | 0.000633 | yes |  |
| case_bench_fmu-002319 | yes | yes | yes | yes | 1.3047 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 0.7757 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002310 | yes | yes | yes | yes | 20.7841 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002322 | yes | yes | yes | yes | 1.3794 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002323 | yes | no | no | yes | 5.7657 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 25.1329 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002325 | yes | yes | yes | yes | 1.1679 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002326 | yes | no | no | yes | 4.1526 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002316 | yes | yes | yes | yes | 26.9490 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002321 | yes | yes | yes | yes | 27.7308 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002336 | yes | yes | yes | yes | 4.4345 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002340 | yes | yes | yes | yes | 1.4427 | 6.855169 | 52.698386 | 0.074496 | no |  |
| case_bench_fmu-002341 | yes | yes | yes | yes | 1.9404 | 0.001058 | 0.051129 | 0.000466 | yes |  |
| case_bench_fmu-002324 | yes | no | no | yes | 15.2377 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002342 | yes | yes | yes | yes | 2.9902 | 0.006604 | 0.014665 | 0.013089 | yes |  |
| case_bench_fmu-002343 | yes | yes | yes | yes | 2.9009 | 0.001768 | 0.002460 | 0.000856 | yes |  |
| case_bench_fmu-002344 | yes | yes | yes | yes | 3.3321 | 0.001998 | 0.003749 | 0.001646 | yes |  |
| case_bench_fmu-002327 | yes | no | no | yes | 12.8314 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002345 | yes | yes | yes | yes | 2.0086 | 0.000000 | 0.000001 | 0.027639 | yes |  |
| case_bench_fmu-002349 | yes | yes | yes | no | 3.3912 | - | - | - | no |  |
| case_bench_fmu-002350 | yes | yes | yes | no | 2.1281 | - | - | - | no |  |
| case_bench_fmu-002352 | yes | yes | yes | no | 2.1479 | - | - | - | no |  |
| case_bench_fmu-002360 | yes | yes | yes | yes | 2.1064 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002376 | yes | no | no | no | 2.0056 | - | - | - | no |  |
| case_bench_fmu-002368 | yes | yes | yes | yes | 2.6028 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002351 | yes | no | no | yes | 5.9223 | 26.400000 | 80.643661 | 1.000000 | no |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 1.7657 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 1.6921 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 3.9916 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 1.9192 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 2.3265 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 1.1688 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 1.1477 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 1.6173 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002452 | yes | yes | yes | yes | 4.0463 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002702 | yes | yes | yes | yes | 1.4081 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 1.4822 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002707 | yes | yes | yes | yes | 1.7772 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002710 | yes | yes | yes | yes | 2.0899 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002736 | yes | yes | yes | yes | 2.1039 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002739 | yes | yes | yes | yes | 1.8042 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002744 | yes | yes | yes | yes | 1.6431 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002704 | yes | no | no | yes | 5.1350 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002749 | yes | yes | yes | yes | 1.2385 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002752 | yes | yes | yes | yes | 1.1896 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002777 | yes | yes | yes | yes | 1.0536 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002779 | yes | yes | yes | yes | 1.5731 | 2.063364 | 3.103850 | 0.570646 | yes |  |
| case_bench_fmu-002782 | yes | yes | yes | yes | 1.6044 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002746 | yes | no | no | yes | 4.8619 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002785 | yes | yes | yes | yes | 1.4986 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002811 | yes | yes | yes | yes | 1.7677 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002814 | yes | yes | yes | yes | 8.9884 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_dtaas_drobotti_rmqfmu | yes | yes | yes | yes | 9.2084 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_incubator_nurv_monitor_validation | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_flex_cell | yes | yes | yes | yes | 17.2946 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_mass_spring_damper | yes | yes | yes | yes | 10.0895 | - | - | - | no |  |
| case_dtaas_three_tank | yes | no | no | yes | 7.4924 | - | - | - | yes |  |
| case_dtaas_water_tank_fi_monitor | yes | no | no | yes | 12.2858 | 12.146166 | 28.585480 | 0.386980 | no |  |
| case_dtaas_mass_spring_damper_monitor | yes | yes | yes | yes | 22.8831 | 3.349200 | 12.250649 | 0.055550 | no |  |
| case_dtaas_water_tank_fi | yes | yes | yes | yes | 32.0924 | 0.421155 | 0.581271 | 0.569867 | no |  |
| case_manual_003 | yes | yes | yes | yes | 2.5942 | - | - | - | no |  |
| case_manual_004 | yes | yes | yes | yes | 4.5414 | - | - | - | no |  |
| case_manual_001 | yes | yes | yes | yes | 31.5107 | 6.473804 | 14.209260 | 0.355870 | yes |  |
| case_dtaas_water_tank_swap | yes | yes | yes | yes | 47.2361 | 0.260172 | 0.453990 | 0.286998 | no |  |
| case_manual_002 | yes | no | no | yes | 49.0582 | 50.829212 | 100.664866 | 0.636292 | - |  |
| case_manual_005 | yes | yes | yes | yes | 41.4368 | - | - | - | yes |  |
