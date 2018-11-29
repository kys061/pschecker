전체 로직

0. 최초 Stm 응답체크 - 정상
  1.1. 정상 응답일 경우
  1.2. Dpdk 인터페이스 체크
  1.3. Dpdk 인터페이스 정상 셋팅일 경우
  1.4. stm상태를 정상으로 판단
  1.5. 1번부터 1.4번까지 한번 더 10초 간격으로 반복
  1.6. stm 정상일 경우
  1.7. dpdk 스레드 체크
  1.8. 정상일 경우 1번 부터 1.4번까지 10초 간격 반복 체크
  1.9. 1.8이 정상일 경우 1.6번 부터 1.7번까지 10초 간격 반복 체크
  1.10. 1.8이 비정상일 경우
  1.11. 아파치를 7번까지 리스타트
  1.12. 여전히 stm 비정상일 경우 재부팅 진행
  
0. 최초 Stm 응답체크 - 비정상
  2.1. 비정상 응답일 경우
  2.2. 30초간격으로 계속해서 상태 체크

==========================
에러 기록

1. 11/12/2018
2018-11-12 17:36:06,707 - saisei.thread_monitor - INFO - The version of stm is now V7.3
2018-11-12 17:36:16,721 - saisei.thread_monitor - ERROR - TimeOutError, No respond from stm
2018-11-12 17:36:16,722 - saisei.thread_monitor - INFO - STM Thread Checking is Started...
Traceback (most recent call last):
  File "/etc/stmfiles/files/scripts/thread_monitor.py", line 339, in <module>
    main()
  File "/etc/stmfiles/files/scripts/thread_monitor.py", line 322, in main
    check_interface_thread()
  File "/etc/stmfiles/files/scripts/thread_monitor.py", line 259, in check_interface_thread
    get_command(r"show parameter", r"|grep 'interfaces_per_core' |awk '{print $2}'"), 10)[0].strip()):
AttributeError: 'bool' object has no attribute 'strip'


