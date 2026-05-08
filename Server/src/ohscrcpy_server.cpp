/*
 * Copyright (c) 2026 luodh0157.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
 
/* OHScrcpy 服务端实现 - 基于OpenHarmony C-API */

#include "../include/logger.h"

#include <iostream>
#include <thread>
#include <atomic>
#include <memory>
#include <vector>
#include <cstring>
#include <charconv>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <signal.h>
#include <chrono>
#include <mutex>
#include <queue>
#include <condition_variable>
#include <getopt.h>

// OpenHarmony多媒体C-API头文件
#include <native_avscreen_capture.h>
#include <native_avscreen_capture_base.h>
#include <native_avscreen_capture_errors.h>
#include <native_avcodec_videoencoder.h>
#include <native_avcodec_base.h>
#include <native_avformat.h>
#include <native_avbuffer.h>
#include <native_avcapability.h>
#include <native_buffer.h>
#include <display_manager.h>
#include <cstring>

// 网络相关头文件
#include <netinet/tcp.h>

// 常量定义
#define DEFAULT_PORT 27183
#define DEFAULT_FPS 30
#define DEFAULT_BITRATE 1500000  // 1.5 Mbps
#define DEFAULT_WIDTH 720
#define DEFAULT_HEIGHT 1280
#define MAX_CLIENTS 1

// 数据包类型定义
#define PACKET_TYPE_HEARTBEAT      0x00000000
#define PACKET_TYPE_SPS            0x00000001
#define PACKET_TYPE_PPS            0x00000002
#define PACKET_TYPE_KEYFRAME       0x00000003
#define PACKET_TYPE_FRAME          0x00000004
#define PACKET_TYPE_CONFIG         0x00000005
#define PACKET_TYPE_VPS            0x00000006
#define PACKET_TYPE_CONFIG_DATA    0x00000007
#define PACKET_TYPE_LOG            0x00000008

// 日志文件路径前缀
#define LOG_FILE_PREFIX "/data/local/tmp/server_"

// 版本信息
#define VERSION "v2.1"

// H.264 NALU类型
enum H264NaluType {
    NALU_TYPE_SPS = 7,
    NALU_TYPE_PPS = 8,
    NALU_TYPE_IDR = 5,
    NALU_TYPE_SEI = 6,
    NALU_TYPE_NON_IDR = 1
};

// H.265 NALU类型
enum H265NaluType {
    H265_NALU_TYPE_VPS = 32,
    H265_NALU_TYPE_SPS = 33,
    H265_NALU_TYPE_PPS = 34,
    H265_NALU_TYPE_IDR_W = 19,
    H265_NALU_TYPE_IDR_N = 20,
    H265_NALU_TYPE_CRA = 21
};

using namespace OHOS;
using namespace OHOS::Rosen;
using namespace OHScrcpy;

// 全局控制标志
std::atomic<bool> g_running(false);
std::atomic<bool> g_client_connected(false);
std::atomic<bool> g_streaming(false);

// 信号处理
void signal_handler(int signum) {
    LOG_INFO("Server", "Received signal " + std::to_string(signum) + ", shutting down...");
    g_running = false;
    g_streaming = false;
}

// 屏幕信息结构
struct ScreenInfo {
    int32_t width = DEFAULT_WIDTH;
    int32_t height = DEFAULT_HEIGHT;
    int32_t fps = DEFAULT_FPS;
    int32_t bitrate = DEFAULT_BITRATE;
    uint64_t displayid = 0;
    std::string codec = "h264";
};

// 命令行参数结构
struct CommandLineArgs {
    int32_t port = DEFAULT_PORT;
    int32_t width = DEFAULT_WIDTH;
    int32_t height = DEFAULT_HEIGHT;
    int32_t framerate = DEFAULT_FPS;
    int32_t bitrate = DEFAULT_BITRATE;
    bool show_help = false;
    bool show_version = false;
    bool log_enabled = false;
};

// 视频流消息包头
struct VideoPacketHeader {
    int32_t packet_type;
    int32_t packet_size;
};

// 网络传输类
class NetworkStreamer {
public:
    NetworkStreamer() : server_fd_(-1), client_fd_(-1), last_heartbeat_time_(std::chrono::steady_clock::now()) {
        memset(&client_addr_, 0, sizeof(client_addr_));
    }
    ~NetworkStreamer() { closeAll(); }
    
    bool initialize(int port) {
        if (server_fd_ >= 0) {
            LOG_INFO("Server", "NetworkStreamer has been initialized");
            return true;
        }
        
        // 创建socket
        server_fd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd_ < 0) {
            LOG_ERROR("Server", "Failed to create socket: " + std::string(strerror(errno)));
            return false;
        }
        
        // 设置socket选项
        int opt = 1;
        if (setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
            LOG_ERROR("Server", "Failed to set SO_REUSEADDR: " + std::string(strerror(errno)));
        }
        
        // 设置非阻塞
        fcntl(server_fd_, F_SETFL, O_NONBLOCK);
        
        // 绑定地址
        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = htonl(INADDR_ANY);
        addr.sin_port = htons(port);
        
        if (bind(server_fd_, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
            LOG_ERROR("Server", "Failed to bind socket: " + std::string(strerror(errno)));
            return false;
        }
        
        // 开始监听
        if (listen(server_fd_, MAX_CLIENTS) < 0) {
            LOG_ERROR("Server", "Failed to listen on socket: " + std::string(strerror(errno)));
            return false;
        }
        
        LOG_INFO("Server", "Network streamer initialized on port " + std::to_string(port));
        return true;
    }
    
    bool acceptClient() {
        if (client_fd_ >= 0) {
            return true;
        }
        
        socklen_t addr_len = sizeof(client_addr_);
        client_fd_ = accept(server_fd_, (struct sockaddr*)&client_addr_, &addr_len);
        
        if (client_fd_ < 0) {
            if (errno != EWOULDBLOCK && errno != EAGAIN) {
                LOG_ERROR("Server", "Failed to accept client: " + std::string(strerror(errno)));
            }
            return false;
        }
        
        // 设置客户端socket选项
        int opt = 1;
        setsockopt(client_fd_, IPPROTO_TCP, TCP_NODELAY, &opt, sizeof(opt));
        
        // 设置非阻塞
        fcntl(client_fd_, F_SETFL, O_NONBLOCK);
        
        char client_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr_.sin_addr, client_ip, sizeof(client_ip));
        LOG_INFO("Server", "++++++++++++++++++++++++++++++++++++++++++++++++++++++");
        LOG_INFO("Server", "Client connected from " + std::string(client_ip) + ":" + std::to_string(ntohs(client_addr_.sin_port)));
        
