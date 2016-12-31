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


trace = False

if trace:
    sys.settrace(tracefunc)

debug = False

# =====================================================================================================================#
#   Profiling
# =====================================================================================================================#

import cProfile
import functools
import pstats

def profile(func):
    """
    Decorator to profile the function *func*.

    .. attribute:: profile

        The generated profile of the function. Any calls to the wrapped
        function will contribute to the profile.
    """

    profile = cProfile.Profile()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return profile.runcall(func, *args, **kwargs)

    wrapper.profile = profile
    return wrapper

def PluginMessage(msg_type, data):
    if msg_type == c4d.C4DPL_RELOADPYTHONPLUGINS:
        profile = OffsetYSpline.GetVirtualObjects.profile
        profile.create_stats()
        if profile.stats:
            # Creating the Stats object will fail if the profile
            # has recorded data.
            stats = pstats.Stats(profile)
            stats.sort_stats('time').print_stats()

    return True

# =====================================================================================================================#
# Global Functions Definitions
# =====================================================================================================================#

def SetClosed(spline, value):
    """Global function responsible to set the close status of a spline"""

    if spline is not None:
        spline[c4d.SPLINEOBJECT_CLOSED] = value
        return True

    return False


def IsClosed(spline):
    """Global function responsible to check the close status of a spline"""
    if spline is None:
        return False

    # ?? In case we've got a LineObject from a cache, get the Spline that created it and check it's closed state. ??
    if spline.GetCacheParent() is not None:
        return spline.GetCacheParent().IsClosed()
    else:
        return spline.IsClosed()

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

    if source.GetDeformCache() is not None:
        # it seems it's never hit
        source = source.GetDeformCache()

    # return the spline as a procedural curve
    if not source.IsInstanceOf(c4d.Ospline):
        real_spline = source.GetRealSpline()
        if real_spline is not None:
            return real_spline

    return source


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

    if input_spline.GetType() == c4d.Ospline:
        tangent_count = input_spline.GetTangentCount()
        spline_type = input_spline.GetInterpolationType()

    # allocate the resulting spline
    # TODO: Add support for segments
    result_spline = c4d.SplineObject(point_count, spline_type)
    if result_spline is None:
        return None

    # Offset & Set the Points
    input_spline_points = input_spline.GetAllPoints()
    for i in xrange(point_count):
        cur_pos = input_ml * input_spline_points[i]
        input_spline_points[i] = c4d.Vector(cur_pos.x, cur_pos.y + offset_value, cur_pos.z)
    result_spline.SetAllPoints(input_spline_points)

    # Set Tangents
    if tangent_count != 0:
        for i in xrange(point_count):
            cur_tangent = input_spline.GetTangent(i)
            result_spline.SetTangent(i, input_scale_rotate * cur_tangent["vl"], input_scale_rotate * cur_tangent["vr"])

    # return the computed spline
    return result_spline


def GetFirstActiveChild(op):
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
        return GetFirstActiveChild(child_obj)


