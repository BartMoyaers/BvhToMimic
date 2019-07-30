import json
import numpy as np
import math
from pyquaternion import Quaternion
from typing import List
from BvhChildren import BvhExtended
from tqdm import tqdm
from JointInfo import JointInfo
from BvhJoint import BvhJoint

class BvhJointHandler:
    """ Handles conversion of BVH files to DeepMimic format.
    """

    def __init__(self, mocap: BvhExtended, rigPath="./Rigs/humanoidRig.json", posLocked=False):
        self.mocap = mocap
        self.posLocked = posLocked

        # get json of humanoidRig
        with open(rigPath) as json_data:
            self.humanoidRig = json.load(json_data)

        # Sets up list of bones used by DeepMimic humanoid
        # Order is important
        self.deepMimicHumanoidJoints = ["seconds", "hip", "hip", "chest", "neck", "right hip", "right knee", "right ankle",
                                        "right shoulder", "right elbow", "left hip", "left knee", "left ankle", "left shoulder", "left elbow"]

        self.jointDimensions = [1, 3, 4, 4, 4, 4, 1, 4, 4, 1, 4, 1, 4, 4, 1]

        # Looking directly at the front of the DeepMimic model, X-axis points at you, Y-axis points straight up, Z-axis points left.
        # Image of correct deepMimic humanoid bind pose: https://user-images.githubusercontent.com/43953552/61379957-cb485c80-a8a8-11e9-8b78-24f4bf581900.PNG
        self.rotVecDict = {
            "seconds": [],
            "hip": [0, 0, 0],
            "hip": [0, 0, 0],
            "chest": [0, 1, 0],
            "neck": [0, 1, 0],
            "right hip": [0, -1, 0],
            "right knee": [0, -1, 0],
            "right ankle": [1, 0, 0],
            "right shoulder": [0, -1, 0],
            "right elbow": [0, -1, 0],
            "left hip": [0, -1, 0],
            "left knee": [0, -1, 0],
            "left ankle": [1, 0, 0],
            "left shoulder": [0, -1, 0],
            "left elbow": [0, -1, 0]
        }

        self.generateJointData()

        # Joint tree starting at root
        self.root = BvhJoint(self.mocap, self.humanoidRig[self.deepMimicHumanoidJoints[1]])

    def generateJointData(self):
        assert len(self.deepMimicHumanoidJoints) == len(self.jointDimensions)

        self.jointData = []

        for i in range(2, len(self.deepMimicHumanoidJoints)):
            deepMimicBoneName = self.deepMimicHumanoidJoints[i]
            bvhBoneName = self.bvhBoneName(deepMimicBoneName)
            jointInfo = JointInfo(
                deepMimicBoneName,
                bvhBoneName,
                self.jointDimensions[i],
                self.rotVecDict[deepMimicBoneName],
            )
            self.jointData.append(jointInfo)

    def generateKeyFrame(self, frameNumber: int):
        result = []
        # Update positions and transformation
        self.root.update(frameNumber)
        self.current_hip_rotation = self.getRootQuat()

        # Append Time
        result.append(self.mocap.frame_time)

        # Append hip root pos
        if self.posLocked:
            result.extend([2, 2, 2])
        else:
            result.extend(
                self.getJointTranslation(self.jointData[0])
            )

        # Append hip rotation
        result.extend(
            BvhJointHandler.quatBvhToDM(
                self.current_hip_rotation.elements
            )
        )

        # Append other rotations
        for joint in self.jointData[1:]:
            result.extend(self.getJointRotation(joint))

        return result

    def generateKeyFrames(self):
        keyFrames = []
        for i in tqdm(range(0, self.mocap.nframes)):
            keyFrames.append(self.generateKeyFrame(i))

        return keyFrames

    def bvhBoneName(self, deepMimicBoneName):
        return self.humanoidRig[deepMimicBoneName]

    def getJointOffset(self, bvhJointName):
        return list(self.mocap.joint_offset(bvhJointName))

    def getJointTranslation(self, jointInfo: JointInfo):
        return BvhJointHandler.posBvhToDM(
            self.root.getJointPosition(jointInfo.bvhName)
        )

    def getJointRotation(self, jointInfo: JointInfo) -> List[float]:
        joint = self.root.searchJoint(jointInfo.bvhName)
        if jointInfo.dimensions > 1:
            return self.calcRotation(joint, jointInfo)
        else:
            # 1D DeepMimic joint
            assert jointInfo.dimensions == 1
            # Get child position
            childPos = joint.getRelativeChildPosition()

            # rotate zeroRotVec with rootquat
            zeroRotVec = np.array(jointInfo.zeroRotVector)
            zeroVec = self.current_hip_rotation.rotate(zeroRotVec)

            # Calculate quaternion
            result = BvhJointHandler.calcQuatFromVecs(zeroVec, childPos)
            return [result.angle]

    def calcRotation(self, joint: BvhJoint, jointInfo: JointInfo):
        # Get vector from joint to child
        childPos = self.normalize(joint.getRelativeChildPosition())

        child = joint.children[0]
        if jointInfo.deepMimicName not in ["chest", "neck", "left ankle", "right ankle"]:
            # get child's child position
            childsChildPos = child.getRelativeChildPosition()

            y = -1 * childPos
            # TODO: check if vectors coincide
            x = self.normalize(np.cross(y, childsChildPos))
            z = self.normalize(np.cross(x, y))

            # Create rotation matrix from frame
            rot_mat = np.array([x, y, z]).T
            # Take base rotation into account
            zero_rot_mat = self.root.getTotalRotationMatrix()
            result = zero_rot_mat.T @ rot_mat
            return BvhJointHandler.quatBvhToDM(
                Quaternion(matrix=result)
            ).elements
        elif jointInfo.deepMimicName in ["left ankle", "right ankle"]:
            # get child's child position
            childsChildPos = child.getRelativeChildPosition()

            # Feet are pointed in Z direction TODO: find out why minus sign is needed
            z = -childPos
            x = self.normalize(np.cross(childsChildPos, z))
            y = self.normalize(np.cross(z, x))
            # Create rotation matrix from frame
            rot_mat = np.array([x, y, z]).T
            # Take base rotation into account
            zero_rot_mat = self.root.getTotalRotationMatrix()
            result = zero_rot_mat.T @ rot_mat
            return BvhJointHandler.quatBvhToDM(
                Quaternion(matrix=result)
            ).elements
        else:
            # rotate zeroRotVec with rootquat
            zeroRotVec = np.array(jointInfo.zeroRotVector)
            zeroVec = self.current_hip_rotation.rotate(zeroRotVec)

            # Calculate quaternion
            result = BvhJointHandler.calcQuatFromVecs(zeroVec, childPos)
            return BvhJointHandler.quatBvhToDM(result).elements

    def getRelativeJointTranslation(self, bvhJointName):
        joint = self.root.searchJoint(bvhJointName)
        return joint.getRelativeJointTranslation()

    def getRootQuat(self):
        # get left hip position
        root_left = BvhJointHandler.normalize(
            self.getRelativeJointTranslation(
                self.bvhBoneName("root rot left")
            )
        )

        # get spine "up" position (y axis in local root frame)
        y = BvhJointHandler.normalize(
            self.getRelativeJointTranslation(
                self.bvhBoneName("root rot up")
            )
        )

        # Create orthonormal frame
        z = BvhJointHandler.normalize(np.cross(root_left, y))
        x = BvhJointHandler.normalize(np.cross(y, z))

        # Create rotation matrix from frame
        rot_mat = np.array([x, y, z]).T

        # Create quaternion
        return Quaternion(matrix=rot_mat)

    @staticmethod
    def calcQuatFromVecs(v1, v2) -> Quaternion:
        v1 = BvhJointHandler.normalize(v1)
        v2 = BvhJointHandler.normalize(v2)

        # Calculate perpendicular vector
        perpvec = np.cross(v1, v2)
        perpnorm = np.linalg.norm(perpvec)
        if perpnorm > 0:
            perpvec = perpvec / perpnorm
            # Check for float slightly larger than 1
            temp = np.dot(v1, v2)
            if temp > 1:
                temp = 1.0
            angle = math.acos(temp)
        else:
            perpvec = np.array([1, 0, 0])
            angle = 0

        # Calculate quaternion from angle axis form.
        result = Quaternion(axis=perpvec, radians=angle)

        return result

    @staticmethod
    def normalize(vector):
        # Normalize a vector (create unit vector)
        norm = np.linalg.norm(vector)
        if norm != 1 and norm > 0:
            vector = vector / norm
        return vector

    @staticmethod
    def quatBvhToDM(quaternion: Quaternion) -> Quaternion:
        # transform x -> z and z -> -x
        return Quaternion(
            quaternion[0],
            quaternion[3],
            quaternion[2],
            -quaternion[1]
        )

    @staticmethod
    def posBvhToDM(translation: List[float]) -> List[float]:
        # transform x -> z and z -> -x
        return [
            translation[2],
            translation[1],
            -translation[0]
        ]