        g_client_connected = true;
        last_heartbeat_time_ = std::chrono::steady_clock::now();
        return true;
    }
    
    bool checkConnection() {
        if (client_fd_ < 0) return false;
        
        // 使用MSG_PEEK检查socket是否可读
        char buf[1];
        ssize_t n = recv(client_fd_, buf, sizeof(buf), MSG_PEEK | MSG_DONTWAIT);
        
        if (n == 0) {
            LOG_INFO("Server", "Client closed connection");
            disconnectClient();
            return false;
        } else if (n < 0) {
            if (errno != EWOULDBLOCK && errno != EAGAIN) {
                LOG_INFO("Server", "Socket error: " + std::string(strerror(errno)));
                disconnectClient();
                return false;
            }
        }
        
        return true;
    }
    
    bool sendData(const void* data, size_t size) {
        if (client_fd_ < 0) {
            LOG_ERROR("Server", "Invalid client fd");
            return false;
        }

        // 先检查连接状态
        if (!checkConnection()) {
            return false;
        }
        
        size_t total_sent = 0;
        while (total_sent < size) {
            ssize_t sent = send(client_fd_, (const char*)data + total_sent, 
                               size - total_sent, MSG_NOSIGNAL);
            if (sent < 0) {
                if (errno == EWOULDBLOCK || errno == EAGAIN) {
                    LOG_INFO("Server", "Buffer is full, wait a moment...");
                    usleep(1000);
                    continue;
                } else {
                    LOG_ERROR("Server", "Failed to send data: " + std::string(strerror(errno)));
                    disconnectClient();
                    return false;
                }
            }
            
            total_sent += sent;
        }
        
        return true;
    }
    
    bool sendPacket(const void* data, size_t size, uint32_t packet_type) {
        // 记录发送的包类型
        const char* type_name = "";
        switch(packet_type) {
            case PACKET_TYPE_HEARTBEAT: type_name = "HEARTBEAT"; break;
            case PACKET_TYPE_SPS: type_name = "SPS"; break;
            case PACKET_TYPE_PPS: type_name = "PPS"; break;
            case PACKET_TYPE_KEYFRAME: type_name = "KEYFRAME"; break;
            case PACKET_TYPE_FRAME: type_name = "FRAME"; break;
            case PACKET_TYPE_CONFIG: type_name = "CONFIG"; break;
            case PACKET_TYPE_CONFIG_DATA: type_name = "CONFIG_DATA"; break;
            default: type_name = "UNKNOWN"; break;
        }
        if (packet_type != PACKET_TYPE_HEARTBEAT) {
            LOG_INFO("Server", "Send packet: type=" + std::string(type_name) + ", size=" + std::to_string(size) + " bytes");
        }

        VideoPacketHeader header = {
            .packet_type = htonl(packet_type),
            .packet_size = htonl(size)
        };
        if (!sendData(&header, sizeof(header))) return false;
        if (!sendData(data, size)) return false;
        
        return true;
    }
    
    bool sendVideoConfig(const ScreenInfo& info) {
        // 发送视频配置信息
        uint32_t config_data[4];
        config_data[0] = htonl(info.width);
        config_data[1] = htonl(info.height);
        config_data[2] = htonl(info.fps);
        config_data[3] = htonl(info.bitrate);
        
        return sendPacket(config_data, sizeof(config_data), PACKET_TYPE_CONFIG);
    }
    
    bool sendConfig(const ScreenInfo& info) {
        std::string config_str = "SCREEN_INFO:" +
            std::to_string(info.width) + ":" +
            std::to_string(info.height) + ":" +
            std::to_string(info.fps) + ":" +
            std::to_string(info.bitrate) + ":" +
            info.codec +  "\n";

        bool succ = sendData(config_str.c_str(), config_str.length());
        if (succ) {
            LOG_INFO("Server", "sendConfig to client succ, " + config_str);
        } else {
            LOG_INFO("Server", "sendConfig to client fail, " + config_str);
        }
        return succ;
    }
    
    bool receiveAck(int timeout_ms = 5000) {
        if (client_fd_ < 0) return false;
        
        char buffer[256];
        auto start_time = std::chrono::steady_clock::now();
        
        while (std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now() - start_time).count() < timeout_ms) {
            ssize_t received = recv(client_fd_, buffer, sizeof(buffer) - 1, 0);
            
            if (received > 0) {
                buffer[received] = '\0';
                if (parseConfigAck(buffer, received)) {
                    return true;
                }
            } else if (received < 0 && errno != EWOULDBLOCK && errno != EAGAIN) {
                LOG_ERROR("Server", "receiveAck fail, received:" + std::to_string(received) + " errno:" + std::to_string(errno));
                break;
            }
            usleep(5000);  // 5ms
        }
        
        return false;
    }

    bool parseConfigAck(char *buffer, size_t size) {
        char *cfg_ack = strstr(buffer, "CONFIG_ACK");
        if (cfg_ack == nullptr) {
            LOG_ERROR("Server", "invalid ACK: no include CONFIG_ACK");
            return false;
        }
        return true;
    }
    
    void sendHeartbeat() {
        if (hasClient()) {
            static uint32_t heartbeat_counter = 0;
            heartbeat_counter++;
            uint32_t net_counter = htonl(heartbeat_counter);
            
            if (!sendPacket(&net_counter, sizeof(heartbeat_counter), PACKET_TYPE_HEARTBEAT)) {
                LOG_INFO("Server", "Failed to send heartbeat, connection may be lost");
            }
            
            last_heartbeat_time_ = std::chrono::steady_clock::now();
        }
    }
    
    void disconnectClient() {
        if (client_fd_ >= 0) {
            close(client_fd_);
            client_fd_ = -1;
            memset(&client_addr_, 0, sizeof(client_addr_));
        }
        g_client_connected = false;
        LOG_INFO("Server", "Client disconnected");
    }
    
    void closeAll() {
        disconnectClient();
        if (server_fd_ >= 0) {
            close(server_fd_);
            server_fd_ = -1;
        }
    }
    
    bool hasClient() const { return client_fd_ >= 0; }
    
    auto getLastHeartbeatTime() const { return last_heartbeat_time_; }
    
private:
    int server_fd_;
    int client_fd_;
    struct sockaddr_in client_addr_;
    std::chrono::steady_clock::time_point last_heartbeat_time_;
};

// H.264工具函数
class H264Utils {
public:
    // 从H.264数据中提取SPS和PPS（Annex-B格式）
    static bool extractSpsPpsAnnexB(const uint8_t* data, size_t size, 
                                    std::vector<uint8_t>& sps, std::vector<uint8_t>& pps) {
        sps.clear();
        pps.clear();
        
        if (size < 4) return false;
        
        size_t pos = 0;
        bool found_sps = false;
        bool found_pps = false;
        
        while (pos + 4 < size) {
            // 查找起始码 0x00000001 或 0x000001
            bool found_start = false;
            size_t start_len = 0;
            
            if (data[pos] == 0x00 && data[pos+1] == 0x00 && 
                data[pos+2] == 0x00 && data[pos+3] == 0x01) {
                found_start = true;
                start_len = 4;
            } else if (data[pos] == 0x00 && data[pos+1] == 0x00 && 
                      data[pos+2] == 0x01) {
                found_start = true;
                start_len = 3;
            }
            
            if (found_start) {
                size_t nalu_start = pos + start_len;
                if (nalu_start >= size) break;
                
                // 获取NALU类型
                uint8_t nalu_type = data[nalu_start] & 0x1F;
                
                // 查找下一个起始码
                size_t next_start = pos + start_len;
                while (next_start + 3 < size) {
                    if (data[next_start] == 0x00 && data[next_start+1] == 0x00 && 
                        data[next_start+2] == 0x01) {
                        break;
                    } else if (next_start + 4 < size && 
                              data[next_start] == 0x00 && data[next_start+1] == 0x00 && 
                              data[next_start+2] == 0x00 && data[next_start+3] == 0x01) {
                        break;
                    }
                    next_start++;
                }
                
                size_t nalu_end = (next_start + 3 < size) ? next_start : size;
                
                // 提取NALU数据（包含起始码）
                std::vector<uint8_t> nalu(data + pos, data + nalu_end);
                
                if (nalu_type == NALU_TYPE_SPS) {
                    sps = std::move(nalu);
                    found_sps = true;
                    LOG_INFO("Server", "Found SPS: " + std::to_string(sps.size()) + " bytes");
                } else if (nalu_type == NALU_TYPE_PPS) {
                    pps = std::move(nalu);
                    found_pps = true;
                    LOG_INFO("Server", "Found PPS: " + std::to_string(pps.size()) + " bytes");
                }
                
                pos = nalu_end;
            } else {
                pos++;
            }
            
            if (found_sps && found_pps) {
                return true;
            }
        }
        
        return found_sps && found_pps;
    }
    
    // 检查是否为关键帧
    static bool isKeyFrame(const uint8_t* data, size_t size) {
        if (size < 5) return false;
        
        size_t offset = 0;
        // 查找起始码
        if (size >= 4 && data[0] == 0x00 && data[1] == 0x00 && 
            data[2] == 0x00 && data[3] == 0x01) {
            offset = 4;
        } else if (size >= 3 && data[0] == 0x00 && data[1] == 0x00 && 
                  data[2] == 0x01) {
            offset = 3;
        }
        
        if (offset >= size) return false;
        
        uint8_t nalu_type = data[offset] & 0x1F;
        return nalu_type == NALU_TYPE_IDR;
    }
};

// H.265工具函数
class H265Utils {
public:
    // 从H.265数据中提取VPS、SPS、PPS（Annex-B格式）
    static bool extractVpsSpsPpsAnnexB(const uint8_t* data, size_t size,
                                       std::vector<uint8_t>& vps,
                                       std::vector<uint8_t>& sps,
                                       std::vector<uint8_t>& pps) {
        vps.clear();
        sps.clear();
        pps.clear();
        
        if (size < 4) return false;
        
        size_t pos = 0;
        bool found_vps = false, found_sps = false, found_pps = false;
        
        while (pos + 4 < size) {
            size_t start_len = 0;
            bool found_start = false;
            
            if (data[pos] == 0x00 && data[pos+1] == 0x00 && 
                data[pos+2] == 0x00 && data[pos+3] == 0x01) {
                found_start = true;
                start_len = 4;
            } else if (data[pos] == 0x00 && data[pos+1] == 0x00 && 
                      data[pos+2] == 0x01) {
                found_start = true;
                start_len = 3;
            }
            
            if (found_start) {
                size_t nalu_start = pos + start_len;
                if (nalu_start >= size) break;
                
                uint8_t nalu_type = (data[nalu_start] & 0x7E) >> 1;
                
                size_t next_start = nalu_start + 1;
                while (next_start + 3 < size) {
                    if (data[next_start] == 0x00 && data[next_start+1] == 0x00 &&
                        (data[next_start+2] == 0x01 || 
                         (data[next_start+2] == 0x00 && next_start+4 < size && 
                          data[next_start+3] == 0x01))) {
                        break;
                    }
                    next_start++;
                }
                
                size_t nalu_end = (next_start + 3 < size) ? next_start : size;
                std::vector<uint8_t> nalu(data + pos, data + nalu_end);
                
                if (nalu_type == H265_NALU_TYPE_VPS) {
                    vps = std::move(nalu);
                    found_vps = true;
                    LOG_INFO("Server", "Found VPS: " + std::to_string(vps.size()) + " bytes");
                } else if (nalu_type == H265_NALU_TYPE_SPS) {
                    sps = std::move(nalu);
                    found_sps = true;
                    LOG_INFO("Server", "Found SPS: " + std::to_string(sps.size()) + " bytes");
                } else if (nalu_type == H265_NALU_TYPE_PPS) {
                    pps = std::move(nalu);
                    found_pps = true;
                    LOG_INFO("Server", "Found PPS: " + std::to_string(pps.size()) + " bytes");
                }
                
                pos = nalu_end;
                
                if (found_vps && found_sps && found_pps) {
                    return true;
                }
            } else {
                pos++;
            }
        }
        
        return found_vps && found_sps && found_pps;
    }
    
    static bool isKeyFrame(const uint8_t* data, size_t size) {
        if (size < 5) return false;
        
        size_t offset = 0;
        if (data[0] == 0x00 && data[1] == 0x00) {
            if (data[2] == 0x00 && data[3] == 0x01) {
                offset = 4;
            } else if (data[2] == 0x01) {
                offset = 3;
            }
        }
        
        if (offset >= size) return false;
        
        uint8_t nalu_type = (data[offset] & 0x7E) >> 1;
        return nalu_type == H265_NALU_TYPE_IDR_W || 
               nalu_type == H265_NALU_TYPE_IDR_N || 
               nalu_type == H265_NALU_TYPE_CRA;
    }
};

