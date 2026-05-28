# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_ablation_stage1_top1_llm`
- bundle_name: `ablation_stage1_top1_llm`
- cases_total: 151
- succeeded: 135
- failed: 16
- top1_hit_rate: 0.7778
- topk_hit_rate: 0.7778
- execution_success_rate: 0.9185
- mean_execution_time_seconds: 29.9866
- mae: 4.604865
- rmse: 5.304643
- nrmse: 0.275175
- trimmed_mae (drop top 0.5% cases): 4.281217
- trimmed_rmse (drop top 0.5% cases): 4.909695
- trimmed_nrmse (drop top 0.5% cases): 0.269135
- decision_accuracy (loose pass rate): 0.6591

## By Case Category

### `simple`

- cases_scored: 101
- top1_hit_rate: 0.7921
- topk_hit_rate: 0.7921
- execution_success_rate: 0.9010
- mean_execution_time_seconds: 28.5272
- mae: 5.575370
- rmse: 6.190743
- nrmse: 0.230294
- trimmed_mae (drop top 0.5% cases): 5.154623
- trimmed_rmse (drop top 0.5% cases): 5.673992
- trimmed_nrmse (drop top 0.5% cases): 0.221742
- decision_accuracy (loose pass rate): 0.6040

### `complex`

- cases_scored: 34
- top1_hit_rate: 0.7353
- topk_hit_rate: 0.7353
- execution_success_rate: 0.9706
- mean_execution_time_seconds: 34.0109
- mae: 1.660997
- rmse: 2.616805
- nrmse: 0.411314
- trimmed_mae (drop top 0.5% cases): 1.499545
- trimmed_rmse (drop top 0.5% cases): 2.044308
- trimmed_nrmse (drop top 0.5% cases): 0.391014
- decision_accuracy (loose pass rate): 0.8387

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001292 | yes | yes | yes | yes | 21.8727 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001288 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001280 | yes | yes | yes | yes | 32.7280 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 32.8422 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001523 | yes | yes | yes | no | 30.5461 | - | - | - | no |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 24.2004 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001524 | yes | yes | yes | no | 31.6046 | - | - | - | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 30.4687 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 21.4402 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 23.7372 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001555 | yes | yes | yes | yes | 31.4978 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 31.6708 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 21.4013 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001563 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001569 | yes | yes | yes | yes | 24.7133 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 29.4932 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001571 | yes | no | no | no | 26.2598 | - | - | - | no |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 28.9843 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001574 | yes | no | no | yes | 20.3120 | 43.442641 | 43.442641 | 1.000000 | no |  |
| case_bench_fmu-001573 | yes | no | no | yes | 32.3207 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001575 | yes | yes | yes | yes | 30.6411 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001576 | yes | no | no | yes | 32.5004 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001578 | yes | yes | yes | yes | 23.8699 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001577 | yes | yes | yes | yes | 30.7207 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001579 | yes | yes | yes | yes | 29.7542 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001580 | yes | no | no | no | 25.5234 | - | - | - | no |  |
| case_bench_fmu-001581 | yes | yes | yes | yes | 21.9409 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001582 | yes | yes | yes | yes | 30.5315 | 0.048521 | 0.070131 | 0.019551 | yes |  |
| case_bench_fmu-001584 | yes | yes | yes | yes | 20.4649 | 0.005467 | 0.010411 | 0.000237 | yes |  |
| case_bench_fmu-001586 | yes | yes | yes | yes | 17.1233 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 30.6130 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001588 | yes | no | no | yes | 17.6476 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001587 | yes | yes | yes | yes | 27.9801 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001589 | yes | yes | yes | yes | 24.9822 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001591 | yes | no | no | yes | 21.4447 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001590 | yes | no | no | yes | 32.5623 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001592 | yes | yes | yes | yes | 18.0049 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 30.5576 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 31.1724 | - | - | - | no |  |
| case_bench_fmu-001594 | yes | no | no | yes | 32.5785 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001597 | yes | yes | yes | yes | 30.7660 | 0.003834 | 0.007104 | 0.005028 | yes |  |
| case_bench_fmu-001598 | yes | yes | yes | yes | 26.0493 | 0.012638 | 0.015612 | 0.005416 | yes |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 63.4119 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_bench_fmu-001600 | yes | yes | yes | yes | 17.9840 | 0.000000 | 0.000000 | 0.001528 | yes |  |
| case_bench_fmu-001599 | yes | yes | yes | yes | 48.8077 | 0.004166 | 0.009022 | 0.003976 | yes |  |
| case_bench_fmu-001605 | yes | yes | yes | yes | 30.8264 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001613 | yes | yes | yes | yes | 30.9995 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001621 | yes | no | no | no | 30.8732 | - | - | - | no |  |
| case_bench_fmu-001629 | yes | yes | yes | yes | 31.2458 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 30.9484 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 31.1713 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001665 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001669 | yes | yes | yes | yes | 21.0868 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 16.2550 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 30.8256 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 31.1156 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001754 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-001930 | yes | yes | yes | yes | 30.5161 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001776 | yes | yes | yes | yes | 32.2728 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 30.5099 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 30.7908 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 23.1558 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002019 | yes | yes | yes | yes | 32.2437 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002241 | yes | yes | yes | yes | 32.2827 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 30.7988 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 30.5170 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 30.6563 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 31.0961 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 30.8796 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 30.4834 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 18.0259 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 30.6147 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 30.6056 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002303 | yes | no | no | yes | 32.3937 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002304 | yes | no | no | yes | 38.0244 | 43.364979 | 43.364979 | 1.000000 | no |  |
| case_bench_fmu-002305 | yes | no | no | yes | 34.2782 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002306 | yes | no | no | yes | 32.7529 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002307 | yes | no | no | yes | 21.6349 | 43.364979 | 43.364979 | 1.000000 | no |  |
| case_bench_fmu-002310 | yes | no | no | yes | 22.7538 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002308 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-002309 | yes | no | no | yes | 32.5064 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002311 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_bench_fmu-002312 | yes | yes | yes | yes | 30.5205 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002314 | yes | yes | yes | yes | 30.8497 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 41.1362 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002315 | yes | yes | yes | yes | 30.5003 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002317 | yes | yes | yes | yes | 31.7693 | 0.014467 | 0.027770 | 0.000633 | yes |  |
| case_bench_fmu-002316 | yes | yes | yes | yes | 38.0794 | 0.040723 | 0.053081 | 0.001228 | yes |  |
| case_bench_fmu-002319 | yes | yes | yes | yes | 30.7662 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 30.5345 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002321 | yes | no | no | yes | 26.3590 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002322 | yes | yes | yes | yes | 30.8724 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002324 | yes | no | no | yes | 33.0552 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002323 | yes | no | no | yes | 33.5252 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002325 | yes | yes | yes | yes | 31.2224 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002326 | yes | no | no | yes | 32.6726 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002327 | yes | no | no | yes | 26.9030 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002336 | yes | yes | yes | yes | 32.2286 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002340 | yes | yes | yes | yes | 30.7622 | 6.855169 | 52.698386 | 0.074496 | no |  |
| case_bench_fmu-002342 | yes | yes | yes | yes | 31.4405 | 0.006604 | 0.014665 | 0.013089 | yes |  |
| case_bench_fmu-002341 | yes | yes | yes | yes | 32.3259 | 0.001058 | 0.051129 | 0.000466 | yes |  |
| case_bench_fmu-002343 | yes | yes | yes | yes | 30.6995 | 0.001768 | 0.002460 | 0.000856 | yes |  |
| case_bench_fmu-002345 | yes | yes | yes | yes | 13.6181 | 0.000000 | 0.000001 | 0.027639 | yes |  |
| case_bench_fmu-002344 | yes | yes | yes | yes | 30.9765 | 0.001998 | 0.003749 | 0.001646 | yes |  |
| case_bench_fmu-002349 | yes | yes | yes | no | 30.6418 | - | - | - | no |  |
| case_bench_fmu-002350 | yes | yes | yes | no | 30.5573 | - | - | - | no |  |
| case_bench_fmu-002351 | yes | yes | yes | no | 27.7929 | - | - | - | no |  |
| case_bench_fmu-002352 | yes | yes | yes | no | 30.5768 | - | - | - | no |  |
| case_bench_fmu-002360 | yes | yes | yes | yes | 30.8051 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002368 | yes | yes | yes | yes | 30.9296 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002376 | yes | no | no | no | 30.8269 | - | - | - | no |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 31.0845 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 30.5089 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 30.5030 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 17.1361 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 30.6901 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002452 | yes | yes | yes | yes | 32.4703 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 30.3181 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 30.4987 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 30.6919 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 17.7624 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002702 | yes | yes | yes | yes | 30.6061 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002704 | yes | no | no | yes | 32.6563 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002707 | yes | yes | yes | yes | 30.7374 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002710 | yes | yes | yes | yes | 30.6287 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002736 | yes | yes | yes | yes | 30.5987 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002744 | yes | yes | yes | yes | 31.0550 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002739 | yes | yes | yes | yes | 31.0947 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002746 | yes | no | no | yes | 32.6607 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002749 | yes | yes | yes | yes | 30.5924 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002752 | yes | yes | yes | yes | 31.0953 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002777 | yes | yes | yes | yes | 31.1817 | 2.063160 | 3.105869 | 0.570313 | yes |  |
| case_bench_fmu-002779 | yes | yes | yes | yes | 30.7438 | 2.063364 | 3.103850 | 0.570646 | yes |  |
| case_bench_fmu-002782 | yes | yes | yes | yes | 30.5835 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002785 | yes | yes | yes | yes | 31.0635 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002811 | yes | yes | yes | yes | 31.0383 | 2.063036 | 3.105860 | 0.570296 | yes |  |
| case_bench_fmu-002814 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_drobotti_rmqfmu | yes | no | no | yes | 31.0343 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_incubator_nurv_monitor_validation | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_flex_cell | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_mass_spring_damper | yes | no | no | yes | 31.3245 | - | - | - | - |  |
| case_dtaas_water_tank_fi | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_three_tank | yes | no | no | yes | 33.0172 | - | - | - | yes |  |
| case_dtaas_water_tank_fi_monitor | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_manual_001 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_water_tank_swap | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_manual_002 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_dtaas_mass_spring_damper_monitor | yes | no | no | yes | 87.8013 | 6.343102 | 19.219208 | 0.834956 | no |  |
| case_manual_004 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
| case_manual_003 | yes | no | no | yes | 31.7204 | - | - | - | no |  |
| case_manual_005 | no | no | no | no | - | - | - | - | - | ValueError: compose() received empty selected_fmus |
