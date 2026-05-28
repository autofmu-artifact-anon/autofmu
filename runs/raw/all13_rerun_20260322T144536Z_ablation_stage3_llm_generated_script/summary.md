# Evaluator Summary

- experiment_id: `all13_rerun_20260322T144536Z_ablation_stage3_llm_generated_script`
- bundle_name: `ablation_stage3_llm_generated_script`
- cases_total: 151
- succeeded: 141
- failed: 10
- top1_hit_rate: 0.9362
- topk_hit_rate: 0.9362
- execution_success_rate: 0.9574
- mean_execution_time_seconds: 29.6655
- mae: 1.614337
- rmse: 3.458963
- nrmse: 0.164156
- trimmed_mae (drop top 0.5% cases): 0.971160
- trimmed_rmse (drop top 0.5% cases): 2.270796
- trimmed_nrmse (drop top 0.5% cases): 0.149925
- decision_accuracy (loose pass rate): 0.7609

## By Case Category

### `simple`

- cases_scored: 100
- top1_hit_rate: 0.9700
- topk_hit_rate: 0.9700
- execution_success_rate: 0.9500
- mean_execution_time_seconds: 26.4472
- mae: 0.654524
- rmse: 1.887584
- nrmse: 0.079292
- trimmed_mae (drop top 0.5% cases): 0.380636
- trimmed_rmse (drop top 0.5% cases): 1.049753
- trimmed_nrmse (drop top 0.5% cases): 0.069497
- decision_accuracy (loose pass rate): 0.7300

### `complex`

- cases_scored: 41
- top1_hit_rate: 0.8537
- topk_hit_rate: 0.8537
- execution_success_rate: 0.9756
- mean_execution_time_seconds: 37.3090
- mae: 4.219544
- rmse: 7.724136
- nrmse: 0.394501
- trimmed_mae (drop top 0.5% cases): 1.855880
- trimmed_rmse (drop top 0.5% cases): 3.341537
- trimmed_nrmse (drop top 0.5% cases): 0.347281
- decision_accuracy (loose pass rate): 0.8421

