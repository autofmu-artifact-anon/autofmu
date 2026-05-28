# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_ablation_stage1_rule_template`
- bundle_name: `ablation_stage1_rule_template`
- cases_total: 151
- succeeded: 136
- failed: 15
- top1_hit_rate: 0.8015
- topk_hit_rate: 0.8015
- execution_success_rate: 0.9412
- mean_execution_time_seconds: 5.1505
- mae: 3.845312
- rmse: 5.010846
- nrmse: 0.269220
- trimmed_mae (drop top 0.5% cases): 3.525979
- trimmed_rmse (drop top 0.5% cases): 4.400904
- trimmed_nrmse (drop top 0.5% cases): 0.263326
- decision_accuracy (loose pass rate): 0.6515

## By Case Category

### `simple`

- cases_scored: 101
- top1_hit_rate: 0.8218
- topk_hit_rate: 0.8218
- execution_success_rate: 0.9307
- mean_execution_time_seconds: 4.4414
- mae: 4.537532
- rmse: 5.778358
- nrmse: 0.216100
- trimmed_mae (drop top 0.5% cases): 4.119198
- trimmed_rmse (drop top 0.5% cases): 4.973355
- trimmed_nrmse (drop top 0.5% cases): 0.207671
- decision_accuracy (loose pass rate): 0.6040

### `complex`

