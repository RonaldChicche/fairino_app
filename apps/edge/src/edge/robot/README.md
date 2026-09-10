# robot

Cliente del SDK de FAIRINO para el FR10: conexión con el controlador, lectura de estado e invocación de las primitivas Lua ya cargadas en el robot, con sus parámetros (D2).

No le corresponde: generar trayectorias ni validar límites del brazo (lo hace el controlador), decidir cuándo se mueve (`session/`), ni la seguridad física, que depende del paro por hardware (D10).
