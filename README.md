# OffsetSplineY
Simple Cinema 4D Python Spline Generator Object

Shows how to create an object that uses other spline objects as inputs.

This started as a question on the PluginCafe forums:
- [GetVirtualObjects v GetContour for Spline Gen - Plugin Cafe Forums](http://www.plugincafe.com/forum/forum_posts.asp?TID=13170)

Riccardo of Maxon's SDK Support team generated this example:
- [[Python] OffsetYSpline rev0.2.1 - Pastebin.com](http://pastebin.com/LHsjdg8f)

It's still something of a work in progress. Known issues:

1. Child objects are sometimes deleted when OffsetYSpline object is made editable.