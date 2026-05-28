# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_ablation_stage2_greedy_hybrid`
- bundle_name: `ablation_stage2_greedy_hybrid`
- cases_total: 151
- succeeded: 151
- failed: 0
- top1_hit_rate: 0.4503
- topk_hit_rate: 0.5033
- execution_success_rate: 0.9007
- mean_execution_time_seconds: 4.5448
- mae: 10668027.179719
- rmse: 16864548.716159
- nrmse: 0.500160
- trimmed_mae (drop top 0.5% cases): 535.214178
- trimmed_rmse (drop top 0.5% cases): 2552.919571
- trimmed_nrmse (drop top 0.5% cases): 0.496315
- decision_accuracy (loose pass rate): 0.3723

## By Case Category

### `simple`

- cases_scored: 107
- top1_hit_rate: 0.5701
- topk_hit_rate: 0.5701
- execution_success_rate: 0.9346
- mean_execution_time_seconds: 4.3354
- mae: 13975112.777284
- rmse: 22092554.669541
- nrmse: 0.453140
- trimmed_mae (drop top 0.5% cases): 699.949782
- trimmed_rmse (drop top 0.5% cases): 3348.128096
- trimmed_nrmse (drop top 0.5% cases): 0.447617
- decision_accuracy (loose pass rate): 0.3832

### `complex`

