"""Offset-Y Spline
Takes a child-spline as input and offset all its points on the y-axis by a specific value. Tangents are unaffected.

Usage Instructions
------------------
1. Save in a file called OffsetYSpline.pyp
2. Locate it in the plugin folder
3. Start Cinema
4. Create a generating spline
5. From the Plugin menu, select OffsetYSpline
6. Set the generating spline as input child of the OffsetYSpline


To Do
-----

- [ ] Clear Dead Object Error
- [ ] Allow for child objects
- [ ] Switch to Make Editable instead of CSTO where possible

"""

# =====================================================================================================================#
# Imports
# =====================================================================================================================#

import sys
import c4d
PLUGIN_ID = 98989801


# =====================================================================================================================#
# Debugging
# =====================================================================================================================#

def tracefunc(frame, event, arg, indent = [0]):
    indent_width = 4

    if event == "call":
        indent[0] += indent_width
        print " " * indent[0], "<", frame.f_code.co_name, ">"
    elif event == "return":
        print " " * indent[0], "</", frame.f_code.co_name, ">"
        indent[0] -= indent_width
    return tracefunc

debug = True

if debug:
    sys.settrace(tracefunc)

# =====================================================================================================================#
# Global Functions Definitions
# =====================================================================================================================#

def SetClosed(spline, value):
    """Global function responsible to set the close status of a spline"""

    if spline is not None:
        spline.SetParameter(c4d.DescID(c4d.DescLevel(c4d.SPLINEOBJECT_CLOSED)), value, c4d.DESCFLAGS_SET_FORCESET)
        spline.GetDataInstance().SetBool(c4d.SPLINEOBJECT_CLOSED, value)
        return True

    return False


def IsClosed(spline):
    """Global function responsible to check the close status of a spline"""

    if spline is None:
        return False

    if spline.GetCacheParent() is not None:
        return spline.GetCacheParent().IsClosed()
    else:
        return spline.IsClosed()


def CopySplineParamsValue(sourceSpline, destSpline):
    """Global function responsible to copy the spline parameters across a source and a destination"""

    if sourceSpline is None or destSpline is None:
        return False

    sourceRealSpline = sourceSpline.GetRealSpline()
    if sourceRealSpline is not None:
        sourceRealSplineBC = sourceRealSpline.GetDataInstance()
        if sourceRealSplineBC is not None:
            destSpline.SetParameter(c4d.SPLINEOBJECT_INTERPOLATION,
                                    sourceRealSplineBC.GetInt32(c4d.SPLINEOBJECT_INTERPOLATION),
                                    c4d.DESCFLAGS_SET_FORCESET)
            destSpline.SetParameter(c4d.SPLINEOBJECT_MAXIMUMLENGTH,
                                    sourceRealSplineBC.GetFloat(c4d.SPLINEOBJECT_MAXIMUMLENGTH),
                                    c4d.DESCFLAGS_SET_FORCESET)
            destSpline.SetParameter(c4d.SPLINEOBJECT_SUB, sourceRealSplineBC.GetInt32(c4d.SPLINEOBJECT_SUB),
                                    c4d.DESCFLAGS_SET_FORCESET)
            destSpline.SetParameter(c4d.SPLINEOBJECT_ANGLE, sourceRealSplineBC.GetFloat(c4d.SPLINEOBJECT_ANGLE),
                                    c4d.DESCFLAGS_SET_FORCESET)
            return True

    return False


def FinalSpline(source):
    """Global function responsible to return the final representation of the spline

    Returns:
        None if not a spline
        Deformed RealSpline if it exists
        Spline itself
        Realspline representation if it's a primitive spline
        """

    if source is None:
        return None

    # check is source can be treated as a spline
    if not IsSplineOrLine(source):
        return None

    if source.GetDeformCache() is not None:
        # it seems it's never hit
        source = source.GetDeformCache()

    # return the spline as a procedural curve
    if (not source.IsInstanceOf(c4d.Ospline)) and (source.GetRealSpline() is not None):
        return source.GetRealSpline()

    return source


