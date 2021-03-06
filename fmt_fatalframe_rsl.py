# coding=utf-8

# Grasshopper Manufacture (Wii) plugin by Zhenёq
# https://github.com/Zheneq/Noesis-Plugins

# Supported games:
#   Fatal Frame 4

from inc_noesis import *
import noesis
import rapi
import os
import lib_zq_nintendo_tex as nintex

debug = 0


def readMagic(bs, len = 4):
    try:
        return bs.readBytes(len).decode("ascii").split('\0')[0]
    except UnicodeDecodeError:
        return ''


def readRot(bs):
    r = NoeAngles([bs.readFloat() for j in range(3)]).toDegrees()
    r[0], r[1], r[2] = -r[0], r[2], r[1]
    return r.toQuat()


def readQuat(bs):
    r = [bs.readFloat() for j in range(4)]
    r[0], r[1], r[2], r[3] = r[1], r[2], r[3], r[0]
    return NoeQuat(r)


def readMat43(bs):
    m = [[bs.readFloat() for j in range(3)] for i in range(4)]
    return NoeMat43([m[1], m[2], m[3], m[0]])


def readList(bs, readData, isBidirected, outElemAddrList = None, outListNames = None):
    res = []
    next = bs.tell()
    while next:
        if outElemAddrList is not None:
            outElemAddrList.append(next)

        bs.seek(next)

        if outListNames is not None:
            outListNames.append(readMagic(bs, 8))

        if isBidirected:
            prev = bs.readUInt()

        next = bs.readUInt()
        res.append(readData(bs))
    return res


def registerNoesisTypes():
    handle = noesis.register("Grasshopper Manufacture Container", ".rsl")
    noesis.setHandlerTypeCheck(handle, rslCheckType)
    noesis.setHandlerLoadModel(handle, rslLoadModel)
#    noesis.setHandlerLoadRGBA(handle, rslLoadRGBA)  # scans the whole file for textures

    if debug:
        noesis.logPopup()
    return 1


def rslCheckType(data):
    return RSLFile(NoeBitStream(data)).check()


def rslLoadRGBA(data, texList):
    bs = NoeBitStream(data, NOE_BIGENDIAN)
    ptr = 0
    while ptr < bs.getSize():
        bs.seek(ptr)
        if readMagic(bs) == 'GCT0':
            bs.seek(ptr)
            tex = GCT0(bs)
            if tex.load():
                texList.append(tex.texture)

        ptr += 0x10

    return len(texList)


def rslLoadModel(data, mdlList):
    ctx = rapi.rpgCreateContext()
    RSLFile(NoeBitStream(data), mdlList).load()
    return len(mdlList)


class RSLFile:
    def __init__(self, bs, mdlList = None):
        self.bs = bs
        self.mdlList = mdlList
        self.root = None

    def check(self):
        return RMHG(self.bs, []).loadHeader()

    def load(self):
        self.root = RMHG(self.bs, self.mdlList)
        self.root.load()

        if debug:
            print("Structure:\nRoot {:#x} bytes".format(self.bs.getSize()))
            self.root.printStructure()


class RMHG:
    def __init__(self, bs, mdlList):
        self.bs = bs
        self.mdlList = mdlList
        self.records = []
        self.children = []

        self.parsers = {
            'RMHG': RMHG,
            'CGMG': CGMG,
            'GCT0': GCT0,
        }

    def printStructure(self, prefix = ""):
        for x in self.records:
            print("\t" + prefix, x['type'], "{:#x} bytes".format(x['size']))
            if x['type'] == "RMHG" and 'data' in x:
                x['data'].printStructure("\t" + prefix)

    def loadHeader(self):
        bs = self.bs
        bs.seek(0)

        if readMagic(bs) != "RMHG":
            return 0

        count = bs.readUInt()

        headerDataAddr = bs.readUInt()
        unk2 = bs.readUInt()
        dataSize = bs.readUInt() # ?

        bs.seek(headerDataAddr)
        self.records = [{
                'addr': bs.readUInt(),
                'size': bs.readUInt(),
                'unk': [bs.readUInt() for j in range(6)]  # unk[0] = 1 if nested rmhg and 0 otherwise ?
            } for i in range(count)]

        if not self.records and not dataSize:
            return 1
        if self.records and (self.records[-1]['addr'] + self.records[-1]['size'] + 0x1F) & 0xFFFFFFE0 == dataSize and dataSize <= bs.getSize():  # size is rounded up to 0x20
            return 1
        return 0

        # trailing data?

    def load(self):
        bs = self.bs
        self.loadHeader()
        for x in self.records:
            print("@{:#x}".format(x['addr']))
            bs.seek(x['addr'])
            x['type'] = readMagic(bs)
            if not x['addr'] or not x['size']:
                print("Empty", x['type'])
            elif x['type'] in self.parsers:
                print("Loading", x['type'])
                subBs = NoeBitStream(bs.getBuffer(x['addr'], x['addr'] + x['size']))
                x['data'] = self.parsers[x['type']](subBs, self.mdlList)
                x['data'].load()
            else:
                print("Cannot parse", x['type'])


