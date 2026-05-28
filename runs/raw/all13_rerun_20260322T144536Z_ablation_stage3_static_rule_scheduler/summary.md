# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_ablation_stage3_static_rule_scheduler`
- bundle_name: `ablation_stage3_static_rule_scheduler`
- cases_total: 151
- succeeded: 133
- failed: 18
- top1_hit_rate: 0.9398
- topk_hit_rate: 0.9398
- execution_success_rate: 0.9549
- mean_execution_time_seconds: 9.8127
- mae: 1.458935
- rmse: 3.089555
- nrmse: 0.145882
- trimmed_mae (drop top 0.5% cases): 0.793934
- trimmed_rmse (drop top 0.5% cases): 1.860412
- trimmed_nrmse (drop top 0.5% cases): 0.139049
- decision_accuracy (loose pass rate): 0.7769

## By Case Category

### `simple`

- cases_scored: 100
- top1_hit_rate: 0.9700
- topk_hit_rate: 0.9700
- execution_success_rate: 0.9500
- mean_execution_time_seconds: 10.1186
- mae: 0.654524
- rmse: 1.887584
- nrmse: 0.079292
- trimmed_mae (drop top 0.5% cases): 0.380636
- trimmed_rmse (drop top 0.5% cases): 1.049753
- trimmed_nrmse (drop top 0.5% cases): 0.069497
- decision_accuracy (loose pass rate): 0.7300

### `complex`

