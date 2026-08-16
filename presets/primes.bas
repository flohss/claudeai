10 REM Nombres premiers jusqu'a N
20 INPUT "Jusqu'a quel nombre"; N
30 PRINT "Nombres premiers :"
40 FOR K = 2 TO N
50 P = 1
60 FOR D = 2 TO K - 1
70 IF K MOD D = 0 THEN P = 0
80 NEXT D
90 IF P = 1 THEN PRINT K; " ";
100 NEXT K
110 PRINT
120 END
