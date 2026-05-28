# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_baseline_b3_graph_aware`
- bundle_name: `baseline_b3_graph_aware`
- cases_total: 151
- succeeded: 147
- failed: 4
- top1_hit_rate: 0.5510
- topk_hit_rate: 0.5510
- execution_success_rate: 0.9252
- mean_execution_time_seconds: 1.5275
- mae: 444.312201
- rmse: 2312.106721
- nrmse: 0.522074
- trimmed_mae (drop top 0.5% cases): 9.661832
- trimmed_rmse (drop top 0.5% cases): 11.872861
- trimmed_nrmse (drop top 0.5% cases): 0.510792
- decision_accuracy (loose pass rate): 0.4122

## By Case Category

### `simple`

- cases_scored: 106
- top1_hit_rate: 0.6226
- topk_hit_rate: 0.6226
- execution_success_rate: 0.8962
- mean_execution_time_seconds: 0.6359
- mae: 613.613678
- rmse: 3207.041712
- nrmse: 0.405519
- trimmed_mae (drop top 0.5% cases): 9.678604
- trimmed_rmse (drop top 0.5% cases): 10.917236
- trimmed_nrmse (drop top 0.5% cases): 0.399194
- decision_accuracy (loose pass rate): 0.4057

### `complex`

- cases_scored: 41
- top1_hit_rate: 0.3659
- topk_hit_rate: 0.3659
- execution_success_rate: 1.0000
- mean_execution_time_seconds: 3.5935
- mae: 9.619220
- rmse: 14.300663
- nrmse: 0.821337
- trimmed_mae (drop top 0.5% cases): 6.477715
- trimmed_rmse (drop top 0.5% cases): 10.408123
- trimmed_nrmse (drop top 0.5% cases): 0.788596
- decision_accuracy (loose pass rate): 0.4400

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001280 | yes | yes | yes | yes | 0.6665 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 0.7397 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 0.7490 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001288 | yes | yes | yes | yes | 0.9394 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001523 | yes | no | no | yes | 0.4721 | 31.000000 | 31.000000 | 1.000000 | no |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 0.4191 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001524 | yes | no | no | yes | 0.5555 | 4.307538 | 4.688875 | 1.000000 | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 0.5230 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001555 | yes | yes | yes | yes | 0.5578 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 0.7423 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 0.7366 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 0.5442 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001569 | yes | no | no | yes | 0.4939 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 0.6919 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001563 | yes | yes | yes | yes | 0.7832 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 0.5259 | 0.124852 | 0.199641 | 0.042775 | yes |  |
| case_bench_fmu-001571 | yes | no | no | yes | 0.4912 | 43.442641 | 43.442641 | 1.000000 | no |  |
| case_bench_fmu-001573 | yes | yes | yes | yes | 0.4728 | 0.124852 | 0.199641 | 0.042775 | yes |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 0.6241 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001575 | yes | no | no | yes | 0.4524 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 0.7095 | 3.537296 | 4.657938 | 0.107220 | no |  |
| case_bench_fmu-001577 | yes | no | no | yes | 0.3762 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001576 | yes | yes | yes | yes | 0.5375 | 0.133084 | 0.208688 | 0.046757 | yes |  |
| case_bench_fmu-001578 | yes | no | no | yes | 0.3059 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001579 | yes | no | no | yes | 0.4884 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001580 | yes | no | no | yes | 0.4042 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001581 | yes | no | no | yes | 0.4370 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001582 | yes | no | no | yes | 0.5578 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001584 | yes | no | no | yes | 0.4011 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 0.6751 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001586 | yes | no | no | yes | 0.6243 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001588 | yes | no | no | yes | 0.3580 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001587 | yes | yes | yes | yes | 0.5736 | 0.124852 | 0.199641 | 0.042775 | yes |  |
| case_bench_fmu-001589 | yes | no | no | yes | 0.4286 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001591 | yes | no | no | yes | 0.4245 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001592 | yes | no | no | yes | 0.5612 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001590 | yes | yes | yes | yes | 0.7194 | 0.124852 | 0.199641 | 0.042775 | yes |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 0.5923 | 0.124852 | 0.199641 | 0.042775 | yes |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 0.8284 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001597 | yes | no | no | yes | 1.2427 | 0.999492 | 0.999492 | 1.000000 | no |  |
| case_bench_fmu-001598 | yes | no | no | yes | 1.3527 | 2.882502 | 2.882502 | 1.000000 | no |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 2.4631 | - | - | - | no |  |
| case_bench_fmu-001599 | yes | no | no | yes | 0.8647 | 2.261612 | 2.261732 | 1.000000 | no |  |
| case_bench_fmu-001600 | yes | no | no | yes | 0.6611 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-001613 | yes | no | no | no | 0.8485 | - | - | - | no |  |
| case_bench_fmu-001605 | yes | yes | yes | yes | 1.5107 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001629 | yes | no | no | yes | 1.5980 | 57383.510544 | 303642.742476 | 1.000000 | no |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 1.1320 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001621 | yes | no | no | no | 2.8621 | - | - | - | no |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 0.8518 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001665 | yes | yes | yes | yes | 1.3063 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 0.8922 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 1.1352 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 0.8474 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 0.9222 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001754 | yes | yes | yes | yes | 1.3877 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001776 | yes | no | no | yes | 0.8331 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 0.5100 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 0.4171 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 0.4870 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 0.7097 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002019 | yes | no | no | yes | 0.3662 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002241 | yes | no | no | yes | 0.4284 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 0.4313 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 0.5032 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 0.5237 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 0.9209 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 0.7220 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 0.4265 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 0.7262 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 1.0083 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 0.7484 | 0.009348 | 0.017965 | 0.000410 | yes |  |
| case_bench_fmu-002303 | yes | yes | yes | yes | 0.3156 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002306 | yes | yes | yes | yes | 0.3754 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002305 | yes | yes | yes | yes | 0.5562 | 0.009348 | 0.017965 | 0.000410 | yes |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 0.6625 | 3.535673 | 4.654562 | 0.107335 | no |  |
| case_bench_fmu-002307 | yes | yes | yes | yes | 0.5226 | 3.535673 | 4.654562 | 0.107335 | no |  |
| case_bench_fmu-002309 | yes | yes | yes | yes | 0.5025 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002310 | yes | no | no | yes | 0.3786 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002312 | yes | no | no | yes | 0.5855 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 0.6836 | 3.535650 | 4.649164 | 0.107525 | no |  |
| case_bench_fmu-002308 | yes | no | no | no | 2.2288 | - | - | - | no |  |
| case_bench_fmu-002314 | no | no | no | no | - | - | - | - | - | TimeoutError: execution exceeded 300.000 seconds |
| case_bench_fmu-002311 | yes | no | no | no | 2.1081 | - | - | - | no |  |
| case_bench_fmu-002315 | yes | no | no | yes | 0.4538 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002316 | yes | no | no | yes | 0.3383 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002317 | yes | no | no | yes | 0.3153 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-002319 | yes | no | no | yes | 0.3505 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 0.3550 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002321 | yes | no | no | yes | 0.3457 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002322 | yes | no | no | yes | 0.3287 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002323 | yes | yes | yes | yes | 0.3700 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002325 | yes | no | no | yes | 0.3400 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 0.5613 | 3.535650 | 4.649164 | 0.107525 | no |  |
| case_bench_fmu-002326 | yes | yes | yes | yes | 0.3581 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002336 | yes | no | no | yes | 0.3925 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002340 | yes | no | no | yes | 0.3033 | 138.192193 | 238.064833 | 1.000000 | no |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 0.7627 | 3.535650 | 4.649164 | 0.107525 | no |  |
| case_bench_fmu-002341 | yes | no | no | yes | 0.4828 | 122.713385 | 154.432115 | 1.000000 | no |  |
| case_bench_fmu-002342 | yes | no | no | yes | 0.4510 | 0.999265 | 0.999266 | 1.000000 | no |  |
| case_bench_fmu-002343 | yes | no | no | yes | 0.4274 | 2.874242 | 2.874242 | 1.000000 | no |  |
| case_bench_fmu-002344 | yes | no | no | yes | 0.3846 | 2.260368 | 2.260482 | 1.000000 | no |  |
| case_bench_fmu-002345 | yes | no | no | yes | 0.3142 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-002349 | yes | yes | yes | no | 1.0339 | - | - | - | no |  |
| case_bench_fmu-002350 | yes | yes | yes | no | 2.4578 | - | - | - | no |  |
| case_bench_fmu-002351 | yes | yes | yes | no | 2.7029 | - | - | - | no |  |
| case_bench_fmu-002368 | yes | no | no | no | 0.4927 | - | - | - | no |  |
| case_bench_fmu-002352 | yes | yes | yes | no | 2.3458 | - | - | - | no |  |
| case_bench_fmu-002360 | yes | yes | yes | yes | 1.2124 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 0.4320 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 0.4003 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 1.8342 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 0.6294 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002376 | yes | no | no | no | 2.1827 | - | - | - | no |  |
| case_bench_fmu-002452 | yes | no | no | yes | 0.3545 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 0.4818 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 0.3431 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 0.2834 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 0.6580 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 0.5882 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002702 | yes | no | no | yes | 0.5590 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002704 | yes | no | no | yes | 0.3696 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002707 | yes | no | no | yes | 0.3796 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002710 | yes | no | no | yes | 0.4014 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002744 | yes | no | no | yes | 0.5938 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002746 | yes | no | no | yes | 0.5796 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002749 | yes | no | no | yes | 0.6487 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002752 | yes | no | no | yes | 0.6555 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002777 | yes | no | no | yes | 0.4717 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002779 | yes | no | no | yes | 0.4956 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002739 | yes | no | no | yes | 10.3472 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002736 | yes | no | no | yes | 10.5345 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002782 | yes | no | no | yes | 10.2957 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002814 | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_dtaas_drobotti_rmqfmu | yes | yes | yes | yes | 0.4528 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_flex_cell | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_dtaas_incubator_nurv_monitor_validation | yes | no | no | yes | 1.2100 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_mass_spring_damper | yes | yes | yes | yes | 0.7784 | - | - | - | yes |  |
| case_bench_fmu-002785 | yes | no | no | yes | 9.8656 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_dtaas_three_tank | no | no | no | no | - | - | - | - | - | ValueError: greedy_multirate_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-002811 | yes | no | no | yes | 10.2026 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_dtaas_water_tank_fi | yes | yes | yes | yes | 0.7266 | 24.460869 | 39.927241 | 28.498824 | no |  |
| case_dtaas_water_tank_fi_monitor | yes | no | no | yes | 1.7221 | 46.950023 | 76.525718 | 7.171120 | no |  |
| case_dtaas_mass_spring_damper_monitor | yes | yes | yes | yes | 4.9381 | 2.542997 | 11.671466 | 0.161485 | no |  |
| case_manual_002 | yes | no | no | yes | 1.9500 | 53.380339 | 106.289174 | 0.580178 | - |  |
| case_manual_003 | yes | yes | yes | yes | 0.6498 | - | - | - | yes |  |
| case_dtaas_water_tank_swap | yes | yes | yes | yes | 4.8371 | 16.434375 | 32.645291 | 9.272761 | no |  |
| case_manual_004 | yes | yes | yes | yes | 0.7810 | - | - | - | no |  |
| case_manual_005 | yes | yes | yes | yes | 0.4184 | - | - | - | no |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 54.1456 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_manual_001 | yes | yes | yes | yes | 11.6433 | 7.005093 | 14.367874 | 0.470085 | yes |  |