def OffsetSpline(inputSpline, offsetValue):
    """Global function responsible for modifying the spline
    """

    if inputSpline is None:
        return None

    # just return if the input object doesn't belong to spline or line type
    if not IsSplineOrLine(inputSpline):
        return None

    # local matrix for updating the point position in parent space
    inputML = inputSpline.GetMl()

    # local matrix for updating the tangents direction and scaling in parent space
    inputScaleRotate = inputSpline.GetMl()
    inputScaleRotate.off = c4d.Vector(0, 0, 0)

    # retrieve child points count and type
    pointsCnt = inputSpline.GetPointCount()
    tangentsCnt = 0
    splineType = 0

    if (inputSpline.GetType() == c4d.Ospline):
        tangentsCnt = inputSpline.GetTangentCount()
        splineType = inputSpline.GetInterpolationType()

    # allocate the resulting spline
    resSpline = c4d.SplineObject(pointsCnt, splineType)
    if resSpline is None:
        return None

    # set the points position and tangency data
    for i in range(pointsCnt):
        # currPos = inputSpline.GetPoint(i)
        currPos = inputML * inputSpline.GetPoint(i)
        resSpline.SetPoint(i, c4d.Vector(currPos.x, currPos.y + offsetValue, currPos.z))
        # set in case the tangency data
        if tangentsCnt != 0:
            currTan = inputSpline.GetTangent(i)
            resSpline.SetTangent(i, inputScaleRotate * currTan["vl"], inputScaleRotate * currTan["vr"])

    # return the computed spline
    return resSpline


def RecurseOnChild(op):
    """Global function responsible to return the first enabled object in a hierarchy"""

    if op is None:
        return None

    childObj = op.GetDown()
    if childObj is None:
        return None

        # skip deformers
    isModifier = childObj.GetInfo() & c4d.OBJECT_MODIFIER
    if isModifier:
        return None

    # check and return the first active child
    if childObj.GetDeformMode():
        return childObj
    else:
        return RecurseOnChild(childObj)


def RecursiveCheckDirty(op):
    """Global function responsible to recursively check the dirty flag in a hierarchy"""

    res = 0

    if op is None:
        return res

    current = op
    nextObj = op.GetNext()
    childObj = op.GetDown()

    res += current.GetDirty(c4d.DIRTYFLAGS_DATA | c4d.DIRTYFLAGS_MATRIX)

    if childObj is not None:
        res += RecursiveCheckDirty(childObj)

    if nextObj is not None:
        res += RecursiveCheckDirty(nextObj)

    return res

def IsSplineOrLine(op):
    """Returns True if op is a Spline or Line"""

    if op is None:
        return

    if op.IsInstanceOf(c4d.Ospline):
        return True

    if op.IsInstanceOf(c4d.Oline):
        return True

    return False

def IsSplineCompatible(op):
    """Returns True if op is a spline or could be converted into one"""

    if op is None:
        return

    if IsSplineOrLine(op):
        return True

    if op.GetInfo() & c4d.OBJECT_ISSPLINE:
        return True

    return False


