# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_baseline_b2_llm_retrieval_rule`
- bundle_name: `baseline_b2_llm_retrieval_rule`
- cases_total: 151
- succeeded: 146
- failed: 5
- top1_hit_rate: 0.3904
- topk_hit_rate: 0.3904
- execution_success_rate: 0.8356
- mean_execution_time_seconds: 29.0623
- mae: 985.016963
- rmse: 5161.956369
- nrmse: 0.546393
- trimmed_mae (drop top 0.5% cases): 502.978557
- trimmed_rmse (drop top 0.5% cases): 2610.838539
- trimmed_nrmse (drop top 0.5% cases): 0.542516
- decision_accuracy (loose pass rate): 0.2483

## By Case Category

### `simple`

- cases_scored: 105
- top1_hit_rate: 0.5429
- topk_hit_rate: 0.5429
- execution_success_rate: 0.9429
- mean_execution_time_seconds: 28.7927
- mae: 1170.140961
- rmse: 6147.197332
- nrmse: 0.483407
- trimmed_mae (drop top 0.5% cases): 596.535149
- trimmed_rmse (drop top 0.5% cases): 3111.528504
- trimmed_nrmse (drop top 0.5% cases): 0.478135
- decision_accuracy (loose pass rate): 0.3238

### `complex`