- cases_scored: 35
- top1_hit_rate: 0.7429
- topk_hit_rate: 0.7429
- execution_success_rate: 0.9714
- mean_execution_time_seconds: 7.1107
- mae: 1.746322
- rmse: 2.683551
- nrmse: 0.430293
- trimmed_mae (drop top 0.5% cases): 1.593096
- trimmed_rmse (drop top 0.5% cases): 2.132363
- trimmed_nrmse (drop top 0.5% cases): 0.411303
- decision_accuracy (loose pass rate): 0.8065

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001288 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001280 | yes | yes | yes | yes | 3.5327 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 3.5652 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001523 | yes | yes | yes | no | 2.8440 | - | - | - | no |  |
| case_bench_fmu-001524 | yes | yes | yes | no | 1.4635 | - | - | - | no |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 2.1858 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 6.1085 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 2.6085 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 2.3227 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 1.9363 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001563 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001555 | yes | yes | yes | yes | 3.8822 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001569 | yes | yes | yes | yes | 2.2097 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 3.3657 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 1.8716 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 6.1132 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001571 | yes | yes | yes | yes | 2.2879 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001575 | yes | yes | yes | yes | 1.3207 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001572 | yes | no | no | yes | 4.6470 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001577 | yes | yes | yes | yes | 0.9765 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001573 | yes | no | no | yes | 4.9625 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001574 | yes | no | no | yes | 5.2335 | 43.442641 | 43.442641 | 1.000000 | no |  |
| case_bench_fmu-001578 | yes | yes | yes | yes | 1.4988 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001576 | yes | no | no | yes | 3.9165 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001579 | yes | yes | yes | yes | 1.5433 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001580 | yes | yes | yes | yes | 1.6855 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001582 | yes | yes | yes | yes | 1.7401 | 0.048521 | 0.070131 | 0.019551 | yes |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 2.0943 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001581 | yes | yes | yes | yes | 2.4048 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001584 | yes | yes | yes | yes | 1.8123 | 0.005467 | 0.010411 | 0.000237 | yes |  |
| case_bench_fmu-001586 | yes | yes | yes | yes | 1.7821 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001588 | yes | yes | yes | yes | 2.0545 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001589 | yes | yes | yes | yes | 1.7648 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001591 | yes | yes | yes | yes | 1.4711 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001592 | yes | yes | yes | yes | 1.6207 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001587 | yes | no | no | yes | 4.4877 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 1.1195 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 1.4331 | - | - | - | no |  |
| case_bench_fmu-001590 | yes | no | no | yes | 4.8283 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001597 | yes | yes | yes | yes | 1.4935 | 0.003834 | 0.007104 | 0.005028 | yes |  |
| case_bench_fmu-001598 | yes | yes | yes | yes | 1.9801 | 0.012638 | 0.015612 | 0.005416 | yes |  |
| case_bench_fmu-001594 | yes | no | no | yes | 5.1173 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001600 | yes | yes | yes | yes | 1.2085 | 0.000000 | 0.000000 | 0.001528 | yes |  |
| case_bench_fmu-001605 | yes | yes | yes | yes | 2.3688 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001613 | yes | yes | yes | yes | 3.0519 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001621 | yes | no | no | no | 2.3695 | - | - | - | no |  |
| case_bench_fmu-001629 | yes | yes | yes | yes | 3.1234 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 1.9346 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001665 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001669 | yes | yes | yes | yes | 2.5550 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 5.4468 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 2.5582 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001754 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001758 | yes | yes | yes | yes | 2.6613 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 6.0605 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 0.7345 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 0.8383 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 1.2679 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001776 | yes | yes | yes | yes | 5.1636 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 1.4626 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002019 | yes | yes | yes | yes | 5.4221 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002241 | yes | yes | yes | yes | 4.4710 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 1.1805 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 1.2853 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 1.6026 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 1.8795 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 1.2898 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 1.1524 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 1.2673 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 1.5305 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001599 | yes | yes | yes | yes | 35.4279 | 0.004166 | 0.009022 | 0.003976 | yes |  |
| case_bench_fmu-002302 | yes | no | no | yes | 5.5590 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002303 | yes | no | no | yes | 5.7496 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002305 | yes | no | no | yes | 6.5248 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002306 | yes | no | no | yes | 6.4933 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002308 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-002309 | yes | no | no | yes | 4.5991 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002304 | yes | no | no | yes | 17.0680 | 43.364979 | 43.364979 | 1.000000 | no |  |
| case_bench_fmu-002311 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-002312 | yes | yes | yes | yes | 1.9474 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 58.4960 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_bench_fmu-002314 | yes | yes | yes | yes | 1.8252 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002315 | yes | yes | yes | yes | 1.2756 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002307 | yes | no | no | yes | 15.3963 | 43.364979 | 43.364979 | 1.000000 | no |  |
| case_bench_fmu-002317 | yes | yes | yes | yes | 0.9331 | 0.014467 | 0.027770 | 0.000633 | yes |  |
| case_bench_fmu-002319 | yes | yes | yes | yes | 1.2442 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 0.8362 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002310 | yes | yes | yes | yes | 23.3817 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002322 | yes | yes | yes | yes | 2.1547 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 24.6620 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002323 | yes | no | no | yes | 3.8971 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002325 | yes | yes | yes | yes | 1.3713 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002316 | yes | yes | yes | yes | 27.7786 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002326 | yes | no | no | yes | 5.8578 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002321 | yes | yes | yes | yes | 26.2368 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002340 | yes | yes | yes | yes | 1.7614 | 6.855169 | 52.698386 | 0.074496 | no |  |
| case_bench_fmu-002336 | yes | yes | yes | yes | 3.9499 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002324 | yes | no | no | yes | 13.9567 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002342 | yes | yes | yes | yes | 2.2137 | 0.006604 | 0.014665 | 0.013089 | yes |  |
| case_bench_fmu-002343 | yes | yes | yes | yes | 1.5017 | 0.001768 | 0.002460 | 0.000856 | yes |  |
| case_bench_fmu-002341 | yes | yes | yes | yes | 2.9320 | 0.001058 | 0.051129 | 0.000466 | yes |  |
| case_bench_fmu-002345 | yes | yes | yes | yes | 1.3525 | 0.000000 | 0.000001 | 0.027639 | yes |  |
| case_bench_fmu-002344 | yes | yes | yes | yes | 2.0387 | 0.001998 | 0.003749 | 0.001646 | yes |  |
| case_bench_fmu-002349 | yes | yes | yes | no | 2.0072 | - | - | - | no |  |
| case_bench_fmu-002350 | yes | yes | yes | no | 1.8355 | - | - | - | no |  |
| case_bench_fmu-002327 | yes | no | no | yes | 13.6006 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002352 | yes | yes | yes | no | 2.6316 | - | - | - | no |  |
| case_bench_fmu-002360 | yes | yes | yes | yes | 3.1136 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002368 | yes | yes | yes | yes | 2.3364 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002376 | yes | no | no | no | 1.9333 | - | - | - | no |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 1.0735 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002351 | yes | no | no | yes | 6.7525 | 26.400000 | 80.643661 | 1.000000 | no |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 1.2635 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 2.2765 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 2.1652 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 2.5145 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 2.2973 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 1.0325 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 1.2063 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 1.5438 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002452 | yes | yes | yes | yes | 4.6039 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002702 | yes | yes | yes | yes | 1.5416 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002707 | yes | yes | yes | yes | 1.3922 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002710 | yes | yes | yes | yes | 2.3065 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002736 | yes | yes | yes | yes | 2.1444 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002739 | yes | yes | yes | yes | 1.9123 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002704 | yes | no | no | yes | 4.7880 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002744 | yes | yes | yes | yes | 1.5254 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002749 | yes | yes | yes | yes | 1.4312 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002777 | yes | yes | yes | yes | 1.2665 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002752 | yes | yes | yes | yes | 1.3175 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002779 | yes | yes | yes | yes | 1.7924 | 2.063364 | 3.103850 | 0.570646 | yes |  |
| case_bench_fmu-002782 | yes | yes | yes | yes | 1.3242 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002785 | yes | yes | yes | yes | 1.5233 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002746 | yes | no | no | yes | 4.3621 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002811 | yes | yes | yes | yes | 1.5783 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002814 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_mass_spring_damper | yes | no | no | yes | 6.9526 | - | - | - | - |  |
| case_dtaas_drobotti_rmqfmu | yes | yes | yes | yes | 9.1724 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_three_tank | yes | no | no | yes | 4.4980 | - | - | - | - |  |
| case_dtaas_incubator_nurv_monitor_validation | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_water_tank_fi | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_flex_cell | yes | yes | yes | yes | 18.8988 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_water_tank_swap | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_manual_001 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_water_tank_fi_monitor | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_manual_002 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_manual_003 | yes | no | no | yes | 6.8546 | - | - | - | no |  |
| case_manual_004 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_manual_005 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_mass_spring_damper_monitor | yes | no | no | yes | 63.4124 | 6.343102 | 19.219208 | 0.834956 | no |  |
