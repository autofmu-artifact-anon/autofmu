# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_baseline_b1_rule_sequential`
- bundle_name: `baseline_b1_rule_sequential`
- cases_total: 151
- succeeded: 146
- failed: 5
- top1_hit_rate: 0.3836
- topk_hit_rate: 0.3836
- execution_success_rate: 0.9452
- mean_execution_time_seconds: 1.0926
- mae: 10507606.259586
- rmse: 16610947.010051
- nrmse: 0.617791
- trimmed_mae (drop top 0.5% cases): 527.650189
- trimmed_rmse (drop top 0.5% cases): 2514.773214
- trimmed_nrmse (drop top 0.5% cases): 0.614896
- decision_accuracy (loose pass rate): 0.2937

## By Case Category

### `simple`

- cases_scored: 107
- top1_hit_rate: 0.4673
- topk_hit_rate: 0.4673
- execution_success_rate: 0.9439
- mean_execution_time_seconds: 0.3193
- mae: 13836745.839203
- rmse: 21873817.066241
- nrmse: 0.561221
- trimmed_mae (drop top 0.5% cases): 693.470595
- trimmed_rmse (drop top 0.5% cases): 3315.214177
- trimmed_nrmse (drop top 0.5% cases): 0.556834
- decision_accuracy (loose pass rate): 0.2804

### `complex`