// 视频编码器回调上下文
struct EncoderContext {
    NetworkStreamer* streamer;
    ScreenInfo screen_info;
    std::atomic<uint64_t> frame_count{0};
    std::vector<uint8_t> sps_data;
    std::vector<uint8_t> pps_data;
    std::vector<uint8_t> vps_data;
    std::atomic<bool> params_sent{false};
    bool is_hevc = false;
};

// 视频编码类
class VideoEncoder {
public:
    VideoEncoder() : encoder_(nullptr), surface_(nullptr), is_encoding_(false) {
        context_ = std::make_unique<EncoderContext>();
    }
    
    ~VideoEncoder() { release(); }

void printAvcVideoCodecCapability() {
        LOG_INFO("Server", "------------------------------------------------------");
        LOG_INFO("Server", "AVC(H.264) Video Codec Capability Info: ");
        OH_AVCapability *capability = OH_AVCodec_GetCapabilityByCategory(OH_AVCODEC_MIMETYPE_VIDEO_AVC, true, HARDWARE);
        if (capability == nullptr) {
            LOG_ERROR("Server", "OH_AVCodec_GetCapabilityByCategory fail");
            return;
        }
const char *codecName = OH_AVCapability_GetName(capability);
        LOG_INFO("Server", "  CodecName: " + std::string(codecName));

        bool isSupported = OH_AVCapability_IsEncoderBitrateModeSupported(capability, BITRATE_MODE_CBR);
        bool isSupported2 = OH_AVCapability_IsEncoderBitrateModeSupported(capability, BITRATE_MODE_VBR);
        bool isSupported3 = OH_AVCapability_IsEncoderBitrateModeSupported(capability, BITRATE_MODE_CQ);
        LOG_INFO("Server", "  BitRateModeSupported: CBR[" + std::to_string(isSupported) + "], VBR[" + std::to_string(isSupported2) + "], CQ[" + std::to_string(isSupported3) + "]");

        OH_AVRange bitrateRange = {-1, -1};
        int32_t ret = OH_AVCapability_GetEncoderBitrateRange(capability, &bitrateRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", "  BitRateRange: [" + std::to_string(bitrateRange.minVal) + "~" + std::to_string(bitrateRange.maxVal) + "]");
        }
        OH_AVRange qualityRange = {-1, -1};
        ret = OH_AVCapability_GetEncoderQualityRange(capability, &qualityRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", "QualityRange: [" + std::to_string(qualityRange.minVal) + "~" + std::to_string(qualityRange.maxVal) + "]");
        }

        // 获取profile范围
        const int32_t *profiles = nullptr;
        uint32_t profileNum = 0;
        ret = OH_AVCapability_GetSupportedProfiles(capability, &profiles, &profileNum);
        if (ret == AV_ERR_OK) {
            std::string profileStr = "  SupportedProfiles: [";
            for (uint32_t i = 0; i < profileNum; i++) {
                profileStr += std::to_string(profiles[i]);
                if (i < profileNum - 1) profileStr += ",";
            }
            profileStr += "]";
            LOG_INFO("Server", profileStr);
        }

        // 获取AVC_PROFILE_MAIN对应的Level范围
        int32_t profile = OH_AVCProfile::AVC_PROFILE_MAIN;
        const int32_t *levels = nullptr;
        uint32_t levelNum = 0;
        ret = OH_AVCapability_GetSupportedLevelsForProfile(capability, profile, &levels, &levelNum);
        if (ret == AV_ERR_OK) {
            std::string levelStr = "  SupportedLevelsForProfile " + std::to_string(profile) + ": [";
            for (uint32_t i = 1; i < levelNum; i++) {
               levelStr += std::to_string(levels[i]);
               if (i < levelNum - 1) levelStr += ",";
            }
            levelStr += "]";
            LOG_INFO("Server", levelStr);
        }

        // 获取支持的宽范围
OH_AVRange widthRange = {-1, -1};
        ret = OH_AVCapability_GetVideoWidthRange(capability, &widthRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", "  WidthRange: [" + std::to_string(widthRange.minVal) + "," + std::to_string(widthRange.maxVal) + "]");
        }
        OH_AVRange heightRange = {-1, -1};
        ret = OH_AVCapability_GetVideoHeightRange(capability, &heightRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", ", HeightRange: [" + std::to_string(heightRange.minVal) + "," + std::to_string(heightRange.maxVal) + "]");
        }
OH_AVRange frameRateRange = {-1, -1};
        ret = OH_AVCapability_GetVideoFrameRateRange(capability, &frameRateRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", ", FrameRateRange: [" + std::to_string(frameRateRange.minVal) + "," + std::to_string(frameRateRange.maxVal) + "]");
        }

        int32_t widthAlignment = 0;
        ret = OH_AVCapability_GetVideoWidthAlignment(capability, &widthAlignment);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", "  WidthAlignment: " + std::to_string(widthAlignment));
        }
int32_t heightAlignment = 0;
        ret = OH_AVCapability_GetVideoHeightAlignment(capability, &heightAlignment);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", ", HeightAlignment: " + std::to_string(heightAlignment));
        }

const int32_t *pixFormats = nullptr;
        uint32_t pixFormatNum = 0;
        ret = OH_AVCapability_GetVideoSupportedPixelFormats(capability, &pixFormats, &pixFormatNum);
        if (ret == AV_ERR_OK) {
            std::string pixStr = "  SupportedPixelFormats: [";
            for (uint32_t i = 1; i < pixFormatNum; i++) {
               pixStr += std::to_string(pixFormats[i]);
               if (i < pixFormatNum - 1) pixStr += ",";
            }
            pixStr += "]";
            LOG_INFO("Server", pixStr);
        }
        isSupported = OH_AVCapability_IsFeatureSupported(capability, VIDEO_LOW_LATENCY);
        LOG_INFO("Server", "  IsFeatureSupported VIDEO_LOW_LATENCY: " + std::to_string(isSupported));

        int32_t width = 720;
        int32_t height = 1280;
        // 获取指定视频宽高是否支持
