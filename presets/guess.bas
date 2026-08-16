10 REM Devine le nombre entre 1 et 100
20 PRINT "Je pense a un nombre entre 1 et 100."
30 SECRET = INT(RND(1) * 100) + 1
40 TRIES = 0
50 INPUT "Ton essai"; G
60 TRIES = TRIES + 1
70 IF G = SECRET THEN GOTO 110
80 IF G < SECRET THEN PRINT "Plus grand !"
90 IF G > SECRET THEN PRINT "Plus petit !"
100 GOTO 50
110 PRINT "Bravo ! Trouve en "; TRIES; " essais."
120 END
