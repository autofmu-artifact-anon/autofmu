# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_ablation_stage2_semantic_retrieval_only`
- bundle_name: `ablation_stage2_semantic_retrieval_only`
- cases_total: 151
- succeeded: 148
- failed: 3
- top1_hit_rate: 0.2905
- topk_hit_rate: 0.3176
- execution_success_rate: 0.8514
- mean_execution_time_seconds: 3.9928
- mae: 11455487.135913
- rmse: 18111149.408712
- nrmse: 0.702605
- trimmed_mae (drop top 0.5% cases): 1053.288276
- trimmed_rmse (drop top 0.5% cases): 5258.062730
- trimmed_nrmse (drop top 0.5% cases): 0.691883
- decision_accuracy (loose pass rate): 0.2889

## By Case Category

### `simple`

- cases_scored: 107
- top1_hit_rate: 0.4019
- topk_hit_rate: 0.4019
- execution_success_rate: 0.8692
- mean_execution_time_seconds: 4.1193
- mae: 15027623.324617
- rmse: 23758705.332867
- nrmse: 0.613380
- trimmed_mae (drop top 0.5% cases): 1380.287928
- trimmed_rmse (drop top 0.5% cases): 6908.627001
- trimmed_nrmse (drop top 0.5% cases): 0.598308
- decision_accuracy (loose pass rate): 0.3271

### `complex`

