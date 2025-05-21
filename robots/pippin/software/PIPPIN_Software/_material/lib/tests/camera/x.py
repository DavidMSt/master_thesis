from robot.lib.xgoedu import XGOEDU
XGO_edu = XGOEDU()

while True:
    result=XGO_edu.gestureRecognition()
    print(result)
    if XGO_edu.xgoButton("c"):
        break