| case_id | ok | top1 | topk | exec | time_s | mae | rmse | nrmse | decision | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case_bench_fmu-001288 | no | no | no | no | - | - | - | - | - | ValueError: llm_generated_script_stage3 received empty selected_fmus |
| case_bench_fmu-001292 | yes | yes | yes | yes | 33.4563 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001284 | yes | yes | yes | yes | 33.6198 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001280 | yes | yes | yes | yes | 49.8240 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001535 | yes | yes | yes | yes | 17.4140 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-001524 | yes | yes | yes | no | 17.7414 | - | - | - | no |  |
| case_bench_fmu-001523 | yes | yes | yes | no | 28.8314 | - | - | - | no |  |
| case_bench_fmu-001539 | yes | yes | yes | yes | 16.9561 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001543 | yes | yes | yes | yes | 18.8015 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-001563 | no | no | no | no | - | - | - | - | - | ValueError: llm_generated_script_stage3 received empty selected_fmus |
| case_bench_fmu-001555 | yes | yes | yes | yes | 15.5223 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001541 | yes | yes | yes | yes | 27.0548 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001559 | yes | yes | yes | yes | 16.5336 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001567 | yes | yes | yes | yes | 17.4880 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001570 | yes | yes | yes | yes | 16.5302 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001569 | yes | yes | yes | yes | 22.5421 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001572 | yes | yes | yes | yes | 16.3536 | 0.005571 | 0.010504 | 0.000240 | yes |  |
| case_bench_fmu-001571 | yes | yes | yes | yes | 22.2616 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001574 | yes | yes | yes | yes | 36.0840 | 2.350065 | 3.967188 | 0.091320 | no |  |
| case_bench_fmu-001573 | yes | yes | yes | yes | 54.0540 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001575 | yes | yes | yes | yes | 48.3219 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001577 | yes | yes | yes | yes | 19.6545 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001576 | yes | yes | yes | yes | 48.3826 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001579 | yes | yes | yes | yes | 16.6356 | 0.125627 | 0.214951 | 0.046203 | yes |  |
| case_bench_fmu-001578 | yes | yes | yes | yes | 22.5392 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001581 | yes | yes | yes | yes | 18.7185 | 0.408427 | 0.736411 | 0.016797 | yes |  |
| case_bench_fmu-001580 | yes | yes | yes | yes | 23.1041 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001584 | yes | yes | yes | yes | 14.1827 | 0.005467 | 0.010411 | 0.000237 | yes |  |
| case_bench_fmu-001583 | yes | yes | yes | yes | 16.3340 | 3.430786 | 4.452453 | 0.103468 | no |  |
| case_bench_fmu-001582 | yes | yes | yes | yes | 18.8759 | 0.048521 | 0.070131 | 0.019551 | yes |  |
| case_bench_fmu-001586 | yes | yes | yes | yes | 26.1243 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001587 | yes | yes | yes | yes | 20.1528 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001589 | yes | yes | yes | yes | 22.5913 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001588 | yes | yes | yes | yes | 31.0371 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001591 | yes | yes | yes | yes | 46.0388 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001592 | yes | yes | yes | yes | 43.3694 | 0.005524 | 0.010448 | 0.000238 | yes |  |
| case_bench_fmu-001590 | yes | yes | yes | yes | 52.6369 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001594 | yes | yes | yes | yes | 14.4489 | 1.726628 | 3.435693 | 0.079840 | no |  |
| case_bench_fmu-001593 | yes | yes | yes | yes | 51.0015 | 0.001423 | 0.002880 | 0.000334 | yes |  |
| case_bench_fmu-001595 | yes | yes | yes | no | 18.6856 | - | - | - | no |  |
| case_bench_fmu-001597 | yes | yes | yes | yes | 19.8869 | 0.003834 | 0.007104 | 0.005028 | yes |  |
| case_bench_fmu-001598 | yes | yes | yes | yes | 18.1861 | 0.012638 | 0.015612 | 0.005416 | yes |  |
| case_bench_fmu-001600 | yes | yes | yes | yes | 18.3543 | 0.000000 | 0.000000 | 0.001528 | yes |  |
| case_bench_fmu-001605 | yes | yes | yes | yes | 18.7115 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001596 | yes | yes | yes | yes | 57.1176 | 0.094024 | 0.386942 | 0.002634 | yes |  |
| case_bench_fmu-001613 | yes | yes | yes | yes | 23.7364 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001621 | yes | no | no | yes | 23.3127 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-001661 | yes | yes | yes | yes | 14.1459 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001665 | no | no | no | no | - | - | - | - | - | ValueError: llm_generated_script_stage3 received empty selected_fmus |
| case_bench_fmu-001629 | yes | yes | yes | yes | 46.3997 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-001669 | yes | yes | yes | yes | 14.7977 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001750 | yes | yes | yes | yes | 16.4074 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-001754 | no | no | no | no | - | - | - | - | - | ValueError: llm_generated_script_stage3 received empty selected_fmus |
| case_bench_fmu-001746 | yes | yes | yes | yes | 22.1822 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001657 | yes | yes | yes | yes | 52.0129 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001930 | yes | yes | yes | yes | 16.4741 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-001758 | yes | yes | yes | yes | 22.6108 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001776 | yes | yes | yes | yes | 19.9905 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-001942 | yes | yes | yes | yes | 12.8893 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-001938 | yes | yes | yes | yes | 16.5243 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-001934 | yes | yes | yes | yes | 22.9729 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002241 | yes | yes | yes | yes | 21.8953 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002019 | yes | yes | yes | yes | 26.7302 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002268 | yes | yes | yes | yes | 46.9819 | 0.008991 | 0.094821 | 0.009482 | yes |  |
| case_bench_fmu-002272 | yes | yes | yes | yes | 46.7111 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002276 | yes | yes | yes | yes | 18.7661 | 0.000820 | 0.001440 | 0.001440 | yes |  |
| case_bench_fmu-002274 | yes | yes | yes | yes | 55.0939 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002292 | yes | yes | yes | yes | 15.7295 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002288 | yes | yes | yes | yes | 22.9627 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002296 | yes | yes | yes | yes | 22.8704 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002302 | yes | yes | yes | yes | 16.2141 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002300 | yes | yes | yes | yes | 22.2705 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002303 | yes | yes | yes | yes | 15.2351 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002305 | yes | yes | yes | yes | 13.4486 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002304 | yes | yes | yes | yes | 50.7444 | 0.033818 | 0.042684 | 0.000984 | yes |  |
| case_bench_fmu-002308 | no | no | no | no | - | - | - | - | - | ValueError: llm_generated_script_stage3 received empty selected_fmus |
| case_bench_fmu-002306 | yes | yes | yes | yes | 47.9292 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002307 | yes | yes | yes | yes | 49.9474 | 0.033818 | 0.042684 | 0.000984 | yes |  |
| case_bench_fmu-001599 | no | no | no | no | - | - | - | - | - | TimeoutError: execution exceeded 300.000 seconds |
| case_bench_fmu-002311 | no | no | no | no | - | - | - | - | - | ValueError: llm_generated_script_stage3 received empty selected_fmus |
| case_bench_fmu-002309 | yes | yes | yes | yes | 16.7979 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002312 | yes | yes | yes | yes | 18.0067 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002314 | yes | yes | yes | yes | 14.6898 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002315 | yes | yes | yes | yes | 12.2256 | 0.009636 | 0.026439 | 0.006845 | yes |  |
| case_bench_fmu-002310 | yes | yes | yes | yes | 43.9662 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002313 | yes | yes | yes | yes | 41.6796 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002317 | yes | yes | yes | yes | 16.1490 | 0.014467 | 0.027770 | 0.000633 | yes |  |
| case_bench_fmu-002316 | yes | yes | yes | yes | 35.6480 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002319 | yes | yes | yes | yes | 48.9467 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002320 | yes | yes | yes | yes | 48.7466 | 0.125853 | 0.200473 | 0.040235 | yes |  |
| case_bench_fmu-002322 | yes | yes | yes | yes | 48.5343 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002321 | yes | yes | yes | yes | 65.0716 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002323 | yes | yes | yes | yes | 31.6775 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002325 | yes | yes | yes | yes | 19.5685 | 0.000249 | 0.002425 | 0.000055 | yes |  |
| case_bench_fmu-002326 | yes | yes | yes | yes | 16.9065 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002324 | yes | yes | yes | yes | 40.3700 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002336 | yes | yes | yes | yes | 19.8348 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002340 | yes | yes | yes | yes | 17.1653 | 6.855169 | 52.698386 | 0.074496 | no |  |
| case_bench_fmu-002341 | yes | yes | yes | yes | 16.0361 | 0.001058 | 0.051129 | 0.000466 | yes |  |
| case_bench_fmu-002327 | yes | yes | yes | yes | 35.1888 | 0.040738 | 0.053091 | 0.001228 | yes |  |
| case_bench_fmu-002342 | yes | yes | yes | yes | 18.5816 | 0.006604 | 0.014665 | 0.013089 | yes |  |
| case_bench_fmu-002343 | yes | yes | yes | yes | 18.8572 | 0.001768 | 0.002460 | 0.000856 | yes |  |
| case_bench_fmu-002344 | yes | yes | yes | yes | 33.4843 | 0.001998 | 0.003749 | 0.001646 | yes |  |
| case_bench_fmu-002345 | yes | yes | yes | yes | 45.1629 | 0.000000 | 0.000001 | 0.027639 | yes |  |
| case_bench_fmu-002349 | yes | yes | yes | no | 37.2824 | - | - | - | no |  |
| case_bench_fmu-002351 | yes | no | no | yes | 22.5933 | 26.400000 | 80.643661 | 1.000000 | no |  |
| case_bench_fmu-002350 | yes | yes | yes | no | 46.0869 | - | - | - | no |  |
| case_bench_fmu-002360 | yes | yes | yes | yes | 15.8078 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002352 | yes | yes | yes | no | 19.5478 | - | - | - | no |  |
| case_bench_fmu-002368 | yes | yes | yes | yes | 15.7603 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002376 | yes | no | no | yes | 12.9087 | 1.000000 | 1.000000 | 1.000000 | no |  |
| case_bench_fmu-002384 | yes | yes | yes | yes | 19.8548 | 0.000000 | 0.000000 | 0.000030 | yes |  |
| case_bench_fmu-002410 | yes | yes | yes | yes | 19.1755 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002414 | yes | yes | yes | yes | 17.4343 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002418 | yes | yes | yes | yes | 21.2258 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002422 | yes | yes | yes | yes | 18.4359 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002452 | yes | yes | yes | yes | 17.6503 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_bench_fmu-002550 | yes | yes | yes | yes | 15.6875 | 0.072738 | 0.255523 | 0.028412 | yes |  |
| case_bench_fmu-002554 | yes | yes | yes | yes | 20.0574 | 0.373762 | 0.610368 | 0.302419 | no |  |
| case_bench_fmu-002558 | yes | yes | yes | yes | 15.9497 | 0.093062 | 0.140741 | 0.029454 | yes |  |
| case_bench_fmu-002702 | yes | yes | yes | yes | 50.0708 | 2.038465 | 3.104730 | 0.555556 | yes |  |
| case_bench_fmu-002562 | yes | yes | yes | yes | 54.5655 | 0.004409 | 0.009657 | 0.009658 | yes |  |
| case_bench_fmu-002704 | yes | no | no | yes | 45.9993 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002710 | yes | yes | yes | yes | 14.2648 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_bench_fmu-002707 | yes | yes | yes | yes | 51.8772 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_bench_fmu-002739 | yes | yes | yes | yes | 15.1866 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_bench_fmu-002736 | yes | yes | yes | yes | 20.9419 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_bench_fmu-002744 | yes | yes | yes | yes | 12.4953 | 2.038465 | 3.104730 | 0.555556 | yes |  |
| case_bench_fmu-002749 | yes | yes | yes | yes | 15.2381 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_bench_fmu-002746 | yes | no | no | yes | 22.8161 | 3.851116 | 4.336938 | 1.000000 | - |  |
| case_bench_fmu-002752 | yes | yes | yes | yes | 16.0362 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_bench_fmu-002777 | yes | yes | yes | yes | 14.8120 | 2.038465 | 3.104730 | 0.555556 | yes |  |
| case_bench_fmu-002782 | yes | yes | yes | yes | 18.2600 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_bench_fmu-002811 | yes | yes | yes | yes | 16.3707 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_bench_fmu-002779 | yes | yes | yes | yes | 23.0729 | 2.039449 | 3.102694 | 0.557238 | yes |  |
| case_bench_fmu-002785 | yes | yes | yes | yes | 22.4246 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_dtaas_incubator_nurv_monitor_validation | no | no | no | no | - | - | - | - | - | ValueError: llm_generated_script_stage3 received empty selected_fmus |
| case_bench_fmu-002814 | yes | yes | yes | yes | 69.9977 | 2.038384 | 3.104720 | 0.555556 | yes |  |
| case_dtaas_drobotti_rmqfmu | yes | yes | yes | yes | 80.4010 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_flex_cell | yes | no | no | yes | 82.1970 | 0.000000 | 0.000000 | 0.000000 | yes |  |
| case_dtaas_water_tank_fi | no | no | no | no | - | - | - | - | - | ValueError: llm_generated_script_stage3 received empty selected_fmus |
| case_dtaas_water_tank_fi_monitor | no | no | no | no | - | - | - | - | - | ValueError: llm_generated_script_stage3 received empty selected_fmus |
| case_dtaas_mass_spring_damper | yes | yes | yes | yes | 36.3147 | - | - | - | no |  |
| case_dtaas_three_tank | yes | no | no | yes | 30.1621 | - | - | - | yes |  |
| case_dtaas_mass_spring_damper_monitor | yes | no | no | yes | 41.4309 | 3.204866 | 11.701923 | 0.801640 | no |  |
| case_dtaas_water_tank_swap | yes | yes | yes | yes | 39.6665 | 16.434375 | 32.645291 | 9.272761 | no |  |
| case_manual_001 | yes | yes | yes | yes | 82.7725 | 6.743301 | 16.049995 | 0.362604 | yes |  |
| case_manual_004 | yes | yes | yes | yes | 51.4762 | - | - | - | no |  |
| case_manual_002 | yes | no | no | yes | 79.4205 | 84.584142 | 156.732509 | 0.727091 | - |  |
| case_manual_003 | yes | yes | yes | yes | 78.8657 | - | - | - | yes |  |
| case_manual_005 | yes | yes | yes | yes | 42.9764 | - | - | - | no |  |