- cases_scored: 41
- top1_hit_rate: 0.0000
- topk_hit_rate: 0.0976
- execution_success_rate: 0.8049
- mean_execution_time_seconds: 3.6363
- mae: 15.910067
- rmse: 21.789871
- nrmse: 0.988741
- trimmed_mae (drop top 0.5% cases): 12.083875
- trimmed_rmse (drop top 0.5% cases): 16.970491
- trimmed_nrmse (drop top 0.5% cases): 0.952625
- decision_accuracy (loose pass rate): 0.1429

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001288 | yes | yes | yes | yes | 19.9650 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001523 | yes | no | no | yes | 6.4160 | 31.000000 | 31.000000 | 1.000000 | no |  |
| case_bench_fmu-001280 | yes | yes | yes | yes | 30.6901 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001284 | yes | no | no | no | 30.9618 | - | - | - | no |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 31.0741 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 0.8210 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001539 | yes | no | no | no | 0.7422 | - | - | - | no |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 0.9785 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 0.6296 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001555 | yes | yes | yes | yes | 0.7244 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001559 | yes | no | no | no | 0.4576 | - | - | - | no |  |
| case_bench_fmu-001563 | yes | yes | yes | yes | 0.7330 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 0.8058 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001569 | yes | no | no | yes | 0.7391 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001570 | yes | no | no | yes | 0.6209 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001571 | yes | no | no | yes | 0.3960 | 43.442641 | 43.442641 | 1.000000 | no |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 0.6738 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 0.6980 | 3.537296 | 4.657938 | 0.107220 | no |  |
| case_bench_fmu-001573 | yes | no | no | yes | 0.7713 | 16.532308 | 22.599527 | 3.665947 | no |  |
| case_bench_fmu-001575 | yes | no | no | yes | 0.6645 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001577 | yes | no | no | yes | 0.5299 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001576 | yes | no | no | yes | 0.8986 | 16.532308 | 22.599527 | 3.665947 | no |  |
| case_bench_fmu-001579 | yes | no | no | yes | 0.4574 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001578 | yes | no | no | yes | 0.9667 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001580 | yes | no | no | yes | 0.5878 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001581 | yes | no | no | yes | 0.7148 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001582 | yes | no | no | yes | 0.6193 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 0.7931 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001584 | yes | no | no | yes | 0.7397 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001586 | yes | no | no | yes | 0.6647 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001587 | yes | no | no | yes | 0.7336 | 16.532308 | 22.599527 | 3.665947 | no |  |
| case_bench_fmu-001588 | yes | no | no | yes | 0.6490 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001589 | yes | no | no | yes | 0.7899 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001591 | yes | no | no | yes | 0.4999 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001590 | yes | no | no | yes | 0.9837 | 16.532308 | 22.599527 | 3.665947 | no |  |
| case_bench_fmu-001592 | yes | no | no | yes | 0.6290 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001593 | yes | no | no | yes | 0.5313 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 0.4883 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001597 | yes | no | no | no | 0.3217 | - | - | - | no |  |
| case_bench_fmu-001598 | yes | no | no | no | 0.2918 | - | - | - | no |  |
| case_bench_fmu-001596 | yes | no | no | yes | 1.3327 | 123.043442 | 154.726206 | 1.000000 | no |  |
| case_bench_fmu-001600 | yes | no | no | yes | 0.9910 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-001605 | yes | no | no | yes | 0.9689 | 3.789213 | 5.172025 | 0.822161 | no |  |
| case_bench_fmu-001595 | yes | no | no | yes | 3.6989 | 121.475520 | 209.109758 | 1.000000 | no |  |
| case_bench_fmu-001613 | yes | no | no | yes | 0.8432 | 2.321500 | 3.909657 | 1.000000 | no |  |
| case_bench_fmu-001621 | yes | yes | yes | yes | 0.6731 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 0.2881 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001629 | yes | no | no | yes | 0.6362 | 57383.510544 | 303642.742476 | 1.000000 | no |  |
| case_bench_fmu-001661 | yes | no | no | no | 0.4504 | - | - | - | no |  |
| case_bench_fmu-001665 | yes | yes | yes | yes | 0.5245 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 0.3670 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 0.3636 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001750 | yes | no | no | no | 0.4232 | - | - | - | no |  |
| case_bench_fmu-001754 | yes | yes | yes | yes | 1.2693 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 1.3981 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001776 | yes | no | no | yes | 1.2403 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 1.0511 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001599 | yes | no | no | yes | 8.1703 | 2.261612 | 2.261732 | 1.000000 | no |  |
| case_bench_fmu-001934 | yes | no | no | no | 1.0589 | - | - | - | no |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 1.1261 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 0.8996 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002019 | yes | no | no | yes | 0.6220 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002241 | yes | no | no | yes | 0.8177 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002272 | yes | no | no | no | 0.5312 | - | - | - | no |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 0.8494 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 0.7972 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 0.5162 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 0.8652 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002292 | yes | no | no | no | 0.4256 | - | - | - | no |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 0.8197 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 1.0842 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002303 | yes | no | no | yes | 0.4813 | 18.146101 | 24.643205 | 3.809219 | no |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 1.3307 | 0.013050 | 0.025081 | 0.000572 | yes |  |
| case_bench_fmu-002306 | yes | no | no | yes | 0.5540 | 18.146101 | 24.643205 | 3.809219 | no |  |
| case_bench_fmu-002305 | yes | yes | yes | yes | 1.1281 | 0.013050 | 0.025081 | 0.000572 | yes |  |
| case_bench_fmu-002308 | yes | no | no | yes | 0.4743 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002309 | yes | no | no | yes | 0.6974 | 18.146101 | 24.643205 | 3.809219 | no |  |
| case_bench_fmu-001524 | yes | no | no | yes | 30.6689 | 4.307538 | 4.688875 | 1.000000 | no |  |
| case_bench_fmu-002311 | yes | no | no | yes | 0.7734 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002312 | yes | no | no | yes | 0.4941 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002310 | yes | no | no | yes | 10.6652 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002314 | yes | no | no | yes | 0.5268 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002315 | yes | no | no | yes | 0.4387 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002316 | yes | no | no | yes | 11.5945 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002317 | yes | no | no | yes | 0.6032 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-002319 | yes | no | no | yes | 0.5644 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002320 | yes | no | no | yes | 0.3589 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 38.2564 | 3.318020 | 4.439928 | 0.102385 | no |  |
| case_bench_fmu-002322 | yes | no | no | yes | 0.4658 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002323 | yes | no | no | yes | 0.6770 | 18.146101 | 24.643205 | 3.809219 | no |  |
| case_bench_fmu-002321 | yes | no | no | yes | 14.1819 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002325 | yes | no | no | yes | 0.6388 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002326 | yes | no | no | yes | 1.1328 | 18.146101 | 24.643205 | 3.809219 | no |  |
| case_bench_fmu-002307 | yes | yes | yes | yes | 43.5733 | 3.318020 | 4.439928 | 0.102385 | no |  |
| case_bench_fmu-002336 | yes | no | no | yes | 1.2004 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002340 | yes | no | no | yes | 0.9987 | 138.192193 | 238.064833 | 1.000000 | no |  |
| case_bench_fmu-002341 | yes | no | no | yes | 1.1884 | 122.713385 | 154.432115 | 1.000000 | no |  |
| case_bench_fmu-002342 | yes | no | no | no | 0.9447 | - | - | - | no |  |
| case_bench_fmu-002343 | yes | no | no | no | 0.8259 | - | - | - | no |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 43.1645 | 3.319846 | 4.440635 | 0.102702 | no |  |
| case_bench_fmu-002345 | yes | no | no | yes | 0.6967 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-002344 | yes | no | no | yes | 1.0858 | 2.260368 | 2.260482 | 1.000000 | no |  |
| case_bench_fmu-002350 | yes | no | no | yes | 0.8716 | 3.000000 | 4.123106 | 1.000000 | no |  |
| case_bench_fmu-002349 | yes | no | no | yes | 1.3664 | 1397441982.700000 | 2208924002.272586 | 1.000000 | no |  |
| case_bench_fmu-002352 | yes | no | no | yes | 1.3244 | 10963.833333 | 26750.263566 | 1.000000 | no |  |
| case_bench_fmu-002351 | yes | no | no | yes | 1.7160 | 26.400000 | 80.643661 | 1.000000 | no |  |
| case_bench_fmu-002368 | yes | no | no | yes | 1.2456 | 2.321500 | 3.909657 | 1.000000 | no |  |
| case_bench_fmu-002360 | yes | no | no | yes | 1.4256 | 3.789213 | 5.172025 | 0.822161 | no |  |
| case_bench_fmu-002384 | yes | no | no | yes | 1.1879 | 57383.510544 | 303642.742476 | 1.000000 | no |  |
| case_bench_fmu-002376 | yes | yes | yes | yes | 1.2528 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 0.6406 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | no | no | no | 0.7406 | - | - | - | no |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 0.9273 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 1.2942 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002452 | yes | no | no | yes | 0.8857 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 0.7070 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | no | no | no | 0.8005 | - | - | - | no |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 1.1488 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 0.9221 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002702 | yes | no | no | yes | 1.1295 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002704 | yes | no | no | yes | 0.9140 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002707 | yes | no | no | yes | 0.8063 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002710 | yes | no | no | yes | 0.6479 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002736 | yes | no | no | no | 0.8668 | - | - | - | no |  |
| case_bench_fmu-002739 | yes | no | no | no | 0.8483 | - | - | - | no |  |
| case_bench_fmu-002744 | yes | no | no | yes | 0.6904 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002746 | yes | no | no | yes | 0.9379 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002749 | yes | no | no | yes | 0.5289 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002752 | yes | no | no | yes | 0.5045 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002777 | yes | no | no | yes | 0.5464 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002782 | yes | no | no | no | 1.0052 | - | - | - | no |  |
| case_bench_fmu-002779 | yes | no | no | yes | 1.2800 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 30.0340 | 3.319846 | 4.440635 | 0.102702 | no |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 27.5571 | 3.319846 | 4.440635 | 0.102702 | no |  |
| case_bench_fmu-002814 | yes | no | no | no | 13.9190 | - | - | - | no |  |
| case_bench_fmu-002811 | yes | no | no | no | 26.0199 | - | - | - | no |  |
| case_bench_fmu-002785 | yes | no | no | no | 30.4035 | - | - | - | no |  |
| case_dtaas_mass_spring_damper | yes | no | yes | yes | 0.6288 | - | - | - | yes |  |
| case_dtaas_mass_spring_damper_monitor | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_three_tank | yes | no | no | yes | 0.3032 | - | - | - | - |  |
| case_dtaas_water_tank_fi | yes | no | yes | no | 0.3194 | - | - | - | no |  |
| case_dtaas_water_tank_fi_monitor | yes | no | no | no | 0.4667 | - | - | - | no |  |
| case_dtaas_water_tank_swap | yes | no | no | yes | 0.8802 | 0.358839 | 0.557485 | 0.354538 | no |  |
| case_dtaas_drobotti_rmqfmu | yes | no | no | yes | 30.3614 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_manual_002 | yes | no | no | yes | 1.7360 | 84.584142 | 156.732509 | 0.727091 | - |  |
| case_manual_003 | yes | no | yes | yes | 0.8249 | - | - | - | no |  |
| case_manual_001 | yes | no | no | yes | 3.7997 | 9.693295 | 17.633529 | 0.591859 | yes |  |
| case_manual_005 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_manual_004 | yes | no | yes | yes | 0.8646 | - | - | - | - |  |
| case_dtaas_flex_cell | yes | no | no | yes | 30.6926 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_incubator_nurv_monitor_validation | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