class GCT0:
    def __init__(self, bs, mdlList = None):
        self.bs = bs
        bs.setEndian(NOE_BIGENDIAN)
        self.mdlList = mdlList
        self.texture = None

    def load(self):
        bs = self.bs
        ptr = bs.tell()

        if readMagic(bs) != 'GCT0':
            print("loadTexture failed!")
            return False

        dataFormat = bs.readUInt()
        width = bs.readUShort()
        height = bs.readUShort()
        unk = bs.readUInt()
        bufptr = bs.readUInt()

        bs.seek(ptr + bufptr)
        self.texture = nintex.readTexture(bs, width, height, dataFormat)

        if self.mdlList is not None:
            name = "tex_" + str(len(self.mdlList))
            self.texture.name = name
            self.mdlList.append(NoeModel(modelMats=NoeModelMaterials([self.texture], [NoeMaterial(name, name)])))

        return True


class GrasshopperModel:
    def __init__(self, bs, mdlList):
        self.bs = bs
        bs.setEndian(self.endian)
        self.mdlList  = mdlList
        self.texList  = []
        self.texTable = []
        self.matList  = []
        self.matTable = []
        self.sklList  = []
        self.sklTable = []
        self.meshList = []

    def resetRapi(self):
        rapi.rpgReset()
        rapi.rpgSetOption(noesis.RPGOPT_BIGENDIAN, self.endian == NOE_BIGENDIAN)
        rapi.rpgSetOption(noesis.RPGOPT_TRIWINDBACKWARD, self.bTriBackward)
        rapi.rpgSetOption(noesis.RPGOPT_MORPH_RELATIVEPOSITIONS, 1)

    def load(self):
        self.loadHeader()
        self.loadTextures()
        self.loadMaterials()
        self.loadSkeleton()
        self.loadMeshes()
        return True

    def loadHeader(self):
        bs = self.bs
        bs.seek(4)

        self.header = {
            'unk1':      [bs.readUInt() for i in range(5)],
            'boneCount': bs.readUShort(),
            'texCount':  bs.readUShort(),
            'someCount': bs.readUShort(),
            'matCount':  bs.readUShort(),
            'skelAddr':  bs.readUInt(),
            'texAddr':   bs.readUInt(),
            'someAddr':  bs.readUInt(),
            'matAddr':   bs.readUInt(),
            'unk2':      bs.readUInt(),
            'unk3':      bs.readUInt(),
            'name':      bs.readString()
        }
        if debug:
            print("header", self.header)

    def loadTextures(self):
        bs = self.bs
        self.texList  = []
        self.texTable = []

        texNames = []
        bs.seek(self.header['texAddr'])
        texs = readList(bs, lambda bs: {
            'addr': bs.readUInt(),
            'unk0': bs.readUInt(),
            'size': bs.readUInt(),  # zero in FF4
            'unk1': bs.readUInt(),
        }, True, self.texTable, texNames)

        # Making texture names unique
        for i in range(len(texNames)):
            if texNames.index(texNames[i]) != i:
                texNames[i] += str(i)

        if debug:
            print("Texs")
            for i in range(len(texs)):
                print('\t' + texNames[i] + ':', texs[i])

        if self.header['texCount'] != len(texs):
            print("GM::loadTextures - Wrong texture number!")

        for i in range(len(texs)):
            bs.seek(texs[i]['addr'])
            tex = GCT0(bs)
            if tex.load():
                tex.texture.name = texNames[i]
                self.texList.append(tex.texture)

        bs.setEndian(self.endian)

    def loadMaterials(self):
        bs = self.bs
        self.matList  = []
        self.matTable = []
        matNames = []

        bs.seek(self.header['matAddr'])
        if self.bComplexMaterials:
            mats = readList(bs, lambda bs: {
                    'unk0': bs.readUInt(),
                    'addr': bs.readUInt(),
                    'unk1': bs.readUInt(),
                    'unk2': bs.readUInt(),
                    'unks': [bs.readUInt() for j in range(8)],
                }, True, self.matTable, matNames)
        else:
            mats = readList(bs, lambda bs: {
                'unk0': bs.readUInt(),  # id?
                'addr': bs.readUInt(),
                'unk1': bs.readUInt(),  # 0
                'unk2': bs.readUInt(),  # 0
            }, True, self.matTable, matNames)

        if debug:
            print("Mats")
            for i in range(len(mats)):
                print('\t' + matNames[i] + ':', mats[i])

        if self.header['matCount'] != len(mats):
            print("GM::loadMaterials - Wrong material number!")

        for m in mats:
            if m['addr']:
                bs.seek(m['addr'])
                m['data'] = readList(bs, lambda bs: {
                    'texAddr': bs.readUInt(),
                    'unk2': bs.readUInt(),
                    'unks': [bs.readInt() for i in range(8)],
                }, True)

        for i in range(len(mats)):
            if 'data' in mats[i] and mats[i]['data'][0]['texAddr']:
                texId = self.texTable.index(mats[i]['data'][0]['texAddr'])
                texName = self.texList[texId].name
            else:
                texName = "no_texture"
            self.matList.append(NoeMaterial(matNames[i] + "_" + texName, texName))  # Material name can be not unique

    def loadSkeleton(self):
        bs = self.bs
        self.sklList  = []
        self.sklTable = []
        self.boneList = []

        bs.seek(self.header['skelAddr'])
        self.readSkeleton()

        # Resolving pointers into bone ids and names
        for b in self.sklList:
            for nAddr, nId, nName in (('parentAddr', '_parentId', '_parentName'),
                                      ('leftAddr',   '_leftId',   '_leftName'),
                                      ('rightAddr',  '_rightId',  '_rightName'),
                                      ('childAddr',  '_childId',  '_childName')):
                if b[nAddr]:
                    b[nId] = self.sklTable.index(b[nAddr])
                    b[nName] = self.sklList[b[nId]]['name']
                else:
                    b[nId] = -1
                    b[nName] = ""

        if debug:
            print("Bones")
            for i in range(len(self.sklList)):
                print('\t' + self.sklList[i]['name'] + ':', self.sklList[i])

        # Building NoeBones
        for i in range(len(self.sklList)):
            b = self.sklList[i]
            # if bone has a mesh, it's usually not actually a bone, more like mesh transform (unless the mesh is bound to a signle bone)
            name = b['name'] + ("_Mesh" if b['meshChunkHeadersAddr'] else "")
            bone = NoeBone(i, name, b['_mat'], parentIndex=b['_parentId'])
            self.boneList.append(bone)
        self.boneList = rapi.multiplyBones(self.boneList)

        # Making bone names unique (for conveniency)
        # Actually true bone names are unique, but the bones that are in fact just mesh transforms can have nonunique names
        boneNamesList = []
        for i in range(len(self.boneList)):
            if self.boneList[i].name in boneNamesList:
                self.boneList[i].name += '_' + str(i)
            else:
                boneNamesList.append(self.boneList[i].name)

    def readMeshBones(self, b):
        bs = self.bs
        chunkBoneGroupTable = []
        chunkBoneGroupListList = []
        if b['meshBonesAddr']:
            bs.seek(b['meshBonesAddr'])

            chunkBoneGroupListListAddrs = readList(bs, lambda bs: bs.readUInt(), True, chunkBoneGroupTable)
            chunkBoneGroupListAddrs = []
            for x in chunkBoneGroupListListAddrs:
                bs.seek(x)
                chunkBoneGroupListAddrs.append(readList(bs, lambda bs: bs.readUInt(), True))

            for chunkBoneGroupList in chunkBoneGroupListAddrs:
                t = []
                for boneGroupAddr in chunkBoneGroupList:
                    bs.seek(boneGroupAddr)

                    boneGroup = readList(bs, lambda bs: {
                        'boneAddr': bs.readUInt(),
                        'boneWeight': bs.readFloat()
                    }, True)

                    t.append({
                        'boneIndices': [self.sklTable.index(mb['boneAddr']) for mb in boneGroup],
                        'boneWeights': [mb['boneWeight'] for mb in boneGroup],
                    })
                chunkBoneGroupListList.append(t)

        return chunkBoneGroupTable, chunkBoneGroupListList


