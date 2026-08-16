10 REM Statistiques sur une liste de nombres
20 INPUT "Combien de nombres"; N
30 DIM V(N)
40 SOMME = 0
50 FOR I = 1 TO N
60 PRINT "Nombre "; I; " : ";
70 INPUT X
80 V(I) = X
90 SOMME = SOMME + X
100 IF I = 1 THEN MINV = X : MAXV = X
110 IF X < MINV THEN MINV = X
120 IF X > MAXV THEN MAXV = X
130 NEXT I
140 PRINT "Somme = "; SOMME
150 PRINT "Moyenne = "; SOMME / N
160 PRINT "Minimum = "; MINV
170 PRINT "Maximum = "; MAXV
180 END
