10 REM Suite de Fibonacci
20 INPUT "Combien de termes voulez-vous afficher"; N
30 A = 0
40 B = 1
50 FOR I = 1 TO N
60 PRINT A; " ";
70 T = A + B
80 A = B
90 B = T
100 NEXT I
110 PRINT
120 END
