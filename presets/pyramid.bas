10 REM Pyramide d'etoiles
20 INPUT "Hauteur de la pyramide"; H
30 FOR I = 1 TO H
40 FOR S = 1 TO H - I
50 PRINT " ";
60 NEXT S
70 FOR E = 1 TO 2 * I - 1
80 PRINT "*";
90 NEXT E
100 PRINT
110 NEXT I
120 END