- cases_scored: 33
- top1_hit_rate: 0.8485
- topk_hit_rate: 0.8485
- execution_success_rate: 0.9697
- mean_execution_time_seconds: 8.9045
- mae: 3.924066
- rmse: 6.773017
- nrmse: 0.349948
- trimmed_mae (drop top 0.5% cases): 1.235397
- trimmed_rmse (drop top 0.5% cases): 1.774367
- trimmed_nrmse (drop top 0.5% cases): 0.328279
- decision_accuracy (loose pass rate): 0.9333

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001288 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-001284 | yes | yes | yes | yes | 33.5599 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001280 | yes | yes | yes | yes | 33.5521 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001523 | yes | yes | yes | no | 3.0549 | - | - | - | no |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 34.5060 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 2.9280 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001524 | yes | yes | yes | no | 3.1463 | - | - | - | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 3.6368 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 4.0753 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001563 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-001555 | yes | yes | yes | yes | 3.2989 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 3.4729 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 2.2988 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 3.1790 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001569 | yes | yes | yes | yes | 3.7598 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001571 | yes | yes | yes | yes | 3.7534 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 6.1940 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 3.8094 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001573 | yes | yes | yes | yes | 4.1971 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 4.9422 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001575 | yes | yes | yes | yes | 3.2585 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001576 | yes | yes | yes | yes | 3.5686 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001577 | yes | yes | yes | yes | 3.1470 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001578 | yes | yes | yes | yes | 3.2833 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001579 | yes | yes | yes | yes | 3.3614 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001580 | yes | yes | yes | yes | 2.8881 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001581 | yes | yes | yes | yes | 3.3689 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001582 | yes | yes | yes | yes | 3.1182 | 0.048521 | 0.070131 | 0.019551 | yes |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 3.2173 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001584 | yes | yes | yes | yes | 4.0090 | 0.005467 | 0.010411 | 0.000237 | yes |  |
| case_bench_fmu-001586 | yes | yes | yes | yes | 3.7479 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001587 | yes | yes | yes | yes | 3.5762 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001588 | yes | yes | yes | yes | 3.6587 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001589 | yes | yes | yes | yes | 3.4216 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001590 | yes | yes | yes | yes | 3.5431 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001591 | yes | yes | yes | yes | 2.9589 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001592 | yes | yes | yes | yes | 3.3417 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 3.2462 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 5.1862 | - | - | - | no |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 5.6006 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001597 | yes | yes | yes | yes | 4.6733 | 0.003834 | 0.007104 | 0.005028 | yes |  |
| case_bench_fmu-001598 | yes | yes | yes | yes | 4.6837 | 0.012638 | 0.015612 | 0.005416 | yes |  |
| case_bench_fmu-001600 | yes | yes | yes | yes | 3.6959 | 0.000000 | 0.000000 | 0.001528 | yes |  |
| case_bench_fmu-001605 | yes | yes | yes | yes | 3.0264 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001613 | yes | yes | yes | yes | 3.4300 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001621 | yes | no | no | yes | 4.4315 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-001629 | yes | yes | yes | yes | 4.2121 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 2.9326 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001665 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-001661 | yes | yes | yes | yes | 2.8990 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 2.5593 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 4.5663 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 2.6381 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001754 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-001758 | yes | yes | yes | yes | 4.5302 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001776 | yes | yes | yes | yes | 6.5329 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 53.1508 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 30.7482 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 0.7844 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 11.1331 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 32.6174 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002019 | yes | yes | yes | yes | 3.5892 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 2.4053 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 2.0936 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002241 | yes | yes | yes | yes | 4.3700 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 2.4562 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 2.7306 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 1.9022 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 1.8478 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 2.2366 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 1.9742 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002303 | yes | yes | yes | yes | 2.5487 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 4.1010 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002306 | yes | yes | yes | yes | 3.0728 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002305 | yes | yes | yes | yes | 4.5998 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002308 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-002309 | yes | yes | yes | yes | 1.9063 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 48.2400 | 0.033818 | 0.042684 | 0.000984 | yes |  |
| case_bench_fmu-002311 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-002307 | yes | yes | yes | yes | 51.5738 | 0.033818 | 0.042684 | 0.000984 | yes |  |
| case_bench_fmu-002310 | yes | yes | yes | yes | 45.3899 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002312 | yes | yes | yes | yes | 21.5100 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002315 | yes | yes | yes | yes | 1.2074 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002314 | yes | yes | yes | yes | 32.0140 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002317 | yes | yes | yes | yes | 1.2318 | 0.014467 | 0.027770 | 0.000633 | yes |  |
| case_bench_fmu-002319 | yes | yes | yes | yes | 2.0417 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 1.2630 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 67.3980 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002322 | yes | yes | yes | yes | 2.9699 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002323 | yes | yes | yes | yes | 1.7285 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002321 | yes | yes | yes | yes | 44.1871 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002325 | yes | yes | yes | yes | 3.7379 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002326 | yes | yes | yes | yes | 2.0986 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002316 | yes | yes | yes | yes | 80.1916 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002336 | yes | yes | yes | yes | 5.1774 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002340 | yes | yes | yes | yes | 2.1823 | 6.855169 | 52.698386 | 0.074496 | no |  |
| case_bench_fmu-002341 | yes | yes | yes | yes | 3.4214 | 0.001058 | 0.051129 | 0.000466 | yes |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 43.2269 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002342 | yes | yes | yes | yes | 7.2340 | 0.006604 | 0.014665 | 0.013089 | yes |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 34.9159 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002343 | yes | yes | yes | yes | 9.9271 | 0.001768 | 0.002460 | 0.000856 | yes |  |
| case_bench_fmu-002349 | yes | yes | yes | no | 22.9829 | - | - | - | no |  |
| case_bench_fmu-002344 | yes | yes | yes | yes | 32.1395 | 0.001998 | 0.003749 | 0.001646 | yes |  |
| case_bench_fmu-002350 | yes | yes | yes | no | 1.6886 | - | - | - | no |  |
| case_bench_fmu-002351 | yes | no | no | yes | 3.2190 | 26.400000 | 80.643661 | 1.000000 | no |  |
| case_bench_fmu-002352 | yes | yes | yes | no | 2.1796 | - | - | - | no |  |
| case_bench_fmu-002360 | yes | yes | yes | yes | 1.6330 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002368 | yes | yes | yes | yes | 2.1210 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 3.0825 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002376 | yes | no | no | yes | 3.6853 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-002345 | yes | yes | yes | yes | 32.5256 | 0.000000 | 0.000001 | 0.027639 | yes |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 2.8604 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 2.8857 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 3.2858 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 2.8220 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 2.4261 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 2.6498 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002452 | yes | yes | yes | yes | 5.5427 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 3.1708 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 2.1315 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002702 | yes | yes | yes | yes | 2.3438 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002707 | yes | yes | yes | yes | 2.2957 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002710 | yes | yes | yes | yes | 2.3080 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002704 | yes | no | no | yes | 5.4350 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002736 | yes | yes | yes | yes | 3.6190 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002739 | yes | yes | yes | yes | 3.5618 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002744 | yes | yes | yes | yes | 2.5492 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002749 | yes | yes | yes | yes | 2.1147 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002752 | yes | yes | yes | yes | 2.1626 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-001599 | no | no | no | no | - | - | - | - | - | TimeoutError: execution exceeded 300.000 seconds |
| case_bench_fmu-002777 | yes | yes | yes | yes | 2.3572 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002746 | yes | no | no | yes | 5.3461 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002779 | yes | yes | yes | yes | 3.5427 | 2.063364 | 3.103850 | 0.570646 | yes |  |
| case_bench_fmu-002782 | yes | yes | yes | yes | 4.8465 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002785 | yes | yes | yes | yes | 4.5321 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002811 | yes | yes | yes | yes | 4.3178 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_dtaas_drobotti_rmqfmu | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support loop handling |
| case_bench_fmu-002814 | yes | yes | yes | yes | 24.6409 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_dtaas_incubator_nurv_monitor_validation | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_dtaas_flex_cell | yes | no | no | yes | 41.0922 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_mass_spring_damper | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support loop handling |
| case_dtaas_three_tank | yes | no | no | yes | 34.5564 | - | - | - | no |  |
| case_dtaas_water_tank_fi | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_dtaas_mass_spring_damper_monitor | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support discrepancy_set or adapter generation |
| case_dtaas_water_tank_fi_monitor | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_dtaas_water_tank_swap | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support discrepancy_set or adapter generation |
| case_manual_001 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support loop handling |
| case_manual_002 | yes | no | no | yes | 32.9800 | 84.584142 | 156.732509 | 0.727091 | - |  |
| case_manual_003 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support loop handling |
| case_manual_004 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support loop handling |
| case_manual_005 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support loop handling |
