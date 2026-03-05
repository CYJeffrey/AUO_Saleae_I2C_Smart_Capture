
  # I2C Smart Capture
  
## Getting started

Ver.00.02
1. Only suitable for SGM 30.45 diagnostic use.
2. PASS will result: dignositic 0x1C check = PASS  b'\x00'
3. FAIL will result: dignositic 0x1C check = FAIL  b'\xXX'
4. You Can find total result by search data table with key work : "FAIL"
5. Enjoy your debugging.
  
Ver.00.03
1. Export all i2c command period to local path: D:/total_periods.txt

Ver.00.04
1. Modify txt file output format.

Ver.00.05
1. Fix create file bug.
2. Fix file write issue.