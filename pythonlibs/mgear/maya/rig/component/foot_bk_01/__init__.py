'''

    This file is part of MGEAR.

    MGEAR is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/lgpl.html>.

    Author:     Jeremie Passerin      geerem@hotmail.com
    Url:        http://www.jeremiepasserin.com
    Date:       2011 / 07 / 13

'''

## @package mgear.maya.rig.component.foot_bk_01
# @author Jeremie Passerin
#
#############################################
# GLOBAL
#############################################
# Maya
from pymel.core.general import *
from pymel.core.animation import *
from pymel.util import *
import pymel.core.datatypes as dt

# mgear
from mgear.maya.rig.component import MainComponent

import mgear.maya.primitive as pri
import mgear.maya.transform as tra
import mgear.maya.attribute as att
import mgear.maya.icon as ico
import mgear.maya.node as nod
import mgear.maya.vector as vec
import mgear.maya.applyop as aop


#############################################
# COMPONENT
#############################################
class Component(MainComponent):

    def addObjects(self):

        self.div_count = len(self.guide.apos) - 5

        plane = [self.guide.apos[0], self.guide.apos[-4], self.guide.apos[-3]]
        self.normal = self.getNormalFromPos(plane)
        self.binormal = self.getBiNormalFromPos(plane)

        # Heel ---------------------------------------------
        # bank pivot
        t = tra.getTransformLookingAt(self.guide.pos["heel"], self.guide.apos[-4], self.normal, "xz", self.negate)
        t = tra.setMatrixPosition(t, self.guide.pos["inpivot"])
        self.in_piv = pri.addTransform(self.root, self.getName("in_piv"), t)
        t = tra.setMatrixPosition(t, self.guide.pos["outpivot"])
        self.out_piv = pri.addTransform(self.in_piv, self.getName("out_piv"), t)

        # heel
        t = tra.getTransformLookingAt(self.guide.pos["heel"], self.guide.apos[-4], self.normal, "xz", self.negate)

        self.heel_loc = pri.addTransform(self.out_piv, self.getName("heel_loc"), t)
        att.setRotOrder(self.heel_loc, "YZX")
        self.heel_ctl = self.addCtl(self.heel_loc, "heel_ctl", t, self.color_ik, "sphere", w=self.size*.1)
        att.setKeyableAttributes(self.heel_ctl, self.r_params)

        # Tip ----------------------------------------------
        v = dt.Vector(self.guide.apos[-5].x,self.guide.apos[-1].y,self.guide.apos[-5].z)
        t = tra.setMatrixPosition(t, v)
        self.tip_ctl = self.addCtl(self.heel_ctl, "tip_ctl", t, self.color_ik, "circle", w=self.size)
        att.setKeyableAttributes(self.tip_ctl, self.r_params)

        # Roll ---------------------------------------------
        if self.settings["roll"] == 0:
            t = tra.getRotationFromAxis(self.y_axis, self.normal, "yz", self.negate)
            t = tra.setMatrixPosition(t, self.guide.pos["root"])

            self.roll_np = pri.addTransform(self.root, self.getName("roll_np"), t)
            self.roll_ctl = self.addCtl(self.roll_np, "roll_ctl", t, self.color_ik, "cylinder", w=self.size*.5, h=self.size*.5, ro=dt.Vector(3.1415*.5,0,0))
            att.setKeyableAttributes(self.roll_ctl, ["rx", "rz"])

        # Backward Controlers ------------------------------
        bk_pos = self.guide.apos[1:-3]
        bk_pos.reverse()
        parent = self.tip_ctl
        self.bk_ctl = []
        self.bk_loc = []
        for i, pos in enumerate(bk_pos):

            if i == 0:
                t = tra.getTransform(self.heel_ctl)
                t = tra.setMatrixPosition(t, pos)
            else:
                dir = bk_pos[i-1]
                t = tra.getTransformLookingAt(pos, dir, self.normal, "xz", self.negate)

            bk_loc = pri.addTransform(parent, self.getName("bk%s_loc"%i), t)
            bk_ctl = self.addCtl(bk_loc, "bk%s_ctl"%i, t, self.color_ik, "sphere", w=self.size*.15)
            att.setKeyableAttributes(bk_ctl, self.r_params)

            self.bk_loc.append(bk_loc)
            self.bk_ctl.append(bk_ctl)
            parent = bk_ctl

        # FK Reference ------------------------------------
        self.fk_ref = pri.addTransformFromPos(self.bk_ctl[-1], self.getName("fk_ref"), self.guide.apos[0])
        self.fk_npo = pri.addTransform(self.fk_ref, self.getName("fk0_npo"), tra.getTransform(self.bk_ctl[-1]))

        # Forward Controlers ------------------------------
        self.fk_ctl = []
        self.fk_loc = []
        parent = self.fk_npo
        for i, bk_ctl in enumerate(reversed(self.bk_ctl[1:])):
            t = tra.getTransform(bk_ctl)
            dist = vec.getDistance(self.guide.apos[i+1], self.guide.apos[i+2])

            # fk_npo = pri.addTransform(parent, self.getName("fk%s_npo"%i), t)
            fk_loc = pri.addTransform(parent, self.getName("fk%s_loc"%i), t)
            fk_ctl = self.addCtl(fk_loc, "fk%s_ctl"%i, t, self.color_fk, "cube", w=dist, h=self.size*.5, d=self.size*.5, po=dt.Vector(dist*.5*self.n_factor,0,0))
            att.setKeyableAttributes(fk_ctl)
            self.addShadow(fk_ctl, i)

            parent = fk_ctl
            self.fk_ctl.append(fk_ctl)
            self.fk_loc.append(fk_loc)

    def addAttributes(self):

        # Anim -------------------------------------------
        # Roll Angles
        if self.settings["roll"] == 1:
            self.roll_att = self.addAnimParam("roll", "Roll", "double", 0, -180, 180)
            self.bank_att = self.addAnimParam("bank", "Bank", "double", 0, -180, 180)

        self.angles_att = [ self.addAnimParam("angle_%s"%i, "Angle %s"%i, "double", -20) for i in range(self.div_count) ]

        # Setup ------------------------------------------
        self.blend_att = self.addSetupParam("blend", "Fk/Ik Blend", "double", 1, 0, 1)

    def addOperators(self):

        # Visibilities -------------------------------------

        # ik
        if self.settings["roll"] == 0:
            for shp in self.roll_ctl.getShapes():
                connectAttr(self.blend_att, shp.attr("visibility"))
        for bk_ctl in self.bk_ctl:
            for shp in bk_ctl.getShapes():
                connectAttr(self.blend_att, shp.attr("visibility"))

        for shp in self.heel_ctl.getShapes():
            connectAttr(self.blend_att, shp.attr("visibility"))
        for shp in self.tip_ctl.getShapes():
            connectAttr(self.blend_att, shp.attr("visibility"))

        # Roll / Bank --------------------------------------
        if self.settings["roll"] == 0: # Using the controler
            self.roll_att = self.roll_ctl.attr("rz")
            self.bank_att = self.roll_ctl.attr("rx")

        # heel roll and bank
        if self.negate:
            inpiv_nod = nod.createAddNode(self.bank_att, self.in_piv.getAttr("rx"))
            clamp_node = nod.createClampNode([self.roll_att, self.bank_att, inpiv_nod+".output"], [0, -180, -180], [180,0,0])
        else:
            clamp_node = nod.createClampNode([self.roll_att, self.bank_att, self.bank_att], [0, -180, 0], [180,0,180])
        inAdd_nod = nod.createAddNode(clamp_node+".outputB", getAttr(self.in_piv.attr("rx")) *  self.n_factor) 
           
        connectAttr(clamp_node+".outputR", self.heel_loc.attr("rz"))
        connectAttr(clamp_node+".outputG", self.out_piv.attr("rx"))
        connectAttr(inAdd_nod+".output", self.in_piv.attr("rx"))

        # Reverse Controler offset -------------------------
        angle_outputs = nod.createAddNodeMulti(self.angles_att)
        for i, bk_loc in enumerate(reversed(self.bk_loc)):

            if i == 0 : # First
                input = self.roll_att
                min_input = self.angles_att[i]

            elif i == len(self.angles_att): # Last
                sub_nod = nod.createSubNode(self.roll_att, angle_outputs[i-1])
                input = sub_nod+".output"
                min_input = -360

            else: # Others
                sub_nod = nod.createSubNode(self.roll_att, angle_outputs[i-1])
                input = sub_nod+".output"
                min_input = self.angles_att[i]

            clamp_node = nod.createClampNode(input, min_input, 0)
            add_node = nod.createAddNode(clamp_node+".outputR", bk_loc.getAttr("rz"))
            connectAttr(add_node+".output", bk_loc.attr("rz"))

        # Reverse compensation -----------------------------
        for i, fk_loc in enumerate(self.fk_loc):
            bk_ctl = self.bk_ctl[-i-1]
            bk_loc = self.bk_loc[-i-1]
            fk_ctl = self.fk_ctl[i]

            # Inverse Rotorder
            node = aop.gear_inverseRotorder_op(bk_ctl, fk_ctl)
            connectAttr(node+".output", bk_loc.attr("ro"))
            connectAttr(fk_ctl.attr("ro"), fk_loc.attr("ro"))


            # Compensate the backward rotation
            # ik
            addx_node = nod.createAddNode(bk_ctl.attr("rx"), bk_loc.attr("rx"))
            addy_node = nod.createAddNode(bk_ctl.attr("ry"), bk_loc.attr("ry"))
            addz_node = nod.createAddNode(bk_ctl.attr("rz"), bk_loc.attr("rz"))
            addz_node = nod.createAddNode(addz_node+".output", -bk_loc.getAttr("rz") - fk_loc.getAttr("rz"))

            neg_node = nod.createMulNode([addx_node+".output",addy_node+".output",addz_node+".output"], [-1,-1,-1])
            ik_outputs = [neg_node+".outputX", neg_node+".outputY", neg_node+".outputZ"]

            # fk
            fk_outputs = [0,0,fk_loc.getAttr("rz")]

            # blend
            blend_node = nod.createBlendNode(ik_outputs, fk_outputs, self.blend_att)
            connectAttr(blend_node+".output", fk_loc.attr("rotate"))

        return

    # =====================================================
    # CONNECTOR
    # =====================================================
    ## Set the relation beetween object from guide to rig.\n
    # @param self
    def setRelation(self):
        self.relatives["root"] = self.root
        self.relatives["heel"] = self.root
        self.relatives["inpivot"] = self.root
        self.relatives["outpivot"] = self.root

        for i in range(self.div_count):
            self.relatives["%s_loc"%i] = self.fk_ctl[i]

        if self.div_count > 0:
            self.relatives["%s_loc"%self.div_count] = self.fk_ctl[-1]

    ## Add more connection definition to the set.
    # @param self
    def addConnection(self):
        self.connections["leg_2jnt_01"] = self.connect_leg_2jnt_01
        self.connections["leg_3jnt_01"] = self.connect_leg_3jnt_01

    ## leg connection definition.
    # @param self
    def connect_leg_2jnt_01(self):
        # If the parent component hasn't been generated we skip the connection
        if self.parent_comp is None:
            return

        ## DIRTY TEMP
        # b_attr = pri.findChild(self.model, self.parent_comp.fullName+"_root")
        # b_attr += "."+self.parent_comp.fullName+"_blend"

        connectAttr(self.parent_comp.blend_att, self.blend_att)
        # connectAttr(b_attr, self.blend_att)
        parent(self.root, self.parent_comp.ik_ctl)
        parent(self.parent_comp.ik_ref, self.bk_ctl[-1])
        # parent(self.fk_ref, self.parent_comp.tws2_rot)
        parentConstraint(self.parent_comp.tws2_rot, self.fk_ref, maintainOffset=True)

        return

    ## leg connection definition.
    # @param self
    def connect_leg_3jnt_01(self):
        # If the parent component hasn't been generated we skip the connection
        if self.parent_comp is None:
            return

        connectAttr(self.parent_comp.blend_att, self.blend_att)
        parent(self.root, self.parent_comp.ik_ctl)
        parent(self.parent_comp.ik_ref, self.bk_ctl[-1])
        parent(self.fk_ref, self.parent_comp.tws3_rot)
        parentConstraint(self.parent_comp.tws2_rot, self.fk_ref, maintainOffset=True)

        return