isSupported = OH_AVCapability_IsVideoSizeSupported(capability, width, height);
        LOG_INFO("Server", "  [720*1280] IsVideoSizeSupported: " + std::to_string(isSupported));
        frameRateRange = {-1, -1};
        ret = OH_AVCapability_GetVideoFrameRateRangeForSize(capability, width, height, &frameRateRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", ", FrameRateRange: [" + std::to_string(frameRateRange.minVal) + "," + std::to_string(frameRateRange.maxVal) + "]");
        }

        LOG_INFO("Server", "------------------------------------------------------");
    }
    
    void printHevcVideoCodecCapability() {
        LOG_INFO("Server", "------------------------------------------------------");
        LOG_INFO("Server", "HEVC(H.265) Video Codec Capability Info: ");
        OH_AVCapability *capability = OH_AVCodec_GetCapabilityByCategory(OH_AVCODEC_MIMETYPE_VIDEO_HEVC, true, HARDWARE);
        if (capability == nullptr) {
            LOG_INFO("Server", "  H265 encoder NOT supported");
            LOG_INFO("Server", "------------------------------------------------------");
            return;
        }
        const char *codecName = OH_AVCapability_GetName(capability);
        LOG_INFO("Server", "  CodecName: " + std::string(codecName));

        bool isSupported = OH_AVCapability_IsEncoderBitrateModeSupported(capability, BITRATE_MODE_CBR);
        bool isSupported2 = OH_AVCapability_IsEncoderBitrateModeSupported(capability, BITRATE_MODE_VBR);
        bool isSupported3 = OH_AVCapability_IsEncoderBitrateModeSupported(capability, BITRATE_MODE_CQ);
        LOG_INFO("Server", "  BitRateModeSupported: CBR[" + std::to_string(isSupported) + "], VBR[" + std::to_string(isSupported2) + "], CQ[" + std::to_string(isSupported3) + "]");

        OH_AVRange bitrateRange = {-1, -1};
        int32_t ret = OH_AVCapability_GetEncoderBitrateRange(capability, &bitrateRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", "  BitRateRange: [" + std::to_string(bitrateRange.minVal) + "~" + std::to_string(bitrateRange.maxVal) + "]");
        }

        OH_AVRange widthRange = {-1, -1}, heightRange = {-1, -1};
        ret = OH_AVCapability_GetVideoWidthRange(capability, &widthRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", "  WidthRange: [" + std::to_string(widthRange.minVal) + "~" + std::to_string(widthRange.maxVal) + "]");
        }
        ret = OH_AVCapability_GetVideoHeightRange(capability, &heightRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", "  HeightRange: [" + std::to_string(heightRange.minVal) + "~" + std::to_string(heightRange.maxVal) + "]");
        }

        int32_t widthAlignment = 0, heightAlignment = 0;
        OH_AVCapability_GetVideoWidthAlignment(capability, &widthAlignment);
        OH_AVCapability_GetVideoHeightAlignment(capability, &heightAlignment);
        LOG_INFO("Server", "  Alignment: " + std::to_string(widthAlignment) + "x" + std::to_string(heightAlignment));

        OH_AVRange frameRateRange = {-1, -1};
        ret = OH_AVCapability_GetVideoFrameRateRange(capability, &frameRateRange);
        if (ret == AV_ERR_OK) {
            LOG_INFO("Server", "  FrameRateRange: [" + std::to_string(frameRateRange.minVal) + "~" + std::to_string(frameRateRange.maxVal) + "]");
        }

        const int32_t *profiles = nullptr;
        uint32_t profileNum = 0;
        OH_AVCapability_GetSupportedProfiles(capability, &profiles, &profileNum);
        if (profiles != nullptr && profileNum > 0) {
            std::string profileStr = "  SupportedProfiles: [";
            for (uint32_t i = 0; i < profileNum; i++) {
                profileStr += std::to_string(profiles[i]);
                if (i < profileNum - 1) profileStr += ",";
            }
            profileStr += "]";
            LOG_INFO("Server", profileStr);
        }

        LOG_INFO("Server", "------------------------------------------------------");
    }
    
    bool initialize(const ScreenInfo& info, NetworkStreamer* streamer) {
        if (encoder_ != nullptr) {
            LOG_INFO("Server", "VideoEncoder has been initialized");
            return true;
        }
        LOG_INFO("Server", "Initializing VideoEncoder...");

        bool is_hevc = (info.codec == "h265");
        
        if (is_hevc) {
            printHevcVideoCodecCapability();
        } else {
            printAvcVideoCodecCapability();
        }
        
        // 根据codec类型创建编码器
        if (is_hevc) {
            encoder_ = OH_VideoEncoder_CreateByMime(OH_AVCODEC_MIMETYPE_VIDEO_HEVC);
        } else {
            encoder_ = OH_VideoEncoder_CreateByMime(OH_AVCODEC_MIMETYPE_VIDEO_AVC);
        }
        if (encoder_ == nullptr) {
            LOG_ERROR("Server", "OH_VideoEncoder_CreateByMime fail for codec: " + info.codec);
            return false;
        }

        // 注册回调
        OH_AVCodecCallback callback = {
            .onError = &VideoEncoder::onError,
            .onStreamChanged = &VideoEncoder::onStreamChanged,
            .onNeedInputBuffer = &VideoEncoder::onNeedInputBuffer,
            .onNewOutputBuffer = &VideoEncoder::onNewOutputBuffer
        };
        int32_t ret = OH_VideoEncoder_RegisterCallback(encoder_, callback, this);
        if (ret != AV_ERR_OK) {
            LOG_ERROR("Server", "OH_VideoEncoder_RegisterCallback fail, err: " + std::to_string(ret));
            return false;
        }
        
        // 创建并配置编码格式
        OH_AVFormat* format = OH_AVFormat_Create();
        if (format == nullptr) {
            LOG_ERROR("Server", "OH_AVFormat_Create fail");
            return false;
        }
        // 设置编码参数
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_WIDTH, info.width);
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_HEIGHT, info.height);
        OH_AVFormat_SetDoubleValue(format, OH_MD_KEY_FRAME_RATE, info.fps);
        OH_AVFormat_SetLongValue(format, OH_MD_KEY_BITRATE, info.bitrate); // 必须配置，设置码率，单位为bps。
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_PIXEL_FORMAT, AV_PIXEL_FORMAT_RGBA);
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_VIDEO_ENCODE_BITRATE_MODE, OH_BitrateMode::BITRATE_MODE_VBR);
        
        // 根据codec类型设置Profile
        if (is_hevc) {
            OH_AVFormat_SetIntValue(format, OH_MD_KEY_PROFILE, OH_HEVCProfile::HEVC_PROFILE_MAIN);
        } else {
            OH_AVFormat_SetIntValue(format, OH_MD_KEY_PROFILE, OH_AVCProfile::AVC_PROFILE_MAIN);
        }
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_I_FRAME_INTERVAL, 500); // 关键帧间隔，单位毫秒
        
        // 配置编码器
        ret = OH_VideoEncoder_Configure(encoder_, format);
        if (ret != AV_ERR_OK && ret != AV_ERR_INVALID_VAL) {
            LOG_ERROR("Server", "OH_VideoEncoder_Configure fail, err: " + std::to_string(ret));
            OH_AVFormat_Destroy(format);
            return false;
        }
        OH_AVFormat_Destroy(format);
        
        // 获取编码器的Surface
ret = OH_VideoEncoder_GetSurface(encoder_, &surface_);
        if (ret != AV_ERR_OK || surface_ == nullptr) {
            LOG_ERROR("Server", "OH_VideoEncoder_GetSurface fail, err: " + std::to_string(ret));
            return false;
        }

        ret = OH_VideoEncoder_Prepare(encoder_);
        if (ret != AV_ERR_OK) {
            LOG_ERROR("Server", "OH_VideoEncoder_Prepare fail, err: " + std::to_string(ret));
            return false;
        }

        context_->streamer = streamer;
        context_->screen_info = info;
        context_->params_sent = false;
        context_->is_hevc = is_hevc;
        LOG_INFO("Server", "VideoEncoder initialized successfully for codec: " + info.codec);
        return true;
    }
    
    bool start() {
        if (encoder_ == nullptr) {
            LOG_ERROR("Server", "VideoEncoder has not been initialized");
            return false;
        }
        
        is_encoding_ = true;
        int32_t ret = OH_VideoEncoder_Start(encoder_);
        if (ret != AV_ERR_OK) {
            LOG_ERROR("Server", "OH_VideoEncoder_Start fail, err: " + std::to_string(ret));
            is_encoding_ = false;
            return false;
        }

        LOG_INFO("Server", "VideoEncoder started");
        return true;
    }
    
    void stop() {
        if (encoder_ && is_encoding_) {
            OH_VideoEncoder_NotifyEndOfStream(encoder_);
            OH_VideoEncoder_Stop(encoder_);
            is_encoding_ = false;
        }
    }
    
    void release() {
        stop();
        if (encoder_) {
            OH_VideoEncoder_Destroy(encoder_);
            encoder_ = nullptr;
        }
    }
    
    bool sendCodecParams() {
        if (!context_->streamer->hasClient()) {
            return false;
        }
        
        // H.265需要发送VPS
        if (context_->is_hevc && !context_->vps_data.empty()) {
            LOG_INFO("Server", "Sending VPS (" + std::to_string(context_->vps_data.size()) + " bytes)");
            if (!context_->streamer->sendPacket(context_->vps_data.data(),
                                               context_->vps_data.size(),
                                               PACKET_TYPE_VPS)) {
                LOG_ERROR("Server", "Failed to send VPS");
                return false;
            }
        }
        
        if (!context_->sps_data.empty() && !context_->pps_data.empty()) {
            LOG_INFO("Server", "Sending SPS (" + std::to_string(context_->sps_data.size()) + " bytes) and PPS (" + std::to_string(context_->pps_data.size()) + " bytes)");
            
            if (!context_->streamer->sendVideoConfig(context_->screen_info)) {
                LOG_ERROR("Server", "Failed to send video config");
                return false;
            }
            
            if (!context_->streamer->sendPacket(context_->sps_data.data(), 
                                            context_->sps_data.size(), 
                                            PACKET_TYPE_SPS)) {
                LOG_ERROR("Server", "Failed to send SPS");
                return false;
            }
            
            if (!context_->streamer->sendPacket(context_->pps_data.data(), 
                                            context_->pps_data.size(), 
                                            PACKET_TYPE_PPS)) {
                LOG_ERROR("Server", "Failed to send PPS");
                return false;
            }
            context_->params_sent = true;
            return true;
        }
        
        LOG_ERROR("Server", "No SPS/PPS data to send");
        return false;
    }

    bool isEncoding() const { return is_encoding_; }
    uint64_t getFrameCount() const { return context_->frame_count; }
    bool isParamsSent() const { return context_->params_sent.load(); }
    
    OH_AVCodec* getEncoder() const { return encoder_; }
    OHNativeWindow* getSurface() const { return surface_; }
    
    // 静态回调函数
    static void onError(OH_AVCodec* codec, int32_t errorCode, void* userData) {
        LOG_ERROR("Server", "VideoEncoder error: " + std::to_string(errorCode));
    }
    
    static void onStreamChanged(OH_AVCodec* codec, OH_AVFormat* format, void* userData) {
        (void)codec;
        (void)userData;
        int32_t width = 0, height = 0;
        OH_AVFormat_GetIntValue(format, OH_MD_KEY_WIDTH, &width);
        OH_AVFormat_GetIntValue(format, OH_MD_KEY_HEIGHT, &height);
        LOG_INFO("Server", "VideoEncoder stream changed: " + std::to_string(width) + "x" + std::to_string(height));
    }
    
    static void onNeedInputBuffer(OH_AVCodec* codec, uint32_t index, OH_AVBuffer* buffer, void* userData) {
        // Surface模式下不需要实现
    }
    
    static void onNewOutputBuffer(OH_AVCodec* codec, uint32_t index, OH_AVBuffer* buffer, void* userData) {
        if (!IsValidOnNewOutputBufferParam(codec, buffer, userData)) {
            OH_VideoEncoder_FreeOutputBuffer(codec, index);
            return;
        }
        
        // 获取编码后的数据
        OH_AVCodecBufferAttr info;
        if (buffer != nullptr) {
            OH_AVErrCode ret = OH_AVBuffer_GetBufferAttr(buffer, &info);
            if (ret != AV_ERR_OK) {
                LOG_ERROR("Server", "OH_AVBuffer_GetBufferAttr fail, err: " + std::to_string(ret));
                return;
            }
            uint32_t no_need_flags = AVCODEC_BUFFER_FLAGS_DISCARD | AVCODEC_BUFFER_FLAGS_DISPOSABLE | 
                AVCODEC_BUFFER_FLAGS_EOS;
            if ((info.flags & no_need_flags) != 0) {
                if ((info.flags & AVCODEC_BUFFER_FLAGS_EOS) != 0) {
                    LOG_INFO("Server", "End-of-Stream frame");
                }
                OH_VideoEncoder_FreeOutputBuffer(codec, index);
                return;
            }
            uint8_t *addr = OH_AVBuffer_GetAddr(buffer);
            if (addr == nullptr) {
                LOG_ERROR("Server", "OH_AVBuffer_GetAddr fail");
                return;
            }
            
            if (info.size > 0) {
                VideoEncoder* self = static_cast<VideoEncoder*>(userData);
                // 首先检查是否为编码器配置数据
                bool is_config = (info.flags & AVCODEC_BUFFER_FLAGS_CODEC_DATA) != 0;
                if (is_config) {
                    handleCofingFrame(self, addr, info.size);
                } else {
                    handleNormalFrame(self, addr, info.size, info.flags);
                }
            }
        }
        
        // 释放缓冲区
        OH_VideoEncoder_FreeOutputBuffer(codec, index);
    }

    static bool IsValidOnNewOutputBufferParam(OH_AVCodec* codec, OH_AVBuffer* buffer, void* userData) {
        if (!codec || !buffer) {
            LOG_ERROR("Server", "Invalid codec or buffer in callback");
            return false;
        }
        
        VideoEncoder* self = static_cast<VideoEncoder*>(userData);
        if (!self || !self->context_ || !self->context_->streamer) {
            LOG_ERROR("Server", "Invalid context in output buffer callback");
            return false;
        }
        
        if (!self->isEncoding()) {
            LOG_INFO("Server", "Encoder not in encoding state, skipping frame");
            return false;
        }
        return true;
    }

    static void handleCofingFrame(VideoEncoder* self, uint8_t *addr, size_t size) {
        LOG_INFO("Server", "Received codec config data: " + std::to_string(size) + " bytes");
        
        if (self->context_->is_hevc) {
            std::vector<uint8_t> vps, sps, pps;
            if (H265Utils::extractVpsSpsPpsAnnexB(addr, size, vps, sps, pps)) {
                self->context_->vps_data = std::move(vps);
                self->context_->sps_data = std::move(sps);
                self->context_->pps_data = std::move(pps);
                
                if (self->context_->streamer->hasClient()) {
                    self->sendCodecParams();
                }
            } else {
                LOG_INFO("Server", "Could not extract VPS/SPS/PPS from config data");
            }
        } else {
            std::vector<uint8_t> sps, pps;
            if (H264Utils::extractSpsPpsAnnexB(addr, size, sps, pps)) {
                self->context_->sps_data = std::move(sps);
                self->context_->pps_data = std::move(pps);
                
                if (self->context_->streamer->hasClient()) {
                    self->sendCodecParams();
                }
            } else {
                LOG_INFO("Server", "Could not extract SPS/PPS from config data");
            }
        }
    }

    static void handleNormalFrame(VideoEncoder* self, uint8_t *addr, size_t size, uint32_t flags) {
        bool is_keyframe = (flags & AVCODEC_BUFFER_FLAGS_SYNC_FRAME) > 0;
        uint32_t packet_type = is_keyframe ? PACKET_TYPE_KEYFRAME : PACKET_TYPE_FRAME;
        if ((flags & AVCODEC_BUFFER_FLAGS_INCOMPLETE_FRAME) > 0) {
            LOG_INFO("Server", "Recv INCOMPLETE_FRAME");
        }
        
        if (is_keyframe && !self->context_->params_sent.load()) {
            if (self->context_->is_hevc) {
                std::vector<uint8_t> vps, sps, pps;
                if (H265Utils::extractVpsSpsPpsAnnexB(addr, size, vps, sps, pps)) {
                    self->context_->vps_data = std::move(vps);
                    self->context_->sps_data = std::move(sps);
                    self->context_->pps_data = std::move(pps);
                    self->sendCodecParams();
                } else {
                    LOG_ERROR("Server", "Failed to extract VPS/SPS/PPS from H.265 keyframe");
                }
            } else {
                std::vector<uint8_t> sps, pps;
                if (H264Utils::extractSpsPpsAnnexB(addr, size, sps, pps)) {
                    self->context_->sps_data = std::move(sps);
                    self->context_->pps_data = std::move(pps);
                    self->sendCodecParams();
                } else {
                    LOG_ERROR("Server", "Failed to extract SPS/PPS from keyframe");
                }
            }
        }
        
        if (self->context_->streamer->hasClient()) {
            self->context_->streamer->sendPacket((const void*)addr, size, packet_type);
            self->context_->frame_count++;
            
            static uint64_t last_frame_count = 0;
            if ((last_frame_count != self->context_->frame_count) && (self->context_->frame_count % 100 == 0)) {
                LOG_INFO("Server", "Sent " + std::to_string(self->context_->frame_count) + " frames");
                last_frame_count = self->context_->frame_count;
            }
        }
    }
    
