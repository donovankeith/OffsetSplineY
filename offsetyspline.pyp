"""Offset-Y Spline
Takes a child-spline as input and offset all its points on the y-axis by a specific value. Tangents are unaffected.

Usage Instructions
------------------
1. Add a `Circle` (or any spline primitive) to your scene.
2. `Plugins > Py-OffsetYSpline`
3. Make the `Circle` a child of `Py-OffsetYSpline`
4. Adjust the `Offset` value in the attributes manager.

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

def tracefunc(frame, event, arg, indent=[0]):
    indent_width = 4

    if event == "call":
        indent[0] += 1
        print " " * indent[0] * indent_width, "<", frame.f_code.co_name, ">"
    elif event == "return":
        print " " * indent[0] * indent_width, "</", frame.f_code.co_name, ">"
        indent[0] -= 1
    return tracefunc


debug = False

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


def CopySplineParamsValue(source_spline, dest_spline):
    """Global function responsible to copy the spline parameters across a source and a destination"""

    if source_spline is None or dest_spline is None:
        return False

    source_real_spline = source_spline.GetRealSpline()
    if source_real_spline is not None:
        source_real_spline_bc = source_real_spline.GetDataInstance()
        if source_real_spline_bc is not None:
            dest_spline.SetParameter(c4d.SPLINEOBJECT_INTERPOLATION,
                                     source_real_spline_bc.GetInt32(c4d.SPLINEOBJECT_INTERPOLATION),
                                     c4d.DESCFLAGS_SET_FORCESET)
            dest_spline.SetParameter(c4d.SPLINEOBJECT_MAXIMUMLENGTH,
                                     source_real_spline_bc.GetFloat(c4d.SPLINEOBJECT_MAXIMUMLENGTH),
                                     c4d.DESCFLAGS_SET_FORCESET)
            dest_spline.SetParameter(c4d.SPLINEOBJECT_SUB, source_real_spline_bc.GetInt32(c4d.SPLINEOBJECT_SUB),
                                     c4d.DESCFLAGS_SET_FORCESET)
            dest_spline.SetParameter(c4d.SPLINEOBJECT_ANGLE, source_real_spline_bc.GetFloat(c4d.SPLINEOBJECT_ANGLE),
                                     c4d.DESCFLAGS_SET_FORCESET)
            return True

    return False


def FinalSpline(source):
    """Global function responsible to return the final representation of the spline"""

    if source is None:
        return None

    # check is source can be treated as a spline
    if not IsSplineCompatible(source):
        return None

    return source.GetRealSpline()


def OffsetSpline(input_spline, offset_value):
    """Global function responsible for modifying the spline"""

    if input_spline is None:
        return None

    # just return if the input object doesn't belong to spline or line type
    if not IsSplineOrLine(input_spline):
        return None

    # local matrix for updating the point position in parent space
    input_ml = input_spline.GetMl()

    # local matrix for updating the tangents direction and scaling in parent space
    input_scale_rotate = input_spline.GetMl()
    input_scale_rotate.off = c4d.Vector(0, 0, 0)

    # retrieve child points count and type
    point_count = input_spline.GetPointCount()
    tangent_count = 0
    spline_type = 0

    if (input_spline.GetType() == c4d.Ospline):
        tangent_count = input_spline.GetTangentCount()
        spline_type = input_spline.GetInterpolationType()

    # allocate the resulting spline
    result_spline = c4d.SplineObject(point_count, spline_type)
    if result_spline is None:
        return None

    # set the points position and tangency data
    for i in range(point_count):
        # currPos = input_spline.GetPoint(i)
        cur_pos = input_ml * input_spline.GetPoint(i)
        result_spline.SetPoint(i, c4d.Vector(cur_pos.x, cur_pos.y + offset_value, cur_pos.z))
        # set in case the tangency data
        if tangent_count != 0:
            cur_tangent = input_spline.GetTangent(i)
            result_spline.SetTangent(i, input_scale_rotate * cur_tangent["vl"], input_scale_rotate * cur_tangent["vr"])

    # return the computed spline
    return result_spline


def RecurseOnChild(op):
    """Global function responsible to return the first enabled object in a hierarchy"""

    if op is None:
        return None

    child_obj = op.GetDown()
    if child_obj is None:
        return None

    # skip deformers
    is_modifier = child_obj.GetInfo() & c4d.OBJECT_MODIFIER
    if is_modifier:
        return None

    # check and return the first active child
    if child_obj.GetDeformMode():
        return child_obj
    else:
        return RecurseOnChild(child_obj)


def RecursiveCheckDirty(op):
    """Global function responsible to recursively check the dirty flag in a hierarchy"""

    res = 0

    if op is None:
        return res

    cur_obj = op
    next_obj = op.GetNext()
    child_obj = op.GetDown()

    res += cur_obj.GetDirty(c4d.DIRTYFLAGS_DATA | c4d.DIRTYFLAGS_MATRIX | c4d.DIRTYFLAGS_CACHE)

    if child_obj is not None:
        res += RecursiveCheckDirty(child_obj)

    if next_obj is not None:
        res += RecursiveCheckDirty(next_obj)

    return res


def IsSplineOrLine(op):
    if op is None:
        return False

    return op.IsInstanceOf(c4d.Ospline) or op.IsInstanceOf(c4d.Oline)


def IsSplineCompatible(op):
    if op is None:
        return False

    return IsSplineOrLine(op) or (op.GetInfo() & c4d.OBJECT_ISSPLINE)


# =====================================================================================================================#
#   Class Definitions
# =====================================================================================================================#
class OffsetYSpline(c4d.plugins.ObjectData):
    def __init__(self):
        """Create member variables"""

        self._countour_child_dirty = -1
        self._child_dirty = -1

    def Init(self, op):
        """Establish default values for Dialog"""

        if op is None:
            return False

        bc = op.GetDataInstance()
        if bc is None:
            return False

        bc.SetInt32(c4d.PY_OFFSETYSPLINE_OFFSET, 100)

        return True

    def CheckDirty(self, op, doc):
        """Returns True if op or its children are Dirty. (I think) It's only used for GetContour checks."""

        if (op is None) or (doc is None):
            return

        child_dirty = 0

        child = op.GetDown()

        if child is not None:
            child_dirty = RecursiveCheckDirty(child)

        if child_dirty != self._countour_child_dirty:
            op.SetDirty(c4d.DIRTYFLAGS_DATA)

        self._countour_child_dirty = child_dirty

    def GetVirtualObjects(self, op, hh):
        """Return the result of the generator.

        Responsible for hiding the child objects
        """

        if (op is None) or (hh is None):
            return None

        child = None
        child_spline = None
        result_spline = None
        dirty = False
        clone_dirty = False
        temp = None
        child_dirty = -1

        cache = op.GetCache()
        bc = op.GetDataInstance()
        if bc is None:
            return
        offset_value = bc.GetFloat(c4d.PY_OFFSETYSPLINE_OFFSET)

        # look for the first enabled child in order to support hierarchical
        child = RecurseOnChild(op)
        if child is None:
            self._child_dirty = -1
            self._countour_child_dirty = -1
            return

        # Store whether the spline is open/closed as this will be overwritten later
        is_child_closed = IsClosed(child.GetRealSpline())

        # Use the GetHierarchyClone and the GetAndCheckHierarchyClone to operate as a two-step
        # GetHierarchyClone operates when passing a bool reference in the first step to check
        # the dirtyness and a nullptr on a second step to operate the real clone
        result_ghc = op.GetHierarchyClone(hh, child, c4d.HIERARCHYCLONEFLAGS_ASSPLINE)
        if result_ghc is None:
            result_ghc = op.GetAndCheckHierarchyClone(hh, child, c4d.HIERARCHYCLONEFLAGS_ASSPLINE, False)

        if result_ghc is not None:
            clone_dirty = result_ghc["dirty"]
            temp = result_ghc["clone"]

        dirty |= clone_dirty

        # recursively check the dirty flag for the children (deformers or other generators)
        if IsSplineCompatible(temp):
            child_dirty = RecursiveCheckDirty(child)
            child_spline = temp

        child.Touch()

        dirty |= op.IsDirty(c4d.DIRTYFLAGS_DATA)

        # compare the dirtyness of local and member variable and accordingly update the generator's
        # dirty status and the member variable value
        # check is &= or |=
        dirty |= self._child_dirty != child_dirty
        self._child_dirty = child_dirty

        if (not dirty) and (cache is not None):
            cache_clone = cache.GetClone(c4d.COPYFLAGS_NO_ANIMATION)
            return cache_clone

        if child_spline is None:
            return

        # operate the spline modification
        result_spline = OffsetSpline(FinalSpline(child_spline), offset_value)
        if result_spline is None:
            return

        # restore the closing status of the spline
        SetClosed(result_spline, is_child_closed)

        # copy the spline tags
        child_spline.CopyTagsTo(result_spline, True, c4d.NOTOK, c4d.NOTOK)

        # copy the spline parameters value
        CopySplineParamsValue(child_spline, result_spline)

        # notify about the generator update
        result_spline.Message(c4d.MSG_UPDATE)

        return result_spline

    def GetContour(self, op, doc, lod, bt):
        """Returns a Spline version of the object, called when GetRealSpline() is used.
        """

        if op is None:
            return None

        if doc is None:
            doc = op.GetDocument()

        if doc is None:
            return None

        child = None
        child_spline = None
        result_spline = None

        bc = op.GetDataInstance()
        if bc is None:
            return None
        offset_value = bc.GetFloat(c4d.PY_OFFSETYSPLINE_OFFSET)

        child = RecurseOnChild(op)
        if child is None:
            self._child_dirty = 0
            self._countour_child_dirty = 0
            return None

        # Store whether the spline is open/closed as this will be overwritten later
        is_child_closed = IsClosed(child.GetRealSpline())

        # Emulate GetHierarchyClone in GetContour by using SendModelingCommand
        temp = None
        if child is not None:
            temp = child.GetClone(c4d.COPYFLAGS_NO_ANIMATION)
            if temp is None:
                return None

            result = c4d.utils.SendModelingCommand(command=c4d.MCOMMAND_MAKEEDITABLE, list=[temp], doc=doc)
            if result is False:
                return None

            if IsSplineCompatible(temp):
                child_spline = temp

        if child_spline is None:
            return None

        # operate the spline modification
        result_spline = OffsetSpline(FinalSpline(child_spline), offset_value)
        if result_spline is None:
            return None

        # restore the closing status of the spline
        SetClosed(result_spline, is_child_closed)

        # copy the spline parameters value
        CopySplineParamsValue(child_spline, result_spline)

        # notify about the generator update
        result_spline.Message(c4d.MSG_UPDATE)

        return result_spline


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