# =====================================================================================================================#
#   Class Definitions
# =====================================================================================================================#
class OffsetYSpline(c4d.plugins.ObjectData):
    def __init__(self):
        """Create member variables"""

        self._contourChildDirty = -1
        self._childDirty = -1

    def Init(self, op):
        """Establish default values for Dialog"""

        if op is None:
            return False

        bc = op.GetDataInstance()
        if bc is None:
            return False

        bc.SetInt32(c4d.PY_OFFSETYSPLINE_OFFSET, 100)

        return True

    def GetDimension(self, op, mp, rad):
        """Return the Bounding Box of op

        I think:
        mp & rad are passed by reference, so edit them in place, don't replace w/ a Vector()"""

        # Reset to 0
        mp.x = 0
        mp.y = 0
        mp.z = 0
        rad.x = 0
        rad.y = 0
        rad.z = 0

        if op is None:
            return

        bc = op.GetDataInstance()
        if op.GetDown() is not None:
            rad.x = op.GetDown().GetRad().x
            rad.y = op.GetDown().GetRad().y
            rad.z = op.GetDown().GetRad().z
            mp.x = op.GetMg().off.x
            mp.y = op.GetMg().off.y + bc.GetFloat(c4d.PY_OFFSETYSPLINE_OFFSET)
            mp.z = op.GetMg().off.z

    def CheckDirty(self, op, doc):
        """Returns True if op or its children are Dirty. (I think) It's only used for GetContour checks."""

        if (op is None) or (doc is None):
            return

        childDirty = 0

        child = op.GetDown()

        if child is not None:
            childDirty = RecursiveCheckDirty(child)

        if childDirty != self._contourChildDirty:
            op.SetDirty(c4d.DIRTYFLAGS_DATA)

        self._contourChildDirty = childDirty

    def GetVirtualObjects(self, op, hh):
        """Return the result of the generator."""

        if op is None or hh is None:
            return None

        child = None
        childSpline = None
        resSpline = None
        dirty = False
        cloneDirty = False
        temp = None
        childDirty = -1

        cache = op.GetCache()
        bc = op.GetDataInstance()
        if bc is None:
            return c4d.BaseObject(c4d.Onull)
        offsetValue = bc.GetFloat(c4d.PY_OFFSETYSPLINE_OFFSET)

        # look for the first enabled child in order to support hierarchical
        child = RecurseOnChild(op)
        if child is None:
            self._childDirty = -1
            self._contourChildDirty = -1
            return c4d.BaseObject(c4d.Onull)

        # Store now the closure state of the child cause child will be later on overwritten
        isChildClosed = IsClosed(child.GetRealSpline())

        # Use the GetHierarchyClone and the GetAndCheckHierarchyClone to operate as a two-step
        # GetHierarchyClone operates when passing a bool reference in the first step to check
        # the dirtyness and a nullptr on a second step to operate the real clone
        resGHC = op.GetHierarchyClone(hh, child, c4d.HIERARCHYCLONEFLAGS_ASSPLINE)
        if resGHC is None:
            resGHC = op.GetAndCheckHierarchyClone(hh, child, c4d.HIERARCHYCLONEFLAGS_ASSPLINE, False)

        if resGHC is not None:
            cloneDirty = resGHC["dirty"]
            temp = resGHC["clone"]

        dirty |= cloneDirty

        # recursively check the dirty flag for the children (deformers or other generators)
        if temp is not None and IsSplineCompatible(temp):
            childDirty = RecursiveCheckDirty(child)
            if childSpline is None:
                childSpline = temp

        child.Touch()

        dirty |= op.IsDirty(c4d.DIRTYFLAGS_DATA)

        # compare the dirtyness of local and member variable and accordingly update the generator's
        # dirty status and the member variable value
        # check is &= or |=
        dirty |= self._childDirty != childDirty
        self._childDirty = childDirty

        if not dirty and cache is not None:
            return cache

        if childSpline is None:
            return c4d.BaseObject(c4d.Onull)

            # operate the spline modification
        resSpline = OffsetSpline(FinalSpline(childSpline), offsetValue)
        if resSpline is None:
            return c4d.BaseObject(c4d.Onull)

        # restore the closing status of the spline
        SetClosed(resSpline, isChildClosed)

        # copy the spline tags
        childSpline.CopyTagsTo(resSpline, True, c4d.NOTOK, c4d.NOTOK)

        # copy the spline parameters value
        CopySplineParamsValue(childSpline, resSpline)

        # notify about the generator update
        resSpline.Message(c4d.MSG_UPDATE)

        return resSpline

    def GetContour(self, op, doc, lod, bt):
        if op is None:
            return None

        if doc is None:
            doc = op.GetDocument()

        if doc is None:
            return None

        child = None
        childSpline = None
        resSpline = None

        bc = op.GetDataInstance()
        if bc is None:
            return None
        offsetValue = bc.GetFloat(c4d.PY_OFFSETYSPLINE_OFFSET)

        child = RecurseOnChild(op)
        if child is None:
            self._childDirty = 0
            self._contourChildDirty = 0
            return None

        # Store now the closure state of the child cause child will be later on overwritten
        isChildClosed = IsClosed(child.GetRealSpline())

        # emulate the GetHierarchyClone in the GetContour by using the SendModelingCommand
        temp = child
        if temp is not None:
            temp = temp.GetClone(c4d.COPYFLAGS_NO_ANIMATION)
            if temp is None:
                return None

            result = c4d.utils.SendModelingCommand(command=c4d.MCOMMAND_CURRENTSTATETOOBJECT, list=[temp], doc=doc)

            if result is False:
                return None

            if isinstance(result, list) and temp is not result[0] and result[0] is not None:
                temp = result[0]
                if temp.GetType() == c4d.Onull:
                    result2 = c4d.utils.SendModelingCommand(command=c4d.MCOMMAND_JOIN, list=[temp], doc=doc)

                    if result2 is False:
                        return None

                    if isinstance(result2, list) and result2[0] is not None and temp is not result2[0]:
                        temp = result2[0]

        if (temp is not None) and IsSplineCompatible(temp):
            if childSpline is None:
                childSpline = temp

        if childSpline is None:
            return None

        # operate the spline modification
        resSpline = OffsetSpline(FinalSpline(childSpline), offsetValue)
        if resSpline is None:
            return None

        # restore the closing status of the spline
        SetClosed(resSpline, isChildClosed)

        # copy the spline parameters value
        CopySplineParamsValue(childSpline, resSpline)

        # notify about the generator update
        resSpline.Message(c4d.MSG_UPDATE)

        return resSpline


# =====================================================================================================================#
#   Plugin registration
# =====================================================================================================================#

if __name__ == "__main__":
    c4d.plugins.RegisterObjectPlugin(id=PLUGIN_ID,
                                     str="Py-OffsetYSpline",
                                     g=OffsetYSpline,
                                     description="OoffsetYSpline",
                                     icon=None,
                                     info=c4d.OBJECT_GENERATOR | c4d.OBJECT_INPUT | c4d.OBJECT_ISSPLINE)