private:
    OH_AVCodec* encoder_;
    OHNativeWindow* surface_;
    std::unique_ptr<EncoderContext> context_;
    bool is_encoding_;
};

// 屏幕捕获类
class ScreenCapturer {
public:
    ScreenCapturer() : capture_(nullptr), is_capturing_(false) {}
    ~ScreenCapturer() { release(); }
    
    bool initialize(const ScreenInfo& info, VideoEncoder* encoder, NetworkStreamer* streamer) {
        if (capture_ != nullptr) {
            LOG_INFO("Server", "ScreenCapturer has been initialized");
            return true;
        }
        LOG_INFO("Server", "Initializing ScreenCapturer...");
        
        // 创建屏幕捕获实例
        capture_ = OH_AVScreenCapture_Create();
        if (capture_ == nullptr) {
            LOG_ERROR("Server", "OH_AVScreenCapture_Create fail");
            return false;
        }
        
        // 配置视频捕获信息
        OH_VideoCaptureInfo videoCapInfo = {
            .videoFrameWidth = info.width,
            .videoFrameHeight = info.height,
            .videoSource = OH_VIDEO_SOURCE_SURFACE_RGBA
        };
        
        // 配置视频编码信息 - 根据codec类型选择编码格式
        OH_VideoCodecFormat videoCodec;
        if (info.codec == "h265") {
            videoCodec = OH_VideoCodecFormat::OH_H265;
        } else {
            videoCodec = OH_VideoCodecFormat::OH_H264;
        }
        
        OH_VideoEncInfo videoEncInfo = {
            .videoCodec = videoCodec,
            .videoBitrate = info.bitrate,
            .videoFrameRate = info.fps
        };
        
        OH_VideoInfo videoinfo = {
            .videoCapInfo = videoCapInfo,
            .videoEncInfo = videoEncInfo
        };
        
        OH_AVScreenCaptureConfig config = {
            .captureMode = OH_CAPTURE_HOME_SCREEN,
            .dataType = OH_ORIGINAL_STREAM,
            .videoInfo = videoinfo
        };
        
        // 初始化捕获器
        int32_t ret = OH_AVScreenCapture_Init(capture_, config);
        if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
            LOG_ERROR("Server", "OH_AVScreenCapture_Init fail, err: " + std::to_string(ret));
            return false;
        }

        // 关闭MIC
        OH_AVScreenCapture_SetMicrophoneEnabled(capture_, false);
        
        // 设置错误回调
        ret = OH_AVScreenCapture_SetErrorCallback(capture_, &ScreenCapturer::onError, this);
        if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
            LOG_ERROR("Server", "OH_AVScreenCapture_SetErrorCallback fail, err: " + std::to_string(ret));
            return false;
        }
        
        ret = OH_AVScreenCapture_SetStateCallback(capture_, &ScreenCapturer::onStateChange, this);
        if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
            LOG_ERROR("Server", "OH_AVScreenCapture_SetStateCallback fail, err: " + std::to_string(ret));
            return false;
        }
        
        ret = OH_AVScreenCapture_SetDataCallback(capture_, &ScreenCapturer::onBufferAvailable, this);
        if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
            LOG_ERROR("Server", "OH_AVScreenCapture_SetDataCallback fail, err: " + std::to_string(ret));
            return false;
        }
        
        // 保存上下文
        encoder_ = encoder;
        streamer_ = streamer;
        screen_info_ = info;
        LOG_INFO("Server", "Screen capturer initialized: " + std::to_string(info.width) + "x" + std::to_string(info.height) + "@" + std::to_string(info.fps) + "fps");
        return true;
    }
    
    bool start() {
        if (capture_ == nullptr || encoder_ == nullptr) {
            LOG_ERROR("Server", "ScreenCapturer has not been initialized");
            return false;
        }
        
        int32_t ret = OH_AVScreenCapture_StartScreenCaptureWithSurface(capture_, encoder_->getSurface());
        if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
            LOG_ERROR("Server", "OH_AVScreenCapture_StartScreenCaptureWithSurface fail, err: " + std::to_string(ret));
            return false;
        }
        
        is_capturing_ = true;
        LOG_INFO("Server", "Screen capture started");
        return true;
    }
    
    void stop() {
        if (capture_ && is_capturing_) {
            OH_AVScreenCapture_StopScreenCapture(capture_);
            is_capturing_ = false;
        }
    }
    
    void release() {
        stop();
        if (capture_) {
            OH_AVScreenCapture_Release(capture_);
            capture_ = nullptr;
        }
    }
    
    ScreenInfo getScreenInfo() const { return screen_info_; }
    bool isCapturing() const { return is_capturing_; }
    
    // 静态回调函数
    static void onError(OH_AVScreenCapture* capture, int32_t errorCode, void* userData) {
        ScreenCapturer* self = static_cast<ScreenCapturer*>(userData);
        if (self) {
            self->handleError(capture, errorCode);
        }
    }
    
    static void onStateChange(OH_AVScreenCapture* capture, OH_AVScreenCaptureStateCode stateCode, void* userData) {
        ScreenCapturer* self = static_cast<ScreenCapturer*>(userData);
        if (self) {
            self->handleStateChange(capture, stateCode);
        }
    }
    
    static void onBufferAvailable(OH_AVScreenCapture* capture, OH_AVBuffer* buffer, 
                                 OH_AVScreenCaptureBufferType bufferType, int64_t timestamp, void* userData) {
        ScreenCapturer* self = static_cast<ScreenCapturer*>(userData);
        if (self && bufferType == OH_SCREEN_CAPTURE_BUFFERTYPE_VIDEO) {
            self->handleBufferAvailable(capture, buffer, bufferType, timestamp);
        }
    }
    
    // 成员函数用于处理回调
    void handleError(OH_AVScreenCapture* capture, int32_t errorCode) {
        LOG_ERROR("Server", "Screen capture error: " + std::to_string(errorCode));
    }
    
    void handleStateChange(OH_AVScreenCapture* capture, OH_AVScreenCaptureStateCode stateCode) {
        if (stateCode == OH_SCREEN_CAPTURE_STATE_STARTED) {
            LOG_INFO("Server", "Screen capture state: STARTED");
        } else if (stateCode == OH_SCREEN_CAPTURE_STATE_STOPPED_BY_CALL) {
            LOG_INFO("Server", "Screen capture state: STOPPED_BY_CALL");
            is_capturing_ = false;
        } else if (stateCode == OH_SCREEN_CAPTURE_STATE_CANCELED) {
            LOG_INFO("Server", "Screen capture state: CANCELED");
            is_capturing_ = false;
        } else {
            LOG_INFO("Server", "Screen capture state code:" + std::to_string(stateCode));
        }
    }
    
    void handleBufferAvailable(OH_AVScreenCapture* capture, OH_AVBuffer* buffer, 
                              OH_AVScreenCaptureBufferType bufferType, int64_t timestamp) {
        LOG_INFO("Server", "Enter handleBufferAvailable");
        if (!is_capturing_) {
            return;
        }
        
        // 这里可以处理音频数据，当前版本只关注视频
        (void)capture;
        (void)buffer;
        (void)bufferType;
        (void)timestamp;
    }
    
