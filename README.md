# script.dahuacam

This kodi addon originates from a 'feasibility study' leveraging the documented dahua API to display recorded jpg snapshots or mp4 video sequences of my dahua web cam. It's no big effort to capture the cam's live feed in a browser or in kodi as the relevant urls can be easily found on the internet. However, access to recorded media is a more complex process and usually requires the installation of the NACL plugin in chrome.

Since I am using my web cams as monitoring devices I have already adapted the script.securitycam kodi addon to have a cam's live feed displayed on my tv screen when motion is detected. Hence, the next idea was to make recorded data also accessible via kodi to let me quickly check snapshots or videos captured during my absence.
The addon is still at an experimental stage which, however, works quite reliable for me. It resembles the look of the playback section in the NACL plugin.

Navigation is pretty straight forward: After setting the file type and date the addon will query the cam for available files and displays them in a list. You can move up and down and select an item by pressing 'ok' or 'enter' on your remote to show additional info for the selected file below the list. For jpg files a small preview picture is shown. For video sequences you can start playback of the selected item by pressing the 'play' button on your remote. This way, the focus stays on the list and you can easily select the next item after returning from playback. Prior to playback, video files are downloaded to a temporary location. This means you will notice some delay before the video starts. 

The addon can be configured for up to 4 cameras. The active device is selectable in the dialog.

Occasionally, an API call may fail or return incomplete data - particularly if a large amount of data is collected. This will have the effect of an incomplete or empty item list and/or a preview not showing up. In this case, the addon will capture the error and display it in the 'error status' field of the dialog. The easiest way to recover from such situations is to simply repeat the last action.

As in some of my other addons, I used PyXBMCt to create the dialog window. Unfortunately, the startup time of the addon increases with the number of elements the dialog contains. So, please, don't get nervous when the dialog window doesn't instantly pop up after starting the addon. If you have any idea how to speed this up, please drop me a note or - even better - a pull request.

I am not planning on extending the functionality of this addon unless there is a substantial requirement. Maintenance will - for now - be limited to bug fixing. I hope others will find it useful.
