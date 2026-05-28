# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_ablation_stage2_graph_match_only`
- bundle_name: `ablation_stage2_graph_match_only`
- cases_total: 151
- succeeded: 151
- failed: 0
- top1_hit_rate: 0.3775
- topk_hit_rate: 0.4106
- execution_success_rate: 0.9470
- mean_execution_time_seconds: 4.5882
- mae: 10126895.801772
- rmse: 16009101.153264
- nrmse: 0.598195
- trimmed_mae (drop top 0.5% cases): 508.306165
- trimmed_rmse (drop top 0.5% cases): 2423.042904
- trimmed_nrmse (drop top 0.5% cases): 0.595262
- decision_accuracy (loose pass rate): 0.3511

## By Case Category

### `simple`

- cases_scored: 107
- top1_hit_rate: 0.4766
- topk_hit_rate: 0.4766
- execution_success_rate: 0.9626
- mean_execution_time_seconds: 4.7608
- mae: 13568070.807336
- rmse: 21449082.313985
- nrmse: 0.558323
- trimmed_mae (drop top 0.5% cases): 679.514271
- trimmed_rmse (drop top 0.5% cases): 3249.765371
- trimmed_nrmse (drop top 0.5% cases): 0.553993
- decision_accuracy (loose pass rate): 0.3364

### `complex`