private:
    OH_AVScreenCapture* capture_;
    ScreenInfo screen_info_;
    VideoEncoder* encoder_;
    NetworkStreamer* streamer_;
    bool is_capturing_;
};

class OHScrcpyServer;
// 显示状态监听类
class DisplayResolutionListener : public DisplayManager::IDisplayListener {
public:
    DisplayResolutionListener(OHScrcpyServer *scrcpy_server) : scrcpy_server_(scrcpy_server) {};

    virtual void OnCreate(DisplayId displayId) override {
        return;
    };

    virtual void OnDestroy(DisplayId displayId) override {
        return;
    };

    virtual void OnChange(DisplayId displayId) override;
private:
    OHScrcpyServer *scrcpy_server_;
};

// 主服务类
class OHScrcpyServer {
public:
    OHScrcpyServer() : port_(DEFAULT_PORT), screen_info_{} {
        display_listener_ = new (std::nothrow) DisplayResolutionListener(this);
    }
    
    bool start(const CommandLineArgs& args) {
        // 设置端口
        port_ = args.port;
        
        if (!initialize(args)) {
            LOG_ERROR("Server", "OHScrcpyServer initialize fail");
            return false;
        }
        
        g_running = true;
        mainLoop();
        return true;
    }
    
    void stop() {
        LOG_INFO("Server", "Stopping OHScrcpy Server...");
        g_running = false;
        g_streaming = false;
        cleanup();
    }

    bool initCmdArgsFromDevice(CommandLineArgs& args) {
        ScreenInfo screenInfo;
        getPrimaryScreenInfo(screenInfo);

        args.width = screenInfo.width;
        args.height = screenInfo.height;
        args.framerate = screenInfo.fps;
        args.bitrate = screenInfo.bitrate;
        return true;
    }

    void resetVideoOutput(uint64_t displayId, int32_t width, int32_t height) {
        if (displayId != screen_info_.displayid) {
            return;
        }
        if ((width == screen_info_.width) && (height == screen_info_.height)) {
            return;
        }
        LOG_INFO("Server", "Resolution is changed, reset video output: displayId[" + std::to_string(displayId) + "] resolution[" + std::to_string(width) + "x" + std::to_string(height) + "]");
        stopStreaming();
        screen_info_.width = width;
        screen_info_.height = height;
        initStreaming();
    }
    
    // 标准分辨率结构体
    struct StandardResolution {
        int32_t width;
        int32_t height;
        std::string name;
        int64_t defaultBitrate;
    };
    
    // 横屏标准分辨率列表
    const std::vector<StandardResolution> HORIZONTAL_RESOLUTIONS = {
        {3840, 2160, "4K",      8000000},
        {2560, 1440, "2K",      6000000},
        {1920, 1080, "1080p",   4000000},
        {1280, 720,  "720p",    2000000},
        {854,  480,  "480p",    1000000},
        {640,  360,  "360p",    600000},
        {426,  240,  "240p",    300000},
    };
    
    // 竖屏标准分辨率列表
    const std::vector<StandardResolution> VERTICAL_RESOLUTIONS = {
        {2160, 3840, "4K",      8000000},
        {1440, 2560, "2K",      6000000},
        {1080, 1920, "1080p",   4000000},
        {720,  1280, "720p",    2000000},
        {480,  854,  "480p",    1000000},
        {360,  640,  "360p",    600000},
        {240,  426,  "240p",    300000},
    };
    
    // H.265编码器存在性检测（不检测具体分辨率）
    bool checkHevcEncoderExists() {
        LOG_INFO("Server", "[Step 1] Check H.265 hardware encoder existence");
        OH_AVCapability *capability = OH_AVCodec_GetCapabilityByCategory(
            OH_AVCODEC_MIMETYPE_VIDEO_HEVC, true, HARDWARE);
        
        if (capability == nullptr) {
            LOG_INFO("Server", "  H.265 hardware encoder NOT supported");
            return false;
        }
        
        LOG_INFO("Server", "  H.265 hardware encoder supported");
        return true;
    }
    
    // H.265特定分辨率+帧率检测
    bool checkHevcSizeAndFrameRateSupported(int32_t width, int32_t height, int32_t fps) {
        OH_AVCapability *capability = OH_AVCodec_GetCapabilityByCategory(
            OH_AVCODEC_MIMETYPE_VIDEO_HEVC, true, HARDWARE);
        
        if (capability == nullptr) return false;
        
        bool supported = OH_AVCapability_AreVideoSizeAndFrameRateSupported(capability, width, height, fps);
        
        if (supported) {
            LOG_INFO("Server", "  H.265 supports " + std::to_string(width) + "x" + std::to_string(height) + "@" + std::to_string(fps) + "fps");
        } else {
            LOG_INFO("Server", "  H.265 does NOT support " + std::to_string(width) + "x" + std::to_string(height) + "@" + std::to_string(fps) + "fps");
        }
        
        return supported;
    }
    
    // H.264特定分辨率+帧率检测
    bool checkAvcSizeAndFrameRateSupported(int32_t width, int32_t height, int32_t fps) {
        OH_AVCapability *capability = OH_AVCodec_GetCapabilityByCategory(
            OH_AVCODEC_MIMETYPE_VIDEO_AVC, true, HARDWARE);
        
        if (capability == nullptr) return false;
        
        bool supported = OH_AVCapability_AreVideoSizeAndFrameRateSupported(capability, width, height, fps);
        
        if (supported) {
            LOG_INFO("Server", "  H.264 supports " + std::to_string(width) + "x" + std::to_string(height) + "@" + std::to_string(fps) + "fps");
        } else {
            LOG_INFO("Server", "  H.264 does NOT support " + std::to_string(width) + "x" + std::to_string(height) + "@" + std::to_string(fps) + "fps");
        }
        
        return supported;
    }
    
    // 判断屏幕方向
    bool isHorizontalScreen(int32_t width, int32_t height) {
        return width >= height;
    }
    
    // 计算分辨率接近度
    int64_t calculateResolutionDistance(int32_t w1, int32_t h1, int32_t w2, int32_t h2) {
        int64_t pixels1 = (int64_t)w1 * h1;
        int64_t pixels2 = (int64_t)w2 * h2;
        return std::abs(pixels1 - pixels2);
    }
    
    // 从指定codec的标准列表找支持的分辨率
    StandardResolution findCodecSupportedResolution(const std::string& codec,
                                                    int32_t origWidth, int32_t origHeight, int32_t fps) {
        bool isHorizontal = isHorizontalScreen(origWidth, origHeight);
        const std::vector<StandardResolution>& resolutions = 
            isHorizontal ? HORIZONTAL_RESOLUTIONS : VERTICAL_RESOLUTIONS;
        
        LOG_INFO("Server", "  Searching " + codec + " supported resolutions (direction: " + (isHorizontal ? "horizontal" : "vertical") + ")...");
        
        std::vector<StandardResolution> candidates;
        for (const auto& res : resolutions) {
            bool supported;
            if (codec == "h265") {
                supported = checkHevcSizeAndFrameRateSupported(res.width, res.height, fps);
            } else {
                supported = checkAvcSizeAndFrameRateSupported(res.width, res.height, fps);
            }
            
            if (supported) {
                candidates.push_back(res);
                LOG_INFO("Server", "    " + res.name + " (" + std::to_string(res.width) + "x" + std::to_string(res.height) + ") - PASSED");
            } else {
                LOG_INFO("Server", "    " + res.name + " (" + std::to_string(res.width) + "x" + std::to_string(res.height) + ") - NOT supported");
            }
        }
        
        if (candidates.empty()) {
            LOG_INFO("Server", "  No " + codec + " supported resolution found!");
            return {0, 0, "none", 0};
        }
        
        // 找像素数最接近原始的
        StandardResolution best = candidates[0];
        int64_t minDistance = calculateResolutionDistance(origWidth, origHeight, best.width, best.height);
        for (const auto& cand : candidates) {
            int64_t dist = calculateResolutionDistance(origWidth, origHeight, cand.width, cand.height);
            if (dist < minDistance) {
                minDistance = dist;
                best = cand;
            }
        }
        
        LOG_INFO("Server", "  Best " + codec + " match: " + best.name + " (" + std::to_string(best.width) + "x" + std::to_string(best.height) + ")");
        
        return best;
    }
    
