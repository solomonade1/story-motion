' Creates a "StoryMotion Studio" shortcut on your Desktop. Changes nothing else.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
Set lnk = sh.CreateShortcut(sh.SpecialFolders("Desktop") & "\StoryMotion Studio.lnk")
lnk.TargetPath = here & "\StoryMotion Studio.vbs"
lnk.WorkingDirectory = here
lnk.IconLocation = here & "\app\icon.ico"
lnk.Description = "StoryMotion Studio"
lnk.Save
MsgBox "A StoryMotion Studio shortcut was added to your Desktop.", 64, "StoryMotion Studio"