- cases_scored: 44
- top1_hit_rate: 0.1364
- topk_hit_rate: 0.2500
- execution_success_rate: 0.9091
- mean_execution_time_seconds: 4.1439
- mae: 9.356828
- rmse: 13.737428
- nrmse: 0.715531
- trimmed_mae (drop top 0.5% cases): 6.022811
- trimmed_rmse (drop top 0.5% cases): 9.531690
- trimmed_nrmse (drop top 0.5% cases): 0.707164
- decision_accuracy (loose pass rate): 0.4167

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001280 | yes | yes | yes | yes | 30.7425 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 30.8979 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001288 | yes | no | no | yes | 30.8938 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 30.9015 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001523 | yes | no | no | yes | 0.4318 | 31.000000 | 31.000000 | 1.000000 | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 0.3448 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001535 | yes | no | no | yes | 0.4335 | 10.000000 | 10.000000 | 1.000000 | no |  |
| case_bench_fmu-001524 | yes | no | no | yes | 0.5315 | 4.307538 | 4.688875 | 1.000000 | no |  |
| case_bench_fmu-001555 | yes | yes | yes | yes | 0.3009 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 0.5296 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 0.3270 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001543 | yes | no | no | yes | 0.8860 | 0.999955 | 0.999955 | 1.000000 | no |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 0.5517 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001569 | yes | no | no | yes | 0.5026 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001563 | yes | no | no | yes | 0.6367 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 0.4209 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001571 | yes | no | no | yes | 0.3558 | 43.442641 | 43.442641 | 1.000000 | no |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 0.4777 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001573 | yes | yes | yes | yes | 0.5499 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 0.3062 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001575 | yes | no | no | yes | 0.3341 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001576 | yes | yes | yes | yes | 0.3328 | 0.008421 | 0.015823 | 0.004281 | yes |  |
| case_bench_fmu-001577 | yes | no | no | yes | 0.2559 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001579 | yes | no | no | yes | 0.3911 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001578 | yes | no | no | yes | 0.4481 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001580 | yes | no | no | yes | 0.2834 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001581 | yes | no | no | yes | 0.3758 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001582 | yes | no | no | yes | 0.2996 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 0.4005 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001584 | yes | no | no | yes | 0.4617 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001586 | yes | no | no | yes | 0.4585 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001588 | yes | no | no | yes | 0.3002 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001587 | yes | yes | yes | yes | 0.4426 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001589 | yes | no | no | yes | 0.3104 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001590 | yes | yes | yes | yes | 0.3979 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001591 | yes | no | no | yes | 0.2970 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001592 | yes | no | no | yes | 0.3594 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 0.3908 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 0.4174 | - | - | - | no |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 0.4899 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001597 | yes | no | no | yes | 0.5024 | 0.999492 | 0.999492 | 1.000000 | no |  |
| case_bench_fmu-001598 | yes | no | no | yes | 0.4137 | 2.882502 | 2.882502 | 1.000000 | no |  |
| case_bench_fmu-001600 | yes | no | no | yes | 1.1164 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-001605 | yes | no | no | yes | 1.1514 | 3.789213 | 5.172025 | 0.822161 | no |  |
| case_bench_fmu-001613 | yes | no | no | yes | 0.7227 | 2.321500 | 3.909657 | 1.000000 | no |  |
| case_bench_fmu-001629 | yes | no | no | yes | 0.4731 | 57383.510544 | 303642.742476 | 1.000000 | no |  |
| case_bench_fmu-001621 | yes | no | no | yes | 1.1648 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 0.2294 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 0.2704 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 0.6484 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001665 | yes | no | no | yes | 0.9850 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 0.2603 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 0.2912 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 0.3807 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001754 | yes | no | no | yes | 0.6846 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 0.2843 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001776 | yes | no | no | yes | 0.5258 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 0.2303 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001938 | yes | no | no | yes | 0.5931 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 0.4584 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002019 | yes | no | no | yes | 0.6371 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002241 | yes | no | no | yes | 0.7256 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002268 | yes | no | no | yes | 0.5322 | 10.000000 | 10.000000 | 1.000000 | no |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 0.4834 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 0.4343 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 0.6786 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 0.1845 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 0.2480 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002296 | yes | no | no | yes | 0.4068 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 0.3153 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002303 | yes | yes | yes | yes | 0.5545 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 1.0056 | 0.013050 | 0.025081 | 0.000572 | yes |  |
| case_bench_fmu-002305 | yes | yes | yes | yes | 1.4613 | 0.013050 | 0.025081 | 0.000572 | yes |  |
| case_bench_fmu-002306 | yes | yes | yes | yes | 0.8255 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-001599 | yes | no | no | yes | 12.1008 | 2.261612 | 2.261732 | 1.000000 | no |  |
| case_bench_fmu-002308 | yes | no | no | no | 0.5756 | - | - | - | no |  |
| case_bench_fmu-002309 | yes | yes | yes | yes | 0.2990 | 0.128116 | 0.206620 | 0.040742 | yes |  |
| case_bench_fmu-002310 | yes | no | no | yes | 10.9198 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002311 | yes | no | no | no | 0.6778 | - | - | - | no |  |
| case_bench_fmu-002312 | yes | no | no | yes | 0.2180 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 42.3655 | 0.037691 | 0.047933 | 0.001105 | yes |  |
| case_bench_fmu-002314 | yes | no | no | yes | 0.6809 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002315 | yes | no | no | yes | 0.2607 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002307 | yes | yes | yes | yes | 44.8337 | 0.037691 | 0.047933 | 0.001105 | yes |  |
| case_bench_fmu-002316 | yes | no | no | yes | 9.5070 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 39.1493 | 0.044312 | 0.058078 | 0.001343 | yes |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 65.8970 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_bench_fmu-002317 | yes | no | no | yes | 30.3931 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-002322 | yes | no | no | yes | 0.1799 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002319 | yes | yes | yes | yes | 25.3013 | 0.013050 | 0.025081 | 0.000572 | yes |  |
| case_bench_fmu-002323 | yes | yes | yes | yes | 0.1607 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-002325 | yes | no | no | yes | 0.2106 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002326 | yes | yes | yes | yes | 0.1397 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 30.3825 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-002336 | yes | no | no | yes | 0.1940 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002340 | yes | no | no | yes | 0.1759 | 138.192193 | 238.064833 | 1.000000 | no |  |
| case_bench_fmu-002341 | yes | no | no | yes | 0.1963 | 122.713385 | 154.432115 | 1.000000 | no |  |
| case_bench_fmu-002342 | yes | no | no | yes | 0.2937 | 0.999265 | 0.999266 | 1.000000 | no |  |
| case_bench_fmu-002343 | yes | no | no | yes | 0.2105 | 2.874242 | 2.874242 | 1.000000 | no |  |
| case_bench_fmu-002344 | yes | no | no | yes | 0.5636 | 2.260368 | 2.260482 | 1.000000 | no |  |
| case_bench_fmu-002345 | yes | no | no | yes | 0.1768 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-002349 | yes | no | no | yes | 0.9270 | 1397441982.700000 | 2208924002.272586 | 1.000000 | no |  |
| case_bench_fmu-002350 | yes | no | no | yes | 0.8089 | 3.000000 | 4.123106 | 1.000000 | no |  |
| case_bench_fmu-002351 | yes | yes | yes | no | 0.4400 | - | - | - | no |  |
| case_bench_fmu-002352 | yes | no | no | yes | 0.6723 | 10963.833333 | 26750.263566 | 1.000000 | no |  |
| case_bench_fmu-002360 | yes | no | no | yes | 0.8920 | 3.789213 | 5.172025 | 0.822161 | no |  |
| case_bench_fmu-002368 | yes | no | no | yes | 0.4688 | 2.321500 | 3.909657 | 1.000000 | no |  |
| case_bench_fmu-002376 | yes | no | no | yes | 1.3391 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 1.8452 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 0.3725 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 0.3016 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002418 | yes | no | no | yes | 0.6036 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 0.3610 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002452 | yes | no | no | yes | 0.5479 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 0.3464 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 0.4581 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002321 | yes | no | no | yes | 42.0113 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002558 | yes | no | no | yes | 1.1746 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 0.4711 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002702 | yes | no | no | yes | 0.2767 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002707 | yes | no | no | yes | 0.2714 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002704 | yes | no | no | yes | 0.5797 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002736 | yes | no | no | yes | 0.2647 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002710 | yes | no | no | yes | 0.4185 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002739 | yes | no | no | yes | 0.2462 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002744 | yes | no | no | yes | 0.4512 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002746 | yes | no | no | yes | 0.5471 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002749 | yes | no | no | yes | 0.4444 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002752 | yes | no | no | yes | 0.3579 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002777 | yes | no | no | yes | 0.3085 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002782 | yes | no | no | yes | 0.3337 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002785 | yes | no | no | yes | 0.2336 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002779 | yes | no | no | yes | 0.6594 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002811 | yes | no | no | yes | 0.3890 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002814 | yes | no | no | no | 0.5158 | - | - | - | no |  |
| case_dtaas_drobotti_rmqfmu | yes | no | yes | yes | 0.4985 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_flex_cell | yes | no | no | yes | 1.0961 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_mass_spring_damper | yes | no | yes | yes | 0.5126 | - | - | - | - |  |
| case_dtaas_incubator_nurv_monitor_validation | yes | no | no | yes | 5.3119 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_three_tank | yes | no | no | yes | 1.0064 | - | - | - | - |  |
| case_dtaas_mass_spring_damper_monitor | yes | no | no | yes | 5.6927 | 28.578155 | 56.503360 | 0.560689 | no |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 32.2436 | 0.044312 | 0.058078 | 0.001343 | yes |  |
| case_dtaas_water_tank_fi | yes | no | no | no | 1.1759 | - | - | - | no |  |
| case_dtaas_water_tank_fi_monitor | yes | no | no | no | 1.4813 | - | - | - | no |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 33.3668 | 0.044312 | 0.058078 | 0.001343 | yes |  |
| case_dtaas_water_tank_swap | yes | no | no | no | 1.8743 | - | - | - | no |  |
| case_manual_003 | yes | no | yes | yes | 0.5082 | - | - | - | yes |  |
| case_manual_004 | yes | no | yes | yes | 0.4345 | - | - | - | - |  |
| case_manual_002 | yes | no | no | yes | 3.8478 | 84.584142 | 156.732509 | 0.727091 | - |  |
| case_manual_001 | yes | no | yes | yes | 5.1845 | 9.554685 | 20.455818 | 0.706610 | - |  |
| case_manual_005 | yes | no | no | yes | 34.2891 | - | - | - | no |  |
