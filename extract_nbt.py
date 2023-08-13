from nbt import nbt
import os
import math
import json
import sys

FILE_PATH     = 'example.litematic'
PCD_FILE_PATH = "point_cloud.pcd"
CONFIG_PATH   = "config.json"

class ModelConverter:
    def __init__(self) -> None:
        global FILE_PATH, PCD_FILE_PATH
        self.model_size_x = 0
        self.model_size_y = 0
        self.model_size_z = 0
        self.block_stateC = 0
        self.renderPoints = []
        self.current_file_size = 0

        config = self.read_config_from_json(CONFIG_PATH)
        if config:
            print("配置信息:", config)
        FILE_PATH     = config["LitematicaFile"]
        PCD_FILE_PATH = config["OutputFile"]

        self.resolution = config["resolution"]
        self.cube_size  = config["cube_size"]
    
    def convert_64_to_32_bit_list(self,list_64bit):
        list_32bit = []
        for number in list_64bit:
            upper_32bit = (number >> 32) & 0xFFFFFFFF
            lower_32bit = number & 0xFFFFFFFF
            list_32bit.append(upper_32bit)
            list_32bit.append(lower_32bit)
        return list_32bit

    def reverse_bits(self,number, bit_length=64):
        result = 0
        for i in range(bit_length):
            result <<= 1
            result |= number & 1
            number >>= 1
        return result

    def reverse_list_and_bits(self, numbers):
        reversed_numbers = [self.reverse_bits(number) for number in numbers]
        return reversed_numbers

    def printBits(self, list):
        for element in list:
            binary_representation = format(element, '064b')
            print(binary_representation)

    def print_progress_bar(self, percentage):
        bar_length = 50
        progress = int(percentage * bar_length / 100)
        progress_bar = '=' * progress + ' ' * (bar_length - progress)
        sys.stdout.write('\r[{0}] {1}%'.format(progress_bar, percentage))
        sys.stdout.flush()

    def process_nbt_region_data(self, regionData, nbits):
        width  = self.model_size_x
        height = self.model_size_y
        depth  = self.model_size_z
        mask   = (1 << nbits) - 1
        y_shift = abs(width * depth)
        z_shift = abs(width)
        blocks = [[[0 for _ in range(abs(depth))] for _ in range(abs(height))] for _ in range(abs(width))]
        percent = 0
        self.print_progress_bar(0)

        for x in range(abs(width)):
            new_percent = int( 100*x / abs(width) )
            if new_percent > percent:
                percent = new_percent
                self.print_progress_bar(percent)
            for y in range(abs(height)):
                for z in range(abs(depth)):
                    index = y * y_shift + z * z_shift + x
                    start_offset     = index * nbits                       
                    start_arr_index  = start_offset >> 5                   
                    end_arr_index    = ((index + 1) * nbits - 1) >> 5      
                    start_bit_offset = start_offset & 0x1F                 
                    half_ind         = start_arr_index >> 1                
                    block            = regionData[half_ind]                

                    if (start_arr_index & 0x1) == 0:                       # 32bits索引为偶数
                        blockStart = block & 0xFFFFFFFF            
                        blockEnd   = (block >> 32) & 0xFFFFFFFF                   
                    else:                                                   
                        blockStart =  (block >> 32) & 0xFFFFFFFF                   
                        if half_ind + 1 < len(regionData):
                            blockEnd = regionData[half_ind + 1]  & 0xFFFFFFFF 
                        else:
                            blockEnd = 0x0

                    if start_arr_index == end_arr_index:
                        blocks[x][y][z] = (blockStart >> start_bit_offset) & mask

                    else:
                        end_offset = 32 - start_bit_offset  # num curtailed bits
                        val = ((blockStart >> start_bit_offset) & mask) | ((blockEnd << end_offset) & mask)
                        blocks[x][y][z] = val
        print(" Load finished.")

        points = []
        for x in range(abs(width)):
            for y in range(abs(height)):
                for z in range(abs(depth)):
                    if blocks[x][y][z] != 0:
                        points.append( (x,z,y) )
        return points

    def read_config_from_json(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                config = json.load(file)
                return config
        except FileNotFoundError:
            print("文件未找到:", file_path)
            return None
        except json.JSONDecodeError:
            print("JSON解码错误:", file_path)
            return None


    def read_litematic_file(self, file_path):
        try:
            litematic = nbt.NBTFile(file_path, 'rb')
        except:
            print("Cannot open "+file_path )
            return

        # 提取 Metadata
        metadata     = litematic["Metadata"]
        regions      = litematic["Regions"]["Unnamed"]

        block_states          = regions["BlockStates"]
        blockstate_palette    = regions["BlockStatePalette"]


        enclose_size = metadata["EnclosingSize"]
        author       = metadata["Author"]
        region_count = metadata["RegionCount"]
        total_blocks = metadata["TotalBlocks"]
        total_volume = metadata["TotalVolume"]
        

        self.model_size_x = enclose_size["x"].value
        self.model_size_y = enclose_size["y"].value
        self.model_size_z = enclose_size["z"].value


        print(f"作者：{author}")
        print(f"地图尺寸: [", self.model_size_x, ",", self.model_size_y, ",", self.model_size_z, "]")
        print(f"子区域数量：{region_count}")
        print(f"非空气方块数：{total_blocks}")
        print(f"总体积：{total_volume}")
        nbits  = max(2, math.ceil(math.log2(len(blockstate_palette))) )
        print(f"最大索引bit数:{nbits}")

        self.renderPoints = self.process_nbt_region_data( block_states , nbits)
    
    def convert_size(self,size_bytes):
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.log(size_bytes) / math.log(1000))
        p = math.pow(1000, i)
        s = round(size_bytes / p, 2)
        return "{}{}".format(s, size_name[i])
    
    def convertToPCD(self):
        with open(PCD_FILE_PATH, 'w') as f:

            count       = round(self.cube_size/self.resolution)
            point_count = len(self.renderPoints) * (count**3)

            # 写入头部
            f.write("VERSION .7\n")
            f.write("FIELDS x y z\n")
            f.write("SIZE 4 4 4\n")
            f.write("TYPE F F F\n")
            f.write("COUNT 1 1 1\n")
            f.write("WIDTH {}\n".format(point_count) )
            f.write("HEIGHT 1\n")
            f.write("VIEWPOINT 0 0 0 1 0 0 0\n")
            f.write("POINTS {}\n".format(point_count))
            f.write("DATA ascii\n")
            print("估计点云总点数: ", point_count)

            # 写入点数据
            real_point_count = 0
            half_size = self.cube_size/2
            for point in self.renderPoints:
                x = point[0] - half_size
                y = point[1] - half_size
                z = point[2] - half_size
                for dx in range(count):
                    for dy in range(count):
                        for dz in range(count):
                            px = x + dx*self.resolution
                            py = y + dy*self.resolution
                            pz = z + dz*self.resolution
                            f.write("{} {} {}\n".format(px , py, pz))
                            real_point_count += 1

            # 获取文件大小并转换为合适的格式
            file_size              = os.path.getsize(PCD_FILE_PATH)
            self.current_file_size = self.convert_size(file_size)
            print("实际点云总点数: ", real_point_count)

            return True
        return False


converter = ModelConverter()
converter.read_litematic_file(FILE_PATH)