VB_BONEWEIGHT = 0
VB_POSITION = 9
VB_NORMAL = 10
VB_UV = 13
VB_UV2 = 14


class CGMG(GrasshopperModel):
    types = {
        0:  lambda bs: bs.readUByte(),  # weights
        1:  lambda bs: bs.readUByte(),  # ? always {0} + 0x1E
        9:  lambda bs: [bs.readFloat() for i in range(3)],  # verts
        10: lambda bs: [bs.readByte() / 0x40 for i in range(3)],  # normals
        11: lambda bs: [bs.readByte() for i in range(4)],  # ?
        12: lambda bs: [bs.readByte() for i in range(4)],  # ? 11 & 12 are sometimes the same
        13: lambda bs: [(bs.readUShort() % 0x400) / 0x400 for i in range(2)],  # uvs
        14: lambda bs: [(bs.readUShort() % 0x400) / 0x400 for i in range(2)],  # ? uvs 13 & 14 are sometimes the same
        15: lambda bs: [bs.readShort() for i in range(2)],  # ?
    }
    sizes = {
        0:  1,
        1:  1,
        9:  12,
        10: 3,
        11: 4,
        12: 4,
        13: 4,
        14: 4,
        15: 4,
    }

    def __init__(self, bs, mdlList):
        self.endian = NOE_BIGENDIAN
        GrasshopperModel.__init__(self, bs, mdlList)
        self.bComplexMaterials = True
        self.bTriBackward = True

    def readSkeleton(self):
        bs = self.bs
        for i in range(self.header['boneCount']):
            self.sklTable.append(bs.tell())
            self.sklList.append({
                'name': readMagic(bs, 8),
                'unk0': bs.readInt(),
                'meshBufferHeadersAddr': bs.readUInt(),
                'parentAddr': bs.readUInt(),
                'childAddr': bs.readUInt(),  # ?
                'leftAddr': bs.readUInt(),
                'rightAddr': bs.readUInt(),
                'meshChunkHeadersAddr': bs.readUInt(),
                'morphAddr': bs.readUInt(),
                'meshBonesAddr': bs.readUInt(),
                'pos': NoeVec3([bs.readFloat() for j in range(3)]),
                'rot': readRot(bs),
                'scl': NoeVec3([bs.readFloat() for j in range(3)]),
                'unk3': [bs.readFloat() for j in range(6)],
                'unkAddr2': bs.readUInt(),
                'meshAddr': bs.readUInt(),
                'unk4': bs.readInt(),
                'unkAddr3': bs.readUInt(),
                'unk5': bs.readUInt(),
                'unk6': bs.readUInt(),
            })

        # Building bone matrices
        for b in self.sklList:
            trans = NoeMat43().translate(b['pos'])
            scale = (NoeVec3((b['scl'][0], 0.0, 0.0)), NoeVec3((0.0, b['scl'][1], 0.0)),
                     NoeVec3((0.0, 0.0, b['scl'][2])), NoeVec3((0.0, 0.0, 0.0)))
            rot = b['rot'].toMat43()
            b['_mat'] = rot * scale * trans

    def loadMeshes(self):
        bs = self.bs
        self.meshList = []

        self.resetRapi()
        for boneId in range(len(self.sklList)):
            b = self.sklList[boneId]

            rapi.rpgClearBufferBinds()
            rapi.rpgSetName(b['name'])

            if debug:
                print()
                print(boneId, "-", b['name'])
                for x in b:
                    if 'Addr' in x:
                        print('\t', x, ":", "{:#x}".format(b[x]))
                    else:
                        print('\t', x, ":", b[x])
                print()

            if not b['meshChunkHeadersAddr']:
                continue

            ##########################################################

            chunkBoneGroupTable, chunkBoneGroupListList = self.readMeshBones(b)

            bs.seek(b['meshBufferHeadersAddr'])
            bufferHeaders = readList(bs, lambda bs: {
                'addr': bs.readUInt(),
                'stor': bs.readUByte(),  # 1 - embed, 2 - 1-byte index, 3 - 2-byte index
                'type': bs.readUByte(),
                'unks': [bs.readUByte() for i in range(6)],
            }, False)

            if debug:
                print("\tBuffer headers")
                for bh in bufferHeaders:
                    print('\t\t', bh)

            ##########################################################

            bs.seek(b['meshChunkHeadersAddr'])
            chunkHeaders = readList(bs, lambda bs: {
                'triAddr': bs.readUInt(),
                'matAddr': bs.readUInt(),
                'length': bs.readUShort(),
                'unk': bs.readUShort(),
                'boneAddr': bs.readUInt(),
            }, True)

            if debug:
                print("\tChunk headers")
                for chunkHeader in chunkHeaders:
                    print('\t\t', chunkHeader)

            ##########################################################

            morphHeaders = []
            morphNames = []
            if self.sklList[boneId]['morphAddr']:
                bs.seek(self.sklList[boneId]['morphAddr'])
                morphCount = bs.readUShort()
                bs.seek(6, NOESEEK_REL)
                morphHeadersAddr = bs.readUInt()

                bs.seek(morphHeadersAddr)
                morphHeaders = readList(bs, lambda bs: {
                    'unk0': bs.readFloat(),
                    'id': bs.readUByte(),
                    'unks': [bs.readUByte() for i in range(3)],
                    'addr': bs.readUInt(),
                    'junk': bs.readUInt(),
                }, True, None, morphNames)

                for morphHeader in morphHeaders:
                    length = (bs.getSize() - morphHeader['addr']) // 12  #TODO: Actual length?
                    rapi.rpgFeedMorphTargetPositions(bs.getBuffer(morphHeader['addr'], morphHeader['addr'] + length * 12), noesis.RPGEODATA_FLOAT, 12)
                    rapi.rpgCommitMorphFrame(length)
                rapi.rpgCommitMorphFrameSet()

            if debug:
                print("\tMorph headers")
                for i in range(len(morphHeaders)):
                    print('\t\t', morphNames[i], morphHeaders[i])

            ##########################################################

            for chunkHeader in chunkHeaders:
                materialName = self.matList[self.matTable.index(chunkHeader['matAddr'])].name
                rapi.rpgSetMaterial(materialName)
                rapi.rpgSetTransform(self.boneList[boneId].getMatrix())

                bs.seek(chunkHeader['triAddr'])
                self.readBuffers(bufferHeaders, boneId, chunkHeader['length'], chunkBoneGroupListList[chunkBoneGroupTable.index(chunkHeader['boneAddr'])] if chunkHeader['boneAddr'] else None)

            ##########################################################

        rapi.rpgOptimize()
        try:
            rcm = rapi.rpgConstructModel()
        except RuntimeError:
            # no geometry
            rcm = NoeModel()
        rcm.setModelMaterials(NoeModelMaterials(self.texList, self.matList))
        rcm.setBones(self.boneList)

        self.mdlList.append(rcm)

    def readBuffers(self, bufferHeaders, boneId, length, chunkBoneGroup):
        bs = self.bs
        tristripNum = 0
        maxIndex = -1

        if debug:
            print('\t\t\treadBuffers @ {:#x}'.format(bs.tell()))

        end = bs.tell() + length * 32

        while bs.tell() < end:
            if bs.readUByte() == 0x9F:
                tristripNum += 1
                count = bs.readUShort()

                rapi.immBegin(noesis.RPGEO_TRIANGLE_STRIP)

                for i in range(count):
                    for j in range(len(bufferHeaders)):
                        typ, stor = bufferHeaders[j]['type'], bufferHeaders[j]['stor']

                        if stor == 1:
                            # Embedded data
                            if typ in CGMG.types or debug:
                                data = CGMG.types[typ](bs)
                        else:
                            # Indexed data
                            if stor == 2:
                                idx = bs.readUByte()
                            elif stor == 3:
                                idx = bs.readUShort()
                            else:
                                raise ValueError("ReadBuffers - Unknown storage type")

                            # Position index is shared between morphs
                            if typ == VB_POSITION:
                                rapi.immVertMorphIndex(idx)

                                if idx > maxIndex:
                                    maxIndex = idx

                            # Load actual value by index
                            ptr = bs.tell()
                            bs.seek(bufferHeaders[j]['addr'] + idx * self.sizes[typ])
                            data = CGMG.types[typ](bs)
                            bs.seek(ptr)

                        # Feed to rpg (except for positions, which are fed last)
                        if typ == VB_POSITION:
                            pos = data
                        if typ == VB_BONEWEIGHT:
                            try:
                                vertBones = chunkBoneGroup[data // 3]
                                rapi.immBoneIndex(vertBones['boneIndices'])
                                rapi.immBoneWeight(vertBones['boneWeights'])
                            except IndexError:
                                print()
                                print("BONE MAPPING ERROR!")
                                for x in chunkBoneGroup:
                                    print(x)
                                print()
                                print('{:#x}'.format(bs.tell()))
                                print('data =', data)
                                if debug:
                                    raise
                        elif typ == VB_NORMAL:
                            rapi.immNormal3(data)
                        elif typ == VB_UV:
                            rapi.immUV2(data)
                        elif typ == VB_UV2:
                            rapi.immLMUV2(data)
                    rapi.immVertex3(pos)

                rapi.immEnd()

            else:
                break

        if debug:
            print('\t\t\treadBuffers: {} tristrips'.format(tristripNum))
            print('\t\t\t\t maxIndex = {}'.format(maxIndex))