def RecursiveCheckDirty(op):
    """Global function responsible to recursively check the dirty flag in a hierarchy"""

    res = 0

    if op is None:
        return res

    cur_obj = op
    next_obj = op.GetNext()
    child_obj = op.GetDown()

    res += cur_obj.GetDirty(c4d.DIRTYFLAGS_DATA | c4d.DIRTYFLAGS_MATRIX)

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

        self._child_dirty = None
        self._contour_child_dirty = None

        self.ResetDirtySums()

    def Init(self, op):
        """Establish default values for Dialog"""

        if op is None:
            return False

        bc = op.GetDataInstance()
        if bc is None:
            return False

        bc.SetInt32(c4d.PY_OFFSETYSPLINE_OFFSET, 100)

        return True

    def ResetDirtySums(self):
        self._child_dirty = -1
        self._contour_child_dirty = -1

    def CheckDirty(self, op, doc):
        """Returns True if op or its children are Dirty. (I think) It's only used for GetContour checks."""


        print "CheckDirty(%s)" % op.GetName()

        if (op is None) or (doc is None):
            return

        child_dirty = 0

        child = op.GetDown()

        if child is not None:
            child_dirty = RecursiveCheckDirty(child)

        if child_dirty != self._contour_child_dirty:
            op.SetDirty(c4d.DIRTYFLAGS_DATA)

        self._contour_child_dirty = child_dirty

    def GetResultSpline(self, child, child_spline, offset_value):
        if (child is None) or (child_spline is None) or (offset_value is None):
            return None

        # operate the spline modification
        result_spline = OffsetSpline(child_spline, offset_value)
        if result_spline is None:
            return None

        # For some reason it's very important that the next lines be here.
        # They dictate whether deeply nested clones will be updated appropriately.
        # Not sure if it's IsClosed() or GetRealSpline() that's doing it
        # Okay, it looks like it has something to do with GetRealSpline() updating the results of GetDirty for GetContour
        # Store now the closure state of the child cause child will be later on overwritten
        is_child_closed = IsClosed(child.GetRealSpline())  # child_ghc_clone is BaseObject instead of SplineObject

        # restore the closing status of the spline
        SetClosed(result_spline, is_child_closed)

        # copy the spline tags
        child_spline.CopyTagsTo(result_spline, True, c4d.NOTOK, c4d.NOTOK)

        # copy the spline parameters value
        CopySplineParamsValue(child_spline, result_spline)

        # notify about the generator update
        result_spline.Message(c4d.MSG_UPDATE)

        return result_spline

    @profile
    def GetVirtualObjects(self, op, hh):
        """Return the result of the generator."""

        print "GVO(%s)" % op.GetName()

        if op is None or hh is None:
            return None

        child_spline = None
        dirty = False

        cache = op.GetCache()
        bc = op.GetDataInstance()
        if bc is None:
            return None
        offset_value = bc.GetFloat(c4d.PY_OFFSETYSPLINE_OFFSET)

        # look for the first enabled child in order to support hierarchical
        child = GetFirstActiveChild(op)
        if child is None:
            self.ResetDirtySums()
            return None

        # Get the child objects as splines so we can manipulate them.
        # Note: Was a 2-step process in the example, but the first step always seemed to return Null
        result_ghc = op.GetAndCheckHierarchyClone(hh, child, c4d.HIERARCHYCLONEFLAGS_ASSPLINE, False)

        child_ghc_clone = None
        if result_ghc is not None:
            child_ghc_dirty = result_ghc["dirty"]  # BUG: Always True for some Reason
            child_ghc_clone = result_ghc["clone"]

        # recursively check the dirty flag for the children (deformers or other generators)
        child_dirty = -1
        if IsSplineCompatible(child_ghc_clone):
            child_dirty = RecursiveCheckDirty(child)
            if child_spline is None:
                child_spline = FinalSpline(child_ghc_clone)

        child.Touch()  # Doesn't seem to be necessary

        dirty |= op.IsDirty(c4d.DIRTYFLAGS_DATA)
        if dirty:
            print op.GetName() + " is dirty"

        # compare the dirtyness of local and member variable and accordingly update the generator's
        # dirty status and the member variable value
        # check is &= or |=
        dirty |= (self._child_dirty != child_dirty)

        print "self._child_dirty = %s   |   child_dirty = %s" % (self._child_dirty, child_dirty)
        if child_dirty != child_dirty:
            print "child is dirty"

        self._child_dirty = child_dirty

        if (not dirty) and (cache is not None):
            cache_clone = cache.GetClone(c4d.COPYFLAGS_NO_ANIMATION)  # We clone so that the cache is always alive
            return cache_clone

        return self.GetResultSpline(child, child_spline, offset_value)

    def GetContour(self, op, doc, lod, bt):
        print "GetContour(%s)" % op.GetName()

        if op is None:
            return None

        if doc is None:
            doc = op.GetDocument()

        if (doc is None) or (not doc.IsAlive()):
            doc = c4d.documents.GetActiveDocument()  # Is this safe in a render context?!

        if doc is None:
            return None

        bc = op.GetDataInstance()
        if bc is None:
            return None
        offset_value = bc.GetFloat(c4d.PY_OFFSETYSPLINE_OFFSET)

        child = GetFirstActiveChild(op)
        if child is None:
            self.ResetDirtySums()
            return None

        # Store now the closure state of the child cause child will be later on overwritten
        is_child_closed = IsClosed(child.GetRealSpline())

        # emulate the GetHierarchyClone in the GetContour by using the SendModelingCommand
        child_csto = None
        if child is not None:
            child_clone = child.GetClone(c4d.COPYFLAGS_NO_ANIMATION)
            if child_clone is None:
                return None

            csto_result = c4d.utils.SendModelingCommand(command=c4d.MCOMMAND_CURRENTSTATETOOBJECT, list=[child_clone], doc=doc)
            if csto_result is False:
                return None

            if isinstance(csto_result, list) and child_clone is not csto_result[0] and csto_result[0] is not None:
                child_csto = csto_result[0]
                if child_csto.GetType() == c4d.Onull:
                    join_result = c4d.utils.SendModelingCommand(command=c4d.MCOMMAND_JOIN, list=[child_clone], doc=doc)

                    if join_result is False:
                        return None

                    if isinstance(join_result, list) and join_result[0] is not None and child_clone is not join_result[0]:
                        child_csto = join_result[0]

        child_spline = None
        if IsSplineCompatible(child_csto):
            child_spline = FinalSpline(child_csto)

        return self.GetResultSpline(child, child_spline, offset_value)


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