- cases_scored: 39
- top1_hit_rate: 0.1538
- topk_hit_rate: 0.1538
- execution_success_rate: 0.9487
- mean_execution_time_seconds: 3.2036
- mae: 9.461419
- rmse: 13.395202
- nrmse: 0.796340
- trimmed_mae (drop top 0.5% cases): 5.808130
- trimmed_rmse (drop top 0.5% cases): 8.771418
- trimmed_nrmse (drop top 0.5% cases): 0.789770
- decision_accuracy (loose pass rate): 0.3684

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001292 | yes | yes | yes | yes | 0.2057 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001280 | yes | yes | yes | yes | 0.2353 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001288 | yes | no | no | yes | 0.2209 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 0.2447 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001523 | yes | no | no | yes | 0.1939 | 31.000000 | 31.000000 | 1.000000 | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 0.2159 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001535 | yes | no | no | yes | 0.2493 | 10.000000 | 10.000000 | 1.000000 | no |  |
| case_bench_fmu-001524 | yes | no | no | yes | 0.3349 | 4.307538 | 4.688875 | 1.000000 | no |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 0.2858 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001543 | yes | no | no | yes | 0.2681 | 0.999955 | 0.999955 | 1.000000 | no |  |
| case_bench_fmu-001555 | yes | yes | yes | yes | 0.2113 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 0.2022 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001563 | yes | no | no | yes | 0.1669 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001569 | yes | no | no | yes | 0.2360 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001571 | yes | no | no | yes | 0.1016 | 43.442641 | 43.442641 | 1.000000 | no |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 0.2644 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 0.3417 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 0.2923 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001573 | yes | yes | yes | yes | 0.2806 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001575 | yes | no | no | yes | 0.2221 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 0.3755 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001577 | yes | no | no | yes | 0.2562 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001576 | yes | yes | yes | yes | 0.2949 | 0.008421 | 0.015823 | 0.004281 | yes |  |
| case_bench_fmu-001578 | yes | no | no | yes | 0.2298 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001579 | yes | no | no | yes | 0.2319 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001580 | yes | no | no | yes | 0.1429 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001581 | yes | no | no | yes | 0.1370 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001582 | yes | no | no | yes | 0.1810 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 0.1677 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001584 | yes | no | no | yes | 0.1453 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001586 | yes | no | no | yes | 0.1778 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001588 | yes | no | no | yes | 0.1318 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001587 | yes | yes | yes | yes | 0.2200 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001589 | yes | no | no | yes | 0.1490 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001590 | yes | yes | yes | yes | 0.2253 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001591 | yes | no | no | yes | 0.1700 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001592 | yes | no | no | yes | 0.1491 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 0.1855 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001597 | yes | no | no | yes | 0.4799 | 0.999492 | 0.999492 | 1.000000 | no |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 0.5733 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001598 | yes | no | no | yes | 0.6175 | 2.882502 | 2.882502 | 1.000000 | no |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 1.2667 | - | - | - | no |  |
| case_bench_fmu-001599 | yes | no | no | yes | 0.8166 | 2.261612 | 2.261732 | 1.000000 | no |  |
| case_bench_fmu-001600 | yes | no | no | yes | 0.4688 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-001605 | yes | no | no | yes | 0.8925 | 3.145849 | 4.879145 | 0.681758 | no |  |
| case_bench_fmu-001613 | yes | no | no | yes | 1.0436 | 2.321500 | 3.909657 | 1.000000 | no |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 0.8999 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001629 | yes | no | no | yes | 1.2962 | 57383.510544 | 303642.742476 | 1.000000 | no |  |
| case_bench_fmu-001621 | yes | no | no | no | 2.0380 | - | - | - | no |  |
| case_bench_fmu-001665 | yes | no | no | yes | 0.3300 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 0.5419 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 0.5280 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 0.3624 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 0.4437 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001754 | yes | no | no | yes | 0.2397 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001776 | yes | no | no | yes | 0.1557 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 0.2864 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 0.1652 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 0.2282 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001938 | yes | no | no | yes | 0.2203 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 0.2933 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002019 | yes | no | no | yes | 0.1792 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002241 | yes | no | no | yes | 0.1688 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002268 | yes | no | no | yes | 0.1342 | 10.000000 | 10.000000 | 1.000000 | no |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 0.1875 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 0.2907 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 0.1935 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 0.3536 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002296 | yes | no | no | yes | 0.1700 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 0.1762 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 0.2372 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002303 | yes | yes | yes | yes | 0.2347 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 0.3537 | 0.009348 | 0.017965 | 0.000410 | yes |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 0.3056 | 2.425431 | 4.023003 | 0.092771 | no |  |
| case_bench_fmu-002305 | yes | yes | yes | yes | 0.3815 | 0.009348 | 0.017965 | 0.000410 | yes |  |
| case_bench_fmu-002306 | yes | yes | yes | yes | 0.3520 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-002307 | yes | yes | yes | yes | 0.3997 | 2.425431 | 4.023003 | 0.092771 | no |  |
| case_bench_fmu-002310 | yes | no | no | yes | 0.2745 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002309 | yes | yes | yes | yes | 0.3507 | 0.128116 | 0.206620 | 0.040742 | yes |  |
| case_bench_fmu-002312 | yes | no | no | yes | 0.2966 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 0.2977 | 2.422908 | 4.012993 | 0.092812 | no |  |
| case_bench_fmu-002314 | yes | no | no | yes | 0.1643 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002308 | yes | no | no | no | 1.4964 | - | - | - | no |  |
| case_bench_fmu-002315 | yes | no | no | yes | 0.1936 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002316 | yes | no | no | yes | 0.1903 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002317 | yes | no | no | yes | 0.2080 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-002319 | yes | no | no | yes | 0.1974 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 0.2660 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-002311 | yes | no | no | no | 1.6140 | - | - | - | no |  |
| case_bench_fmu-002321 | yes | no | no | yes | 0.2089 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002322 | yes | no | no | yes | 0.2121 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002325 | yes | no | no | yes | 0.1650 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002323 | yes | yes | yes | yes | 0.3302 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 0.3264 | 2.422908 | 4.012993 | 0.092812 | no |  |
| case_bench_fmu-002336 | yes | no | no | yes | 0.1887 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002326 | yes | yes | yes | yes | 0.2550 | 0.129498 | 0.203655 | 0.041262 | yes |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 0.2666 | 2.422908 | 4.012993 | 0.092812 | no |  |
| case_bench_fmu-002340 | yes | no | no | yes | 0.1518 | 138.192193 | 238.064833 | 1.000000 | no |  |
| case_bench_fmu-002341 | yes | no | no | yes | 0.2027 | 122.713385 | 154.432115 | 1.000000 | no |  |
| case_bench_fmu-002342 | yes | no | no | yes | 0.1528 | 0.999265 | 0.999266 | 1.000000 | no |  |
| case_bench_fmu-002343 | yes | no | no | yes | 0.1692 | 2.874242 | 2.874242 | 1.000000 | no |  |
| case_bench_fmu-002345 | yes | no | no | yes | 0.2422 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-002344 | yes | no | no | yes | 0.3035 | 2.260368 | 2.260482 | 1.000000 | no |  |
| case_bench_fmu-002349 | yes | no | no | yes | 0.4347 | 1397441982.700000 | 2208924002.272586 | 1.000000 | no |  |
| case_bench_fmu-002350 | yes | no | no | yes | 0.4716 | 3.000000 | 4.123106 | 1.000000 | no |  |
| case_bench_fmu-002360 | yes | no | no | yes | 0.4119 | 3.145849 | 4.879145 | 0.681758 | no |  |
| case_bench_fmu-002352 | yes | no | no | yes | 0.6903 | 10963.833333 | 26750.263566 | 1.000000 | no |  |
| case_bench_fmu-002351 | yes | yes | yes | no | 1.4482 | - | - | - | no |  |
| case_bench_fmu-002368 | yes | no | no | yes | 0.6158 | 2.321500 | 3.909657 | 1.000000 | no |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 0.3515 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 0.2277 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002418 | yes | no | no | yes | 0.1971 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 0.2450 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002376 | yes | no | no | no | 1.5976 | - | - | - | no |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 0.1589 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002452 | yes | no | no | yes | 0.1812 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 1.5063 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002558 | yes | no | no | yes | 0.2120 | 4.686000 | 4.733557 | 1.000000 | no |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 0.2332 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 0.1840 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002702 | yes | no | no | yes | 0.2782 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002704 | yes | no | no | yes | 0.2796 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002707 | yes | no | no | yes | 0.2537 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002710 | yes | no | no | yes | 0.3799 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002744 | yes | no | no | yes | 0.4148 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002746 | yes | no | no | yes | 0.3899 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002749 | yes | no | no | yes | 0.3477 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002752 | yes | no | no | yes | 0.4587 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002777 | yes | no | no | yes | 0.5588 | 3.854754 | 4.339866 | 1.000000 | - |  |
| case_bench_fmu-002779 | yes | no | no | yes | 0.3664 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002739 | yes | no | no | yes | 7.3091 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002736 | yes | no | no | yes | 7.7307 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002782 | yes | no | no | yes | 7.1219 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_bench_fmu-002814 | yes | no | no | yes | 0.3138 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_dtaas_drobotti_rmqfmu | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support loop handling |
| case_dtaas_flex_cell | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_dtaas_incubator_nurv_monitor_validation | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 requires a strict chain topology |
| case_dtaas_mass_spring_damper | yes | no | no | yes | 0.4299 | - | - | - | - |  |
| case_bench_fmu-002785 | yes | no | no | yes | 7.3993 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_dtaas_three_tank | yes | no | no | yes | 0.2923 | - | - | - | no |  |
| case_bench_fmu-002811 | yes | no | no | yes | 7.4211 | 3.854591 | 4.339852 | 1.000000 | - |  |
| case_dtaas_water_tank_fi | yes | no | no | no | 0.2629 | - | - | - | no |  |
| case_dtaas_water_tank_fi_monitor | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 requires a strict chain topology |
| case_dtaas_mass_spring_damper_monitor | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 does not support loop handling |
| case_dtaas_water_tank_swap | yes | no | no | no | 1.0073 | - | - | - | no |  |
| case_manual_003 | yes | no | no | yes | 0.3951 | - | - | - | yes |  |
| case_manual_004 | yes | no | no | yes | 0.4567 | - | - | - | no |  |
| case_manual_002 | yes | no | no | yes | 6.4008 | 84.584142 | 156.732509 | 0.727091 | - |  |
| case_manual_001 | yes | no | no | yes | 9.5241 | 9.554685 | 20.455818 | 0.706610 | - |  |
| case_manual_005 | yes | no | no | yes | 8.3636 | - | - | - | - |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 48.8137 | 0.094024 | 0.386942 | 0.002634 | yes |  |
