#!/usr/bin/env python3
"""生成测试fixtures数据文件"""

import os
import struct

# 创建fixtures目录
fixtures_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(fixtures_dir, exist_ok=True)

# H264 SPS (Sequence Parameter Set) - 720x1280分辨率
# NALU type = 7 (SPS), profile_idc=66 (Baseline), level_idc=30
h264_sps = bytes([
    0x00, 0x00, 0x00, 0x01,  # Start code
    0x67,  # NAL header: nal_unit_type=7 (SPS)
    0x42,  # profile_idc=66 (Baseline)
    0x00,  # constraint_set flags
    0x1E,  # level_idc=30
    0x90,  # seq_parameter_set_id=0, log2_max_frame_num_minus4=0
    0x8B, 0x60, 0x50, 0x1E, 0xD0, 0x80  # Additional SPS data for 720x1280
])

with open(os.path.join(fixtures_dir, 'sample_sps_h264.bin'), 'wb') as f:
    f.write(h264_sps)

# H264 PPS (Picture Parameter Set)
# NALU type = 8 (PPS)
h264_pps = bytes([
    0x00, 0x00, 0x00, 0x01,  # Start code
    0x68,  # NAL header: nal_unit_type=8 (PPS)
    0xCE, 0x38, 0x80  # PPS data
])

with open(os.path.join(fixtures_dir, 'sample_pps_h264.bin'), 'wb') as f:
    f.write(h264_pps)

# H265 VPS (Video Parameter Set)
# NALU type = 32 (VPS)
h265_vps = bytes([
    0x00, 0x00, 0x00, 0x01,  # Start code
    0x40, 0x01,  # NAL header: nal_unit_type=32 (VPS)
    0x0C, 0x01, 0xFF, 0xFF, 0x01, 0x60, 0x00, 0x00, 0x03, 0x00,
    0x90, 0x00, 0x00, 0x03, 0x00, 0x00, 0x03, 0x00, 0x5D, 0xAC, 0x09
])

with open(os.path.join(fixtures_dir, 'sample_vps_h265.bin'), 'wb') as f:
    f.write(h265_vps)

# H265 SPS (Sequence Parameter Set)
# NALU type = 33 (SPS)
h265_sps = bytes([
    0x00, 0x00, 0x00, 0x01,  # Start code
    0x42, 0x01,  # NAL header: nal_unit_type=33 (SPS)
    0x01, 0x01, 0x60, 0x00, 0x00, 0x03, 0x00, 0x90, 0x00, 0x00, 0x03,
    0x00, 0x00, 0x03, 0x00, 0x5D, 0xA0, 0x02, 0x80, 0x80, 0x2D, 0x16,
    0x80, 0x00, 0x00, 0x03, 0x00, 0x10, 0x00, 0x00, 0x03, 0x01, 0xE0,
    0x80
])

with open(os.path.join(fixtures_dir, 'sample_sps_h265.bin'), 'wb') as f:
    f.write(h265_sps)

# H265 PPS (Picture Parameter Set)
# NALU type = 34 (PPS)
h265_pps = bytes([
    0x00, 0x00, 0x00, 0x01,  # Start code
    0x44, 0x01,  # NAL header: nal_unit_type=34 (PPS)
    0xC1, 0x72, 0xB4, 0x62, 0x40  # PPS data
])

with open(os.path.join(fixtures_dir, 'sample_pps_h265.bin'), 'wb') as f:
    f.write(h265_pps)

# H264 测试帧 (IDR帧 - 关键帧)
# NALU type = 5 (IDR)
h264_frame = bytes([
    0x00, 0x00, 0x00, 0x01,  # Start code
    0x65,  # NAL header: nal_unit_type=5 (IDR)
    0x88, 0x80, 0x10, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00
] * 10)  # 重复数据模拟实际帧大小

with open(os.path.join(fixtures_dir, 'sample_frame_h264.bin'), 'wb') as f:
    f.write(h264_frame)

# H265 测试帧 (IDR帧 - 关键帧)
# NALU type = 19 (IDR_W_RADL)
h265_frame = bytes([
    0x00, 0x00, 0x00, 0x01,  # Start code
    0x26, 0x01,  # NAL header: nal_unit_type=19 (IDR_W_RADL)
    0x80, 0x10, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00
] * 10)

with open(os.path.join(fixtures_dir, 'sample_frame_h265.bin'), 'wb') as f:
    f.write(h265_frame)

# 模拟设备列表输出
device_list = """150100424a544434520325834abb4900    ohos    Device
7001005458323933328a027ce1873800    ohos    Device
"""

with open(os.path.join(fixtures_dir, 'sample_device_list.txt'), 'w') as f:
    f.write(device_list)

# 模拟HDC版本输出
hdc_version = """HDC version: 3.0.0.1
"""

with open(os.path.join(fixtures_dir, 'sample_hdc_version.txt'), 'w') as f:
    f.write(hdc_version)

# 模拟服务端配置包 (720x1280@30fps, bitrate=1500000, codec=h265)
config_packet = struct.pack('>I I I I', 720, 1280, 30, 1500000)
with open(os.path.join(fixtures_dir, 'sample_config_packet.bin'), 'wb') as f:
    f.write(config_packet)

print("测试fixtures数据文件已生成:")
for filename in ['sample_sps_h264.bin', 'sample_pps_h264.bin',
                 'sample_vps_h265.bin', 'sample_sps_h265.bin', 'sample_pps_h265.bin',
                 'sample_frame_h264.bin', 'sample_frame_h265.bin',
                 'sample_device_list.txt', 'sample_hdc_version.txt',
                 'sample_config_packet.bin']:
    filepath = os.path.join(fixtures_dir, filename)
    size = os.path.getsize(filepath)
    print(f"  {filename}: {size} bytes")