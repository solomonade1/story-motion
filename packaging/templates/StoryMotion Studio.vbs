' Starts StoryMotion Studio with no console window. Double-click this file.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = here
sh.Run """" & here & "\python\pythonw.exe"" -m storymotion_media launch", 0, False