- cases_scored: 44
- top1_hit_rate: 0.1591
- topk_hit_rate: 0.3409
- execution_success_rate: 0.8182
- mean_execution_time_seconds: 5.1265
- mae: 9.123056
- rmse: 13.382667
- nrmse: 0.651836
- trimmed_mae (drop top 0.5% cases): 5.336712
- trimmed_rmse (drop top 0.5% cases): 8.604339
- trimmed_nrmse (drop top 0.5% cases): 0.640231
- decision_accuracy (loose pass rate): 0.3333

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001280 | yes | yes | yes | yes | 18.7679 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 30.9118 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001288 | yes | yes | yes | yes | 31.1052 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 31.1344 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001524 | yes | no | no | yes | 0.5679 | 4.307538 | 4.688875 | 1.000000 | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 0.5825 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 0.9744 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 0.6537 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 0.9314 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001555 | yes | yes | yes | yes | 0.5310 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 0.7043 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001563 | yes | yes | yes | yes | 0.9306 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 0.8842 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001569 | yes | no | no | yes | 0.6618 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 0.4980 | 0.124852 | 0.199641 | 0.042775 | yes |  |
| case_bench_fmu-001571 | yes | no | no | yes | 0.5889 | 43.442641 | 43.442641 | 1.000000 | no |  |
| case_bench_fmu-001573 | yes | yes | yes | yes | 0.6952 | 0.004301 | 0.005980 | 0.001660 | yes |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 1.0032 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 0.7781 | 3.537296 | 4.657938 | 0.107220 | no |  |
| case_bench_fmu-001575 | yes | no | no | yes | 0.6899 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001576 | yes | yes | yes | yes | 0.7282 | 0.014731 | 0.027541 | 0.007628 | yes |  |
| case_bench_fmu-001577 | yes | no | no | yes | 0.6898 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001578 | yes | no | no | yes | 0.6806 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001579 | yes | no | no | yes | 0.4799 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001580 | yes | no | no | yes | 0.5923 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001582 | yes | no | no | yes | 0.5617 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001581 | yes | no | no | yes | 0.7842 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 0.6982 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001586 | yes | no | no | yes | 0.5584 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001584 | yes | no | no | yes | 0.7806 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001587 | yes | yes | yes | yes | 0.6959 | 0.004301 | 0.005980 | 0.001660 | yes |  |
| case_bench_fmu-001588 | yes | no | no | yes | 0.5216 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001589 | yes | no | no | yes | 0.6826 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001590 | yes | yes | yes | yes | 0.6245 | 0.004301 | 0.005980 | 0.001660 | yes |  |
| case_bench_fmu-001591 | yes | no | no | yes | 0.6038 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001592 | yes | no | no | yes | 0.6184 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 0.6396 | 0.124852 | 0.199641 | 0.042775 | yes |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 0.7912 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 0.7430 | - | - | - | no |  |
| case_bench_fmu-001597 | yes | no | no | yes | 0.4580 | 0.999492 | 0.999492 | 1.000000 | no |  |
| case_bench_fmu-001598 | yes | no | no | no | 0.1935 | - | - | - | no |  |
| case_bench_fmu-001600 | yes | no | no | yes | 0.6799 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-001605 | yes | no | no | yes | 0.7985 | 3.789213 | 5.172025 | 0.822161 | no |  |
| case_bench_fmu-001613 | yes | no | no | yes | 0.7634 | 2.321500 | 3.909657 | 1.000000 | no |  |
| case_bench_fmu-001621 | yes | no | no | yes | 1.1312 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-001629 | yes | no | no | yes | 0.3668 | 57383.510544 | 303642.742476 | 1.000000 | no |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 0.2400 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 0.1972 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001665 | yes | yes | yes | yes | 0.5202 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 0.4525 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 0.3642 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 0.8764 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001754 | yes | yes | yes | yes | 0.5587 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 0.8543 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001776 | yes | no | no | yes | 0.5581 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-001599 | yes | no | no | yes | 8.4830 | 2.261612 | 2.261732 | 1.000000 | no |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 0.4881 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 0.5767 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001523 | yes | no | no | yes | 31.1577 | 31.000000 | 31.000000 | 1.000000 | no |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 1.0717 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 1.4171 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002019 | yes | no | no | yes | 0.7473 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002241 | yes | no | no | yes | 0.7439 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 0.7240 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 0.6030 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 0.6676 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 0.5174 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 0.9901 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 0.3709 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 0.7474 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 0.9993 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002303 | yes | yes | yes | yes | 0.6779 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 1.4575 | 0.013050 | 0.025081 | 0.000572 | yes |  |
| case_bench_fmu-002306 | yes | yes | yes | yes | 0.5608 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002305 | yes | yes | yes | yes | 1.4128 | 0.013050 | 0.025081 | 0.000572 | yes |  |
| case_bench_fmu-002308 | yes | no | no | no | 1.0472 | - | - | - | no |  |
| case_bench_fmu-002309 | yes | yes | yes | yes | 0.5734 | 0.125368 | 0.207145 | 0.040082 | yes |  |
| case_bench_fmu-002310 | yes | no | no | yes | 10.6994 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002311 | yes | no | no | no | 0.9187 | - | - | - | no |  |
| case_bench_fmu-002312 | yes | no | no | yes | 0.3917 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 44.5313 | 3.318020 | 4.439928 | 0.102385 | no |  |
| case_bench_fmu-002314 | yes | no | no | yes | 1.0285 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002315 | yes | no | no | yes | 0.4441 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002307 | yes | yes | yes | yes | 44.8866 | 3.318020 | 4.439928 | 0.102385 | no |  |
| case_bench_fmu-002317 | yes | no | no | yes | 0.6357 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-002319 | yes | no | no | yes | 0.7181 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 0.5303 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 63.0698 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_bench_fmu-002322 | yes | no | no | yes | 0.6637 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002323 | yes | yes | yes | yes | 0.7747 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 39.0815 | 3.319846 | 4.440635 | 0.102702 | no |  |
| case_bench_fmu-002325 | yes | no | no | yes | 0.5613 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002326 | yes | yes | yes | yes | 0.5335 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002316 | yes | no | no | yes | 10.3551 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002321 | yes | no | no | yes | 9.9202 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 25.4807 | 3.319846 | 4.440635 | 0.102702 | no |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 22.0132 | 3.319846 | 4.440635 | 0.102702 | no |  |
| case_bench_fmu-002340 | yes | no | no | yes | 20.8539 | 138.192193 | 238.064833 | 1.000000 | no |  |
| case_bench_fmu-002336 | yes | no | no | yes | 30.4449 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002344 | yes | no | no | yes | 0.3774 | 2.260368 | 2.260482 | 1.000000 | no |  |
| case_bench_fmu-002345 | yes | no | no | yes | 0.2060 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-002349 | yes | no | no | yes | 0.5127 | 1397441982.700000 | 2208924002.272586 | 1.000000 | no |  |
| case_bench_fmu-002350 | yes | no | no | yes | 0.4500 | 3.000000 | 4.123106 | 1.000000 | no |  |
| case_bench_fmu-002351 | yes | yes | yes | no | 0.2798 | - | - | - | no |  |
| case_bench_fmu-002352 | yes | no | no | yes | 0.4360 | 10963.833333 | 26750.263566 | 1.000000 | no |  |
| case_bench_fmu-002360 | yes | no | no | yes | 0.4860 | 3.789213 | 5.172025 | 0.822161 | no |  |
| case_bench_fmu-002368 | yes | no | no | yes | 0.4555 | 2.321500 | 3.909657 | 1.000000 | no |  |
| case_bench_fmu-002376 | yes | no | no | yes | 0.6888 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 0.7825 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 0.1739 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 0.1813 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 0.3848 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 0.2573 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002452 | yes | no | no | yes | 0.2909 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 0.1956 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 0.2032 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 0.3326 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 0.4937 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002342 | yes | no | no | no | 16.4740 | - | - | - | no |  |
| case_bench_fmu-002702 | yes | no | no | yes | 0.4361 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002704 | yes | no | no | yes | 0.4878 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002707 | yes | no | no | yes | 0.3634 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002710 | yes | no | no | yes | 0.3850 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002736 | yes | no | no | no | 0.4607 | - | - | - | no |  |
| case_bench_fmu-002739 | yes | no | no | no | 0.3860 | - | - | - | no |  |
| case_bench_fmu-002744 | yes | no | no | yes | 0.4881 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002746 | yes | no | no | yes | 0.5003 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002749 | yes | no | no | yes | 0.4928 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002752 | yes | no | no | yes | 0.4250 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002777 | yes | no | no | yes | 0.3192 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002779 | yes | no | no | yes | 0.4915 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002782 | yes | no | no | no | 0.4687 | - | - | - | no |  |
| case_bench_fmu-002785 | yes | no | no | no | 0.4618 | - | - | - | no |  |
| case_bench_fmu-002811 | yes | no | no | no | 0.5259 | - | - | - | no |  |
| case_bench_fmu-002814 | yes | no | no | no | 0.6492 | - | - | - | no |  |
| case_dtaas_drobotti_rmqfmu | yes | no | yes | yes | 0.5310 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_flex_cell | yes | no | yes | yes | 1.1168 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_mass_spring_damper | yes | no | yes | yes | 0.7043 | - | - | - | yes |  |
| case_dtaas_incubator_nurv_monitor_validation | yes | no | no | yes | 4.1745 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_three_tank | yes | no | no | yes | 0.3433 | - | - | - | - |  |
| case_dtaas_water_tank_fi | yes | no | yes | no | 0.4984 | - | - | - | no |  |
| case_dtaas_mass_spring_damper_monitor | yes | no | no | yes | 3.2676 | 2.812056 | 11.686825 | 0.362329 | no |  |
| case_dtaas_water_tank_fi_monitor | yes | no | no | no | 0.9485 | - | - | - | no |  |
| case_dtaas_water_tank_swap | yes | no | yes | yes | 1.7189 | 0.358839 | 0.557485 | 0.354538 | no |  |
| case_manual_002 | yes | no | no | yes | 2.9514 | 84.584142 | 156.732509 | 0.727091 | - |  |
| case_bench_fmu-002341 | yes | no | no | yes | 31.9475 | 122.713385 | 154.432115 | 1.000000 | no |  |
| case_manual_001 | yes | no | yes | yes | 4.7251 | 9.554685 | 20.455818 | 0.706610 | - |  |
| case_manual_003 | yes | no | yes | yes | 1.4582 | - | - | - | no |  |
| case_bench_fmu-002343 | yes | no | no | no | 31.1404 | - | - | - | no |  |
| case_manual_004 | yes | no | yes | yes | 1.5218 | - | - | - | - |  |
| case_manual_005 | yes | yes | yes | yes | 25.5817 | - | - | - | no |  |