- cases_scored: 41
- top1_hit_rate: 0.0000
- topk_hit_rate: 0.0000
- execution_success_rate: 0.5610
- mean_execution_time_seconds: 30.2225
- mae: 20.423503
- rmse: 28.332405
- nrmse: 0.874583
- trimmed_mae (drop top 0.5% cases): 14.722395
- trimmed_rmse (drop top 0.5% cases): 21.198080
- trimmed_nrmse (drop top 0.5% cases): 0.867615
- decision_accuracy (loose pass rate): 0.0500

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001280 | yes | no | no | yes | 15.5724 | 0.258565 | 1.082681 | 0.134436 | no |  |
| case_bench_fmu-001292 | yes | yes | yes | yes | 30.6123 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 30.6517 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001288 | yes | yes | yes | yes | 30.7559 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001523 | yes | no | no | yes | 24.7845 | 31.000000 | 31.000000 | 1.000000 | no |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 24.4064 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001524 | yes | no | no | yes | 30.2646 | 4.307538 | 4.688875 | 1.000000 | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 30.3042 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 30.3971 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 30.3145 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 30.2295 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001555 | yes | no | no | yes | 30.4215 | 0.258565 | 1.082681 | 0.134436 | no |  |
| case_bench_fmu-001563 | yes | yes | yes | yes | 30.3357 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 30.2991 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001569 | yes | yes | yes | yes | 28.1435 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001570 | yes | no | no | yes | 30.2762 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001571 | yes | no | no | yes | 30.2452 | 43.442641 | 43.442641 | 1.000000 | no |  |
| case_bench_fmu-001572 | yes | no | no | yes | 30.2781 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 27.1324 | 3.537296 | 4.657938 | 0.107220 | no |  |
| case_bench_fmu-001573 | yes | no | no | yes | 30.2577 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001575 | yes | yes | yes | yes | 23.8361 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001576 | yes | no | no | yes | 30.2264 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001577 | yes | no | no | yes | 30.2783 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001578 | yes | no | no | yes | 30.2683 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001579 | yes | no | no | yes | 30.2898 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 18.1211 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001580 | yes | no | no | yes | 30.2369 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001581 | yes | no | no | yes | 30.2588 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001582 | yes | no | no | yes | 30.2487 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001584 | yes | no | no | yes | 30.2287 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001586 | yes | no | no | yes | 30.2517 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001587 | yes | no | no | yes | 30.2594 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001588 | yes | no | no | yes | 30.2253 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001589 | yes | no | no | yes | 30.2575 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001590 | yes | no | no | yes | 30.2844 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001591 | yes | no | no | yes | 30.2862 | 43.032021 | 43.032021 | 1.000000 | no |  |
| case_bench_fmu-001592 | yes | no | no | yes | 30.2631 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 22.2030 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001593 | yes | no | no | yes | 30.2183 | 4.307496 | 4.688810 | 1.000000 | no |  |
| case_bench_fmu-001595 | yes | no | no | yes | 30.9015 | 121.475520 | 209.109758 | 1.000000 | no |  |
| case_bench_fmu-001596 | yes | no | no | yes | 30.2769 | 123.043442 | 154.726206 | 1.000000 | no |  |
| case_bench_fmu-001597 | yes | no | no | yes | 30.2837 | 0.999492 | 0.999492 | 1.000000 | no |  |
| case_bench_fmu-001598 | yes | no | no | yes | 30.2924 | 2.882502 | 2.882502 | 1.000000 | no |  |
| case_bench_fmu-001599 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-001600 | yes | no | no | yes | 30.2401 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-001605 | yes | yes | yes | yes | 30.4771 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001613 | yes | no | no | no | 30.2712 | - | - | - | no |  |
| case_bench_fmu-001621 | yes | yes | yes | yes | 30.4222 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001629 | yes | no | no | yes | 30.3950 | 57383.510544 | 303642.742476 | 1.000000 | no |  |
| case_bench_fmu-001657 | yes | no | no | yes | 30.4176 | 0.258565 | 1.082681 | 0.134436 | no |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 30.3028 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001665 | yes | yes | yes | yes | 30.3377 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 30.2415 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001746 | yes | yes | yes | yes | 20.4694 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 30.2541 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001754 | yes | yes | yes | yes | 30.3678 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 30.2800 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001776 | yes | no | no | yes | 29.8188 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 30.2248 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 30.2967 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 30.3707 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 30.3487 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002019 | yes | no | no | yes | 30.2234 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002241 | yes | no | no | yes | 30.2685 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 30.2693 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 30.2512 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 20.1151 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 30.3924 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 30.2817 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 23.7855 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 30.2562 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 23.7948 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002302 | yes | no | no | yes | 30.2968 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002303 | yes | no | no | yes | 30.2217 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 30.4037 | 3.535673 | 4.654562 | 0.107335 | no |  |
| case_bench_fmu-002305 | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_bench_fmu-002306 | yes | no | no | yes | 30.2680 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002307 | yes | yes | yes | yes | 30.3842 | 3.535673 | 4.654562 | 0.107335 | no |  |
| case_bench_fmu-002308 | yes | no | no | yes | 30.2366 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002309 | yes | no | no | yes | 30.2568 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002310 | yes | no | no | yes | 19.1522 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002311 | yes | no | no | yes | 30.2530 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002312 | yes | no | no | yes | 30.3107 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002314 | yes | yes | yes | yes | 20.2060 | 0.009348 | 0.017965 | 0.000410 | yes |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 25.1804 | 3.535650 | 4.649164 | 0.107525 | no |  |
| case_bench_fmu-002316 | yes | yes | yes | yes | 16.9008 | 3.535650 | 4.649164 | 0.107525 | no |  |
| case_bench_fmu-002315 | yes | no | no | yes | 30.2447 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002317 | yes | no | no | yes | 30.2586 | 28.000000 | 28.160256 | 1.000000 | no |  |
| case_bench_fmu-002319 | yes | no | no | yes | 30.2451 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002320 | yes | no | no | yes | 30.2309 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002321 | yes | no | no | yes | 20.8767 | 43.238098 | 43.238098 | 1.000000 | no |  |
| case_bench_fmu-002322 | yes | no | no | yes | 30.2160 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002323 | yes | no | no | yes | 30.2460 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 30.4598 | 3.535650 | 4.649164 | 0.107525 | no |  |
| case_bench_fmu-002325 | yes | no | no | yes | 30.2664 | 27.999836 | 28.160075 | 1.000000 | no |  |
| case_bench_fmu-002326 | yes | no | no | yes | 30.2776 | 4.544989 | 4.965156 | 1.000000 | no |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 30.3719 | 3.535650 | 4.649164 | 0.107525 | no |  |
| case_bench_fmu-002336 | yes | no | no | yes | 29.4797 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002340 | yes | no | no | yes | 30.2722 | 138.192193 | 238.064833 | 1.000000 | no |  |
| case_bench_fmu-002341 | yes | no | no | yes | 30.2509 | 122.713385 | 154.432115 | 1.000000 | no |  |
| case_bench_fmu-002342 | yes | no | no | yes | 30.2317 | 0.999265 | 0.999266 | 1.000000 | no |  |
| case_bench_fmu-002343 | yes | no | no | yes | 30.2378 | 2.874242 | 2.874242 | 1.000000 | no |  |
| case_bench_fmu-002344 | yes | no | no | yes | 30.2674 | 2.260368 | 2.260482 | 1.000000 | no |  |
| case_bench_fmu-002345 | yes | no | no | yes | 23.4720 | 0.000019 | 0.000019 | 1.000000 | no |  |
| case_bench_fmu-002349 | yes | yes | yes | no | 30.3778 | - | - | - | no |  |
| case_bench_fmu-002350 | yes | yes | yes | no | 30.6477 | - | - | - | no |  |
| case_bench_fmu-002351 | yes | yes | yes | no | 30.6675 | - | - | - | no |  |
| case_bench_fmu-002352 | yes | yes | yes | no | 30.6567 | - | - | - | no |  |
| case_bench_fmu-002360 | yes | yes | yes | yes | 30.4274 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002368 | yes | no | no | no | 30.2865 | - | - | - | no |  |
| case_bench_fmu-002376 | yes | yes | yes | yes | 27.3031 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002384 | yes | no | no | yes | 30.3949 | 57383.510544 | 303642.742476 | 1.000000 | no |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 29.8757 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 30.2462 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 30.3803 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 30.3385 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002452 | yes | no | no | yes | 30.2876 | 3.079684 | 3.520871 | 1.000000 | no |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 30.2296 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 30.2560 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 30.2770 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 30.2827 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002702 | yes | no | no | no | 30.2709 | - | - | - | no |  |
| case_bench_fmu-002704 | yes | no | no | no | 30.2404 | - | - | - | no |  |
| case_bench_fmu-002707 | yes | no | no | no | 30.2914 | - | - | - | no |  |
| case_bench_fmu-002710 | yes | no | no | no | 30.2798 | - | - | - | no |  |
| case_bench_fmu-002736 | yes | no | no | no | 30.2992 | - | - | - | no |  |
| case_bench_fmu-002739 | yes | no | no | no | 30.3204 | - | - | - | no |  |
| case_bench_fmu-002744 | yes | no | no | no | 30.3058 | - | - | - | no |  |
| case_bench_fmu-002746 | yes | no | no | no | 30.3229 | - | - | - | no |  |
| case_bench_fmu-002749 | yes | no | no | no | 30.2628 | - | - | - | no |  |
| case_bench_fmu-002752 | yes | no | no | no | 30.3134 | - | - | - | no |  |
| case_bench_fmu-002777 | yes | no | no | no | 30.3335 | - | - | - | no |  |
| case_bench_fmu-002779 | yes | no | no | no | 30.2606 | - | - | - | no |  |
| case_bench_fmu-002782 | yes | no | no | no | 30.2912 | - | - | - | no |  |
| case_bench_fmu-002785 | yes | no | no | no | 30.3040 | - | - | - | no |  |
| case_bench_fmu-002811 | yes | no | no | no | 30.2664 | - | - | - | no |  |
| case_bench_fmu-002814 | yes | no | no | no | 30.2749 | - | - | - | no |  |
| case_dtaas_drobotti_rmqfmu | yes | no | no | yes | 30.2295 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_flex_cell | yes | no | no | yes | 30.3230 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_incubator_nurv_monitor_validation | yes | no | no | yes | 30.4303 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_dtaas_mass_spring_damper | yes | no | no | yes | 30.3507 | - | - | - | - |  |
| case_dtaas_three_tank | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_dtaas_mass_spring_damper_monitor | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_dtaas_water_tank_fi | yes | no | no | no | 30.2874 | - | - | - | no |  |
| case_dtaas_water_tank_fi_monitor | no | no | no | no | - | - | - | - | - | ValueError: static_rule_scheduler_stage3 received empty selected_fmus |
| case_dtaas_water_tank_swap | yes | no | no | no | 30.8593 | - | - | - | no |  |
| case_manual_001 | yes | no | no | yes | 30.3047 | 10.722475 | 20.704679 | 0.885590 | no |  |
| case_manual_002 | yes | no | no | yes | 30.2295 | 84.778819 | 156.750269 | 0.731481 | no |  |
| case_manual_003 | yes | no | no | yes | 30.3137 | - | - | - | no |  |
| case_manual_004 | yes | no | no | yes | 30.2974 | - | - | - | no |  |
| case_manual_005 | yes | no | no | yes | 30.2594 | - | - | - | no |  |
