# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_ablation_stage3_greedy_multirate`
- bundle_name: `ablation_stage3_greedy_multirate`
- cases_total: 151
- succeeded: 139
- failed: 12
- top1_hit_rate: 0.9424
- topk_hit_rate: 0.9424
- execution_success_rate: 0.9568
- mean_execution_time_seconds: 10.5869
- mae: 1.488821
- rmse: 3.166672
- nrmse: 0.146435
- trimmed_mae (drop top 0.5% cases): 0.834528
- trimmed_rmse (drop top 0.5% cases): 1.957492
- trimmed_nrmse (drop top 0.5% cases): 0.139714
- decision_accuracy (loose pass rate): 0.7721

## By Case Category

### `simple`

- cases_scored: 100
- top1_hit_rate: 0.9700
- topk_hit_rate: 0.9700
- execution_success_rate: 0.9500
- mean_execution_time_seconds: 8.6512
- mae: 0.654524
- rmse: 1.887584
- nrmse: 0.079292
- trimmed_mae (drop top 0.5% cases): 0.380636
- trimmed_rmse (drop top 0.5% cases): 1.049753
- trimmed_nrmse (drop top 0.5% cases): 0.069497
- decision_accuracy (loose pass rate): 0.7300

### `complex`

- cases_scored: 39
- top1_hit_rate: 0.8718
- topk_hit_rate: 0.8718
- execution_success_rate: 0.9744
- mean_execution_time_seconds: 15.4262
- mae: 3.890586
- rmse: 6.848895
- nrmse: 0.339727
- trimmed_mae (drop top 0.5% cases): 1.368912
- trimmed_rmse (drop top 0.5% cases): 2.165032
- trimmed_nrmse (drop top 0.5% cases): 0.319093
- decision_accuracy (loose pass rate): 0.8889

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001280 | yes | yes | yes | yes | 9.7379 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 12.3079 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001523 | yes | yes | yes | no | 18.3517 | - | - | - | no |  |
| case_bench_fmu-001288 | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-001284 | yes | yes | yes | yes | 31.6032 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 1.5231 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 1.5261 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 1.2499 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001555 | yes | yes | yes | yes | 1.3674 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 1.2176 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001563 | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-001569 | yes | yes | yes | yes | 2.3297 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 2.8031 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 1.3341 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001571 | yes | yes | yes | yes | 1.4743 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 1.5791 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001573 | yes | yes | yes | yes | 1.6603 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 1.9142 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001575 | yes | yes | yes | yes | 1.7854 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001524 | yes | yes | yes | no | 32.3655 | - | - | - | no |  |
| case_bench_fmu-001576 | yes | yes | yes | yes | 3.1449 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001577 | yes | yes | yes | yes | 3.1541 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001578 | yes | yes | yes | yes | 2.5955 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001579 | yes | yes | yes | yes | 2.0160 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001580 | yes | yes | yes | yes | 2.6034 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001581 | yes | yes | yes | yes | 2.3446 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001582 | yes | yes | yes | yes | 2.4545 | 0.048521 | 0.070131 | 0.019551 | yes |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 2.3470 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001584 | yes | yes | yes | yes | 3.0939 | 0.005467 | 0.010411 | 0.000237 | yes |  |
| case_bench_fmu-001586 | yes | yes | yes | yes | 4.0325 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 27.5296 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001587 | yes | yes | yes | yes | 4.1378 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001588 | yes | yes | yes | yes | 3.4779 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001589 | yes | yes | yes | yes | 3.8408 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001591 | yes | yes | yes | yes | 3.6842 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001590 | yes | yes | yes | yes | 4.0251 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001592 | yes | yes | yes | yes | 3.6157 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 3.4149 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 4.1550 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 5.8896 | - | - | - | no |  |
| case_bench_fmu-001597 | yes | yes | yes | yes | 4.9156 | 0.003834 | 0.007104 | 0.005028 | yes |  |
| case_bench_fmu-001598 | yes | yes | yes | yes | 4.9677 | 0.012638 | 0.015612 | 0.005416 | yes |  |
| case_bench_fmu-001600 | yes | yes | yes | yes | 3.9077 | 0.000000 | 0.000000 | 0.001528 | yes |  |
| case_bench_fmu-001605 | yes | yes | yes | yes | 3.3766 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001613 | yes | yes | yes | yes | 3.5129 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001621 | yes | no | no | yes | 5.6866 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-001629 | yes | yes | yes | yes | 4.6277 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 1.9856 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001665 | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-001661 | yes | yes | yes | yes | 1.8287 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 2.6033 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 4.3379 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001754 | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-001750 | yes | yes | yes | yes | 2.5063 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 4.2884 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 1.3329 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 1.3349 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001776 | yes | yes | yes | yes | 7.3875 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 2.6734 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 2.6213 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002241 | yes | yes | yes | yes | 5.8692 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002019 | yes | yes | yes | yes | 6.4382 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 2.4002 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 2.4033 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 16.5721 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 61.5970 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 31.1362 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 0.7711 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 0.7252 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 1.5167 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002303 | yes | yes | yes | yes | 1.3281 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 19.6893 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002305 | yes | yes | yes | yes | 2.9089 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002306 | yes | yes | yes | yes | 1.4527 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 31.5196 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002308 | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-002309 | yes | yes | yes | yes | 1.7398 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 42.2807 | 0.033818 | 0.042684 | 0.000984 | yes |  |
| case_bench_fmu-002311 | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-002312 | yes | yes | yes | yes | 1.7959 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002307 | yes | yes | yes | yes | 50.6515 | 0.033818 | 0.042684 | 0.000984 | yes |  |
| case_bench_fmu-002314 | yes | yes | yes | yes | 3.8180 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002315 | yes | yes | yes | yes | 1.7744 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002310 | yes | yes | yes | yes | 49.3560 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002317 | yes | yes | yes | yes | 1.5991 | 0.014467 | 0.027770 | 0.000633 | yes |  |
| case_bench_fmu-002319 | yes | yes | yes | yes | 3.7691 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 38.1120 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002316 | yes | yes | yes | yes | 36.2502 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 30.9355 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002323 | yes | yes | yes | yes | 0.7754 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002322 | yes | yes | yes | yes | 33.2149 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002325 | yes | yes | yes | yes | 2.9082 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002326 | yes | yes | yes | yes | 2.2070 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 44.8570 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002321 | yes | yes | yes | yes | 64.2216 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002340 | yes | yes | yes | yes | 1.8942 | 6.855169 | 52.698386 | 0.074496 | no |  |
| case_bench_fmu-002336 | yes | yes | yes | yes | 7.2415 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002342 | yes | yes | yes | yes | 2.5109 | 0.006604 | 0.014665 | 0.013089 | yes |  |
| case_bench_fmu-002341 | yes | yes | yes | yes | 3.3698 | 0.001058 | 0.051129 | 0.000466 | yes |  |
| case_bench_fmu-002343 | yes | yes | yes | yes | 2.4880 | 0.001768 | 0.002460 | 0.000856 | yes |  |
| case_bench_fmu-002344 | yes | yes | yes | yes | 2.9845 | 0.001998 | 0.003749 | 0.001646 | yes |  |
| case_bench_fmu-002345 | yes | yes | yes | yes | 2.0549 | 0.000000 | 0.000001 | 0.027639 | yes |  |
| case_bench_fmu-002349 | yes | yes | yes | no | 2.4019 | - | - | - | no |  |
| case_bench_fmu-002350 | yes | yes | yes | no | 3.2676 | - | - | - | no |  |
| case_bench_fmu-002351 | yes | no | no | yes | 4.6643 | 26.400000 | 80.643661 | 1.000000 | no |  |
| case_bench_fmu-002352 | yes | yes | yes | no | 2.8795 | - | - | - | no |  |
| case_bench_fmu-002360 | yes | yes | yes | yes | 2.4597 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002368 | yes | yes | yes | yes | 2.5789 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 3.0981 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002376 | yes | no | no | yes | 3.8201 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 1.2539 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 1.4993 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 2.2206 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 2.2366 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 3.9266 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002452 | yes | yes | yes | yes | 5.2274 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 2.2188 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 2.0744 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 53.6159 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002704 | yes | no | no | yes | 27.9460 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 31.6630 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002702 | yes | yes | yes | yes | 32.2187 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002710 | yes | yes | yes | yes | 1.6261 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002736 | yes | yes | yes | yes | 2.0706 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002739 | yes | yes | yes | yes | 2.1045 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002744 | yes | yes | yes | yes | 1.3647 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002749 | yes | yes | yes | yes | 1.4138 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002752 | yes | yes | yes | yes | 1.0639 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002746 | yes | no | no | yes | 4.2919 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002777 | yes | yes | yes | yes | 1.1575 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-001599 | no | no | no | no | - | - | - | - | - | TimeoutError: execution exceeded 300.000 seconds |
| case_bench_fmu-002779 | yes | yes | yes | yes | 2.8838 | 2.063364 | 3.103850 | 0.570646 | yes |  |
| case_bench_fmu-002782 | yes | yes | yes | yes | 3.3483 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002785 | yes | yes | yes | yes | 4.2577 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002811 | yes | yes | yes | yes | 2.9256 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002814 | yes | yes | yes | yes | 18.2686 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_dtaas_drobotti_rmqfmu | yes | yes | yes | yes | 16.7861 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002707 | yes | yes | yes | yes | 33.3938 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_dtaas_flex_cell | yes | no | no | yes | 36.2285 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_mass_spring_damper | yes | yes | yes | yes | 24.1973 | - | - | - | yes |  |
| case_dtaas_incubator_nurv_monitor_validation | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_dtaas_three_tank | yes | no | no | yes | 16.7978 | - | - | - | no |  |
| case_dtaas_water_tank_fi | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_dtaas_mass_spring_damper_monitor | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 does not support discrepancy_set or adapter generation |
| case_dtaas_water_tank_fi_monitor | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_dtaas_water_tank_swap | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 does not support discrepancy_set or adapter generation |
| case_manual_003 | yes | yes | yes | yes | 28.9289 | - | - | - | yes |  |
| case_manual_001 | yes | yes | yes | yes | 39.1406 | 6.743301 | 16.049995 | 0.362604 | yes |  |
| case_manual_002 | yes | no | no | yes | 52.1783 | 84.584142 | 156.732509 | 0.727091 | - |  |
| case_manual_004 | yes | yes | yes | yes | 44.0675 | - | - | - | no |  |
| case_manual_005 | yes | yes | yes | yes | 42.7306 | - | - | - | no |  |