    // 按比例调整比特率
    int64_t adjustBitrateByResolution(int64_t originalBitrate,
                                      int32_t origW, int32_t origH,
                                      int32_t newW, int32_t newH) {
        int64_t origPixels = (int64_t)origW * origH;
        int64_t newPixels = (int64_t)newW * newH;
        
        if (origPixels <= 0) return originalBitrate;
        
        double ratio = (double)newPixels / origPixels;
        int64_t newBitrate = (int64_t)(originalBitrate * ratio);
        
        if (newBitrate < 500000) newBitrate = 500000;
        if (newBitrate > originalBitrate * 2) newBitrate = originalBitrate * 2;
        
        return newBitrate;
    }
    
void applyCodecConfig(ScreenInfo& screenInfo, const StandardResolution& res, 
                          int64_t origBitrate, int32_t origWidth, int32_t origHeight,
                          const std::string& codec) {
        screenInfo.width = res.width;
        screenInfo.height = res.height;
        screenInfo.codec = codec;
        screenInfo.bitrate = adjustBitrateByResolution(origBitrate, origWidth, origHeight,
                                                       screenInfo.width, screenInfo.height);
    }
    
    void applyDefaultConfig(ScreenInfo& screenInfo) {
        screenInfo.width = 720;
        screenInfo.height = 1280;
        screenInfo.codec = "h264";
        screenInfo.bitrate = 2000000;
    }
    
    bool selectCodecAndResolution(ScreenInfo& screenInfo, int32_t origWidth, int32_t origHeight,
                                      int32_t origFps, int64_t origBitrate) {
        bool hasHevc = checkHevcEncoderExists();
        
        if (hasHevc) {
            LOG_INFO("Server", "[Step 2] Check if H.265 supports original resolution");
            if (checkHevcSizeAndFrameRateSupported(origWidth, origHeight, origFps)) {
                LOG_INFO("Server", "  H.265 supports original resolution, using H.265 directly");
                screenInfo.codec = "h265";
                return true;
            }
            
            LOG_INFO("Server", "[Step 3] Find H.265 supported resolution from standard list");
            StandardResolution hevcRes = findCodecSupportedResolution("h265", origWidth, origHeight, origFps);
            if (hevcRes.name != "none") {
                LOG_INFO("Server", "  Found H.265 supported resolution, using H.265");
                applyCodecConfig(screenInfo, hevcRes, origBitrate, origWidth, origHeight, "h265");
                return true;
            }
            
            LOG_INFO("Server", "[Step 4] No H.265 resolution found, fallback to H.264");
        } else {
            LOG_INFO("Server", "[Step 2] No H.265 encoder, using H.264");
        }
        
        StandardResolution avcRes = findCodecSupportedResolution("h264", origWidth, origHeight, origFps);
        if (avcRes.name != "none") {
            LOG_INFO("Server", "  Found H.264 supported resolution, using H.264");
            applyCodecConfig(screenInfo, avcRes, origBitrate, origWidth, origHeight, "h264");
            return true;
        }
        
        LOG_INFO("Server", "  No codec supports any standard resolution! Forcing default 720x1280 H.264");
        applyDefaultConfig(screenInfo);
        return true;
    }
    
private:
    bool initialize(const CommandLineArgs& args) {
        LOG_INFO("Server", "Initializing modules...");
        if (!network_.initialize(port_)) {
            LOG_ERROR("Server", "Initialize network module fail");
            return false;
        }

        ScreenInfo screenInfo;
        if (!getPrimaryScreenInfo(screenInfo)) {
            LOG_ERROR("Server", "Get primary screen info fail");
            return false;
        }
        
		selectCodecAndResolution(screenInfo, screenInfo.width, screenInfo.height,
                                 screenInfo.fps, screenInfo.bitrate);

        screen_info_ = screenInfo;
        LOG_INFO("Server", "------------------------------------------------------");
        LOG_INFO("Server", "Final config: " + std::to_string(screen_info_.width) + "x" + std::to_string(screen_info_.height) + "@" + std::to_string(screen_info_.fps) + "fps, codec=" + screen_info_.codec + ", bitrate=" + std::to_string(screen_info_.bitrate) + "bps");
		LOG_INFO("Server", "------------------------------------------------------");
        return true;
    }

    bool getPrimaryScreenInfo(ScreenInfo &info) {
        auto display = DisplayManager::GetInstance().GetDefaultDisplay();
        if (display == nullptr) {
            LOG_ERROR("Server", "DisplayManager::GetDefaultDisplay fail");
            return false;
        }
        
        info.width = display->GetWidth();
        info.height = display->GetHeight();
        info.fps = DEFAULT_FPS;
        info.bitrate = DEFAULT_BITRATE;
        info.codec = "h264";
        info.displayid = display->GetId();
        return true;
    }

    void printScreenDetailsInfo() {
        auto display = DisplayManager::GetInstance().GetDefaultDisplay();
        if (display == nullptr) {
            LOG_ERROR("Server", "DisplayManager::GetDefaultDisplay fail");
            return;
        }

        LOG_INFO("Server", "------------------------------------------------------");
        LOG_INFO("Server", "PrimaryDisplayDetailsInfo: ");
        LOG_INFO("Server", "  id: " + std::to_string(display->GetId()) + ", name: " + std::string(display->GetName()));
        LOG_INFO("Server", "  width: " + std::to_string(display->GetWidth()) + ", height: " + std::to_string(display->GetHeight()));
        LOG_INFO("Server", "  phyWidth: " + std::to_string(display->GetPhysicalWidth()) + ", phyHeight: " + std::to_string(display->GetPhysicalHeight()));
        LOG_INFO("Server", "  refreshRate: " + std::to_string(display->GetRefreshRate()) + ", rotation: " + std::to_string(static_cast<int32_t>(display->GetRotation())));
        
        std::vector<uint32_t> hdrFormats;
        display->GetSupportedHDRFormats(hdrFormats);
        std::string hdrStr = "  HDRFormats: [";
        for (uint32_t i = 0; i < hdrFormats.size(); ++i) {
            hdrStr += std::to_string(hdrFormats[i]);
            if (i < hdrFormats.size() - 1) hdrStr += ", ";
        }
        hdrStr += "]";
        LOG_INFO("Server", hdrStr);

        std::vector<uint32_t> colorSpaces;
        display->GetSupportedColorSpaces(colorSpaces);
        std::string colorStr = "  ColorSpaces: [";
        for (uint32_t i = 0; i < colorSpaces.size(); ++i) {
            colorStr += std::to_string(colorSpaces[i]);
            if (i < colorSpaces.size() - 1) colorStr += ", ";
        }
        colorStr += "]";
        LOG_INFO("Server", colorStr);
        LOG_INFO("Server", "------------------------------------------------------");
    }
    
    bool initStreaming() {
        LOG_INFO("Server", "Initializing streaming modules (encoder & capturer)...");
        
        if (!encoder_.initialize(screen_info_, &network_)) {
            LOG_ERROR("Server", "Initialize video encoder fail");
            return false;
        }

        if (!capturer_.initialize(screen_info_, &encoder_, &network_)) {
            LOG_ERROR("Server", "Initialize screen capturer fail");
            encoder_.release();
            return false;
        }

        if (!encoder_.start()) {
            LOG_ERROR("Server", "Failed to start video encoder");
            capturer_.release();
            encoder_.release();
            return false;
        }
        
        if (!capturer_.start()) {
            LOG_ERROR("Server", "Failed to start screen capture");
            encoder_.stop();
            capturer_.release();
            encoder_.release();
            return false;
        }
        
        DisplayManager::GetInstance().RegisterDisplayListener(display_listener_);

        LOG_INFO("Server", "Initialize streaming modules successfully");
        return true;
    }
    
    void stopStreaming(bool exit = false) {
        LOG_INFO("Server", "Stopping streaming modules...");
        g_streaming = false;
        DisplayManager::GetInstance().UnregisterDisplayListener(display_listener_);
        capturer_.stop();
        encoder_.stop();
        capturer_.release();
        encoder_.release();
        LOG_INFO("Server", "Stop streaming modules complete");
        LOG_INFO("Server", "++++++++++++++++++++++++++++++++++++++++++++++++++++++");
        if (!exit) {
            LOG_INFO("Server", "Waiting for client connection...");
        }
    }
    
