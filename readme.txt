-------Face Intruder Detector---------
please note:
This program has been designed and written by David Bukedi Diela 
as final project for python course.


requirements:
-python >=3.7
-webcam 
-Python modules-opencv,numpy,Pyqt5,beepy


features:
	-register user face
	-detect non-user face and logout(non registered users)
	-set alarm voice type(male/female)
	-set alarm speech(change what voice says)
	-set alarm sound


thanks to saksham-jain check out his github !!
https://github.com/saksham-jain

installation:
after downloading the project file and installing the dependencies, read those instructions:
-run SettingsGUIFunc.py to add users(more features can be seen on the UI) 
-open Task scheduler(windows program)
we will create two tasks; one triggered when the user log on and one that we be trigered after a certain amount of time:
A.first 
-click on create Task and write the task name(suggest FaceIntruderDetector)
-click on the tab Triggers ,new  then on begin task choose "on workstation unlock" then validate
-click on the tab actions an choose the file "FaceIntruder.pyw" an validate
-click on the tab conditions and uncheck "start the task only if the computer is on AC power then ok
B.second
-click on create Task and write the task name(suggest FaceIntruderDetector2)
-click on the tab Triggers ,new  then on begin task choose "on a schdule" then check one time , repeat task every and set the time you want the task to be repeated then ok
-click on the tab actions an choose the file "FaceIntruder.pyw" an validate
-click on the tab conditions and uncheck "start the task only if the computer is on AC power then ok