    void mainLoop() {
        LOG_INFO("Server", "Entering main loop...");
        LOG_INFO("Server", "Waiting for client connection...");
        auto last_stat_time = std::chrono::steady_clock::now();
        auto last_heartbeat_time = std::chrono::steady_clock::now();
        auto last_connection_check = std::chrono::steady_clock::now();
        
        bool handshake_completed = false;
        
        while (g_running) {
            auto now = std::chrono::steady_clock::now();
            
            // 1. 定期发送心跳（每2秒一次）
            if (std::chrono::duration_cast<std::chrono::seconds>(now - last_heartbeat_time).count() >= 2) {
                network_.sendHeartbeat();
                last_heartbeat_time = now;
            }
            
            // 2. 定期检查连接状态（每秒一次）
            if (std::chrono::duration_cast<std::chrono::seconds>(now - last_connection_check).count() >= 1) {
                if (!network_.checkConnection()) {
                    if (handshake_completed || g_streaming) {
                        LOG_INFO("Server", "Client disconnected, stopping streaming...");
                        stopStreaming();
                        handshake_completed = false;
                    }
                }
                last_connection_check = now;
            }
            
            // 3. 检查并接受新客户端连接
            if (!network_.hasClient()) {
                network_.acceptClient();
                usleep(10000); // 10ms
                continue;
            }
            
            // 4. 未完成握手，则执行握手流程
            if (!handshake_completed) {
                LOG_INFO("Server", "Starting handshake with client...");
                
                if (!network_.sendConfig(screen_info_)) {
                    LOG_ERROR("Server", "SendConfig to client fail, disconnected.");
                    network_.disconnectClient();
                    handshake_completed = false;
                    continue;
                }
                LOG_INFO("Server", "SendConfig to client complete, waiting for client's ACK...");
                
                if (!network_.receiveAck(5000)) {
                    LOG_ERROR("Server", "Waiting client config ACK timeout, disconnected.");
                    network_.disconnectClient();
                    handshake_completed = false;
                    continue;
                }
                LOG_INFO("Server", "Received config ACK from client, handshake successful.");
                handshake_completed = true;
                
                if (!initStreaming()) {
                    LOG_ERROR("Server", "initStreaming fail, disconnected.");
                    stopStreaming();
                    network_.disconnectClient();
                    handshake_completed = false;
                    continue;
                }
                
                g_streaming = true;
                LOG_INFO("Server", "Streaming pipeline initialized successfully, starting transmission.");
            }
            
            // 5. 握手完成且流已初始化，进入正常数据传输
            if (handshake_completed && g_streaming) {
                static uint64_t last_frame_count = 0;
                uint64_t frame_count = encoder_.getFrameCount();
                now = std::chrono::steady_clock::now();
                auto stat_elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - last_stat_time);
                if ((stat_elapsed.count() >= 5) && (last_frame_count != frame_count)) {
                    LOG_INFO("Server", "Streaming active, frames sent: " + std::to_string(frame_count));
                    last_stat_time = now;
                    last_frame_count = frame_count;
                }
            }

            usleep(10000);
        }
        LOG_INFO("Server", "Exiting main loop...");
    }
    
    void cleanup() {
        LOG_INFO("Server", "Cleaning up resources...");
        stopStreaming(true);
        network_.closeAll();
        LOG_INFO("Server", "Cleanup completed");
    }
    
private:
    int port_;
    ScreenInfo screen_info_;
    NetworkStreamer network_;
    ScreenCapturer capturer_;
    VideoEncoder encoder_;
    sptr<DisplayManager::IDisplayListener> display_listener_;
};

void DisplayResolutionListener::OnChange(DisplayId displayId) {
    if (scrcpy_server_ == nullptr) {
        return;
    }
    auto display = DisplayManager::GetInstance().GetDisplayById(displayId);
    if (display == nullptr) {
        LOG_ERROR("Server", "DisplayManager::GetDisplayById fail");
        return;
    }
    
    auto width = display->GetWidth();
    auto height = display->GetHeight();
    scrcpy_server_->resetVideoOutput(displayId, width, height);
}

// 打印使用帮助
void print_usage(const char* program_name) {
    LOG_INFO("Server", "Usage: " + std::string(program_name) + " [OPTIONS]");
    LOG_INFO("Server", "");
    LOG_INFO("Server", "Options:");
    LOG_INFO("Server", "  -p, --port PORT         Specify the port to listen on (default: " + std::to_string(DEFAULT_PORT) + ")");
    LOG_INFO("Server", "  -w, --width WIDTH       Screen width in pixels (default: " + std::to_string(DEFAULT_WIDTH) + ")");
    LOG_INFO("Server", "  -h, --height HEIGHT     Screen height in pixels (default: " + std::to_string(DEFAULT_HEIGHT) + ")");
    LOG_INFO("Server", "  -f, --framerate FPS     Frame rate in frames per second (default: " + std::to_string(DEFAULT_FPS) + ")");
    LOG_INFO("Server", "  -b, --bitrate BITRATE   Video bitrate in bits per second (default: " + std::to_string(DEFAULT_BITRATE) + ")");
    LOG_INFO("Server", "  -l, --log               Enable logging to /data/local/tmp/");
    LOG_INFO("Server", "  -V, --version           Show version information");
    LOG_INFO("Server", "  -H, --help              Show this help message");
    LOG_INFO("Server", "");
    LOG_INFO("Server", "Examples:");
    LOG_INFO("Server", "  " + std::string(program_name) + "                         # Use default settings on port " + std::to_string(DEFAULT_PORT));
    LOG_INFO("Server", "  " + std::string(program_name) + " -p 27184                # Listen on port 27184");
    LOG_INFO("Server", "  " + std::string(program_name) + " -w 720 -h 1280          # Set resolution to 720x1280");
    LOG_INFO("Server", "  " + std::string(program_name) + " -f 60 -b 8000000        # 60 fps, 8 Mbps bitrate");
    LOG_INFO("Server", "  " + std::string(program_name) + " -w 720 -h 1280 -f 30    # 720x1280@30fps");
    LOG_INFO("Server", "  " + std::string(program_name) + " -l                     # Enable logging");
    LOG_INFO("Server", "");
}

// 打印版本信息
void print_version() {
    LOG_INFO("Server", "====================================================================");
    LOG_INFO("Server", "        OpenHarmony_Scrcpy Server - " + std::string(VERSION) + " (author: luodh0157)        ");
    LOG_INFO("Server", "====================================================================");
}

// 解析命令行参数
void parse_arguments(int argc, char* argv[], CommandLineArgs& args) {
    // 定义长选项
    static struct option long_options[] = {
        {"port", required_argument, 0, 'p'},
        {"width", required_argument, 0, 'w'},
        {"height", required_argument, 0, 'h'},
        {"framerate", required_argument, 0, 'f'},
        {"bitrate", required_argument, 0, 'b'},
        {"log", no_argument, 0, 'l'},
        {"version", no_argument, 0, 'V'},
        {"help", no_argument, 0, 'H'},
        {0, 0, 0, 0}
    };
    
    int opt;
    int option_index = 0;
    int param = 0;
    
    while ((opt = getopt_long(argc, argv, "p:w:h:f:b:lV:H:?", long_options, &option_index)) != -1) {
        switch (opt) {
            case 'p':
                param = std::atoi(optarg);
                if (param <= 0 || param > 65535) {
                    LOG_ERROR("Server", "Invalid port: " + std::string(optarg) + ", use default " + std::to_string(args.port));
                } else {
                    args.port = param;
                }
                break;
                
            case 'w':
                param = std::atoi(optarg);
                if (param <= 0) {
                    LOG_ERROR("Server", "Invalid width: " + std::string(optarg) + ", use actual " + std::to_string(args.width));
                } else {
                    args.width = param;
                }
                break;
                
            case 'h':
                param = std::atoi(optarg);
                if (param <= 0) {
                    LOG_ERROR("Server", "Invalid height: " + std::string(optarg) + ", use actual " + std::to_string(args.height));
                } else {
                    args.height = param;
                }
                break;
                
            case 'f':
                param = std::atoi(optarg);
                if (param <= 0) {
                    LOG_ERROR("Server", "Invalid framerate: " + std::string(optarg) + ", use actual " + std::to_string(args.framerate));
                } else {
                    args.framerate = param;
                }
                break;
                
            case 'b':
                param = std::atoi(optarg);
                if (param <= 0) {
                    LOG_ERROR("Server", "Invalid bitrate: " + std::string(optarg) + ", use actual " + std::to_string(args.bitrate));
                } else {
                    args.bitrate = param;
                }
                break;
                
            case 'l':
                args.log_enabled = true;
                break;
                
            case 'V':
                args.show_version = true;
                break;
                
            case 'H':
            case '?':
            default:
                args.show_help = true;
                break;
        }
    }
}

// 主函数
int main(int argc, char* argv[]) {
    // 设置信号处理
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    print_version();

    // 获取设备屏幕信息
    CommandLineArgs args;
    OHScrcpyServer server;
    server.initCmdArgsFromDevice(args);

    // 解析命令行参数
    parse_arguments(argc, argv, args);
    
    if (args.log_enabled) {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        pid_t pid = getpid();
        std::stringstream ss;
        ss << LOG_FILE_PREFIX << pid << "_" << std::put_time(std::localtime(&time), "%Y%m%d_%H%M%S") << ".log";
        std::string log_path = ss.str();
        Logger::Instance().SetLogFile(log_path);
        Logger::Instance().EnableFile(true);
        LOG_INFO("Server", "Log file enabled: " + log_path);
    }
    
    if (args.show_help) {
        print_usage(argv[0]);
        return 0;
    }
    if (args.show_version) {
        return 0;
    }
    
    // 启动服务
    if (!server.start(args)) {
        LOG_ERROR("Server", "Start OHScrcpy server fail");
        return 1;
    }
    
    LOG_INFO("Server", "OHScrcpy server exit");
    return 0;
}