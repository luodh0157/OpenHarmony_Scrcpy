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

#include "logger.h"
#include "codec_wrapper.h"
#include "capture_wrapper.h"
#include "error_codes.h"

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

const std::string LOG_TAG = "Server";

// 全局控制标志
std::atomic<bool> g_running(false);
std::atomic<bool> g_client_connected(false);
std::atomic<bool> g_streaming(false);

// 信号处理
void signal_handler(int signum) {
    LOG_INFO(LOG_TAG, "Received signal " + std::to_string(signum) + ", shutting down...");
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
            LOG_INFO(LOG_TAG, "NetworkStreamer has been initialized");
            return true;
        }
        
        // 创建socket
        server_fd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd_ < 0) {
            LOG_ERROR(LOG_TAG, "Failed to create socket: " + std::string(strerror(errno)));
            return false;
        }
        
        // 设置socket选项
        int opt = 1;
        if (setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
            LOG_ERROR(LOG_TAG, "Failed to set SO_REUSEADDR: " + std::string(strerror(errno)));
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
            LOG_ERROR(LOG_TAG, "Failed to bind socket: " + std::string(strerror(errno)));
            return false;
        }
        
        // 开始监听
        if (listen(server_fd_, MAX_CLIENTS) < 0) {
            LOG_ERROR(LOG_TAG, "Failed to listen on socket: " + std::string(strerror(errno)));
            return false;
        }
        
        LOG_INFO(LOG_TAG, "Network streamer initialized on port " + std::to_string(port));
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
                LOG_ERROR(LOG_TAG, "Failed to accept client: " + std::string(strerror(errno)));
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
        LOG_INFO(LOG_TAG, "++++++++++++++++++++++++++++++++++++++++++++++++++++++");
        LOG_INFO(LOG_TAG, "Client connected from " + std::string(client_ip) + ":" + std::to_string(ntohs(client_addr_.sin_port)));
        
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
            LOG_INFO(LOG_TAG, "Client closed connection");
            disconnectClient();
            return false;
        } else if (n < 0) {
            if (errno != EWOULDBLOCK && errno != EAGAIN) {
                LOG_INFO(LOG_TAG, "Socket error: " + std::string(strerror(errno)));
                disconnectClient();
                return false;
            }
        }
        
        return true;
    }
    
    bool sendData(const void* data, size_t size) {
        if (client_fd_ < 0) {
            LOG_ERROR(LOG_TAG, "Invalid client fd");
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
                    LOG_INFO(LOG_TAG, "Buffer is full, wait a moment...");
                    usleep(1000);
                    continue;
                } else {
                    LOG_ERROR(LOG_TAG, "Failed to send data: " + std::string(strerror(errno)));
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
            case PACKET_TYPE_VPS: type_name = "VPS"; break;
            case PACKET_TYPE_KEYFRAME: type_name = "KEYFRAME"; break;
            case PACKET_TYPE_FRAME: type_name = "FRAME"; break;
            case PACKET_TYPE_CONFIG: type_name = "CONFIG"; break;
            case PACKET_TYPE_CONFIG_DATA: type_name = "CONFIG_DATA"; break;
            case PACKET_TYPE_LOG: type_name = "LOG"; break;
            default: type_name = "UNKNOWN"; break;
        }
        if (packet_type != PACKET_TYPE_HEARTBEAT) {
            LOG_INFO(LOG_TAG, "Send packet: type=" + std::string(type_name) + ", size=" + std::to_string(size) + " bytes");
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
            LOG_INFO(LOG_TAG, "sendConfig to client succ, " + config_str);
        } else {
            LOG_INFO(LOG_TAG, "sendConfig to client fail, " + config_str);
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
                LOG_ERROR(LOG_TAG, "receiveAck fail, received:" + std::to_string(received) + " errno:" + std::to_string(errno));
                break;
            }
            usleep(5000);  // 5ms
        }
        
        return false;
    }

    bool parseConfigAck(char *buffer, size_t size) {
        char *cfg_ack = strstr(buffer, "CONFIG_ACK");
        if (cfg_ack == nullptr) {
            LOG_ERROR(LOG_TAG, "invalid ACK: no include CONFIG_ACK");
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
                LOG_INFO(LOG_TAG, "Failed to send heartbeat, connection may be lost");
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
        LOG_INFO(LOG_TAG, "Client disconnected");
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
                    LOG_INFO(LOG_TAG, "Found SPS: " + std::to_string(sps.size()) + " bytes");
                } else if (nalu_type == NALU_TYPE_PPS) {
                    pps = std::move(nalu);
                    found_pps = true;
                    LOG_INFO(LOG_TAG, "Found PPS: " + std::to_string(pps.size()) + " bytes");
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
                    LOG_INFO(LOG_TAG, "Found VPS: " + std::to_string(vps.size()) + " bytes");
                } else if (nalu_type == H265_NALU_TYPE_SPS) {
                    sps = std::move(nalu);
                    found_sps = true;
                    LOG_INFO(LOG_TAG, "Found SPS: " + std::to_string(sps.size()) + " bytes");
                } else if (nalu_type == H265_NALU_TYPE_PPS) {
                    pps = std::move(nalu);
                    found_pps = true;
                    LOG_INFO(LOG_TAG, "Found PPS: " + std::to_string(pps.size()) + " bytes");
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




class OHScrcpyServer;

// 流传输上下文（用于管理编码数据发送）
struct StreamContext {
    NetworkStreamer* streamer;
    ScreenInfo screen_info;
    std::atomic<uint64_t> frame_count{0};
    std::atomic<bool> params_sent{false};
    bool is_hevc = false;
};

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
        stream_context_ = std::make_unique<StreamContext>();
    }
    
    bool start(const CommandLineArgs& args) {
        // 设置端口
        port_ = args.port;
        
        if (!initialize(args)) {
            LOG_ERROR(LOG_TAG, "OHScrcpyServer initialize fail");
            return false;
        }
        
        g_running = true;
        mainLoop();
        return true;
    }
    
    void stop() {
        LOG_INFO(LOG_TAG, "Stopping OHScrcpy Server...");
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
        LOG_INFO(LOG_TAG, "Resolution is changed, reset video output: displayId[" + std::to_string(displayId) + "] resolution[" + std::to_string(width) + "x" + std::to_string(height) + "]");
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
        LOG_INFO(LOG_TAG, "[Step 1] Check H.265 hardware encoder existence");
        OH_AVCapability *capability = OH_AVCodec_GetCapabilityByCategory(
            OH_AVCODEC_MIMETYPE_VIDEO_HEVC, true, HARDWARE);
        
        if (capability == nullptr) {
            LOG_INFO(LOG_TAG, "  H.265 hardware encoder NOT supported");
            return false;
        }
        
        LOG_INFO(LOG_TAG, "  H.265 hardware encoder supported");
        return true;
    }
    
    // H.265特定分辨率+帧率检测
    bool checkHevcSizeAndFrameRateSupported(int32_t width, int32_t height, int32_t fps) {
        OH_AVCapability *capability = OH_AVCodec_GetCapabilityByCategory(
            OH_AVCODEC_MIMETYPE_VIDEO_HEVC, true, HARDWARE);
        
        if (capability == nullptr) return false;
        
        bool supported = OH_AVCapability_AreVideoSizeAndFrameRateSupported(capability, width, height, fps);
        
        if (supported) {
            LOG_INFO(LOG_TAG, "  H.265 supports " + std::to_string(width) + "x" + std::to_string(height) + "@" + std::to_string(fps) + "fps");
        } else {
            LOG_INFO(LOG_TAG, "  H.265 does NOT support " + std::to_string(width) + "x" + std::to_string(height) + "@" + std::to_string(fps) + "fps");
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
            LOG_INFO(LOG_TAG, "  H.264 supports " + std::to_string(width) + "x" + std::to_string(height) + "@" + std::to_string(fps) + "fps");
        } else {
            LOG_INFO(LOG_TAG, "  H.264 does NOT support " + std::to_string(width) + "x" + std::to_string(height) + "@" + std::to_string(fps) + "fps");
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
        
        LOG_INFO(LOG_TAG, "  Searching " + codec + " supported resolutions (direction: " + (isHorizontal ? "horizontal" : "vertical") + ")...");
        
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
                LOG_INFO(LOG_TAG, "    " + res.name + " (" + std::to_string(res.width) + "x" + std::to_string(res.height) + ") - PASSED");
            } else {
                LOG_INFO(LOG_TAG, "    " + res.name + " (" + std::to_string(res.width) + "x" + std::to_string(res.height) + ") - NOT supported");
            }
        }
        
        if (candidates.empty()) {
            LOG_INFO(LOG_TAG, "  No " + codec + " supported resolution found!");
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
        
        LOG_INFO(LOG_TAG, "  Best " + codec + " match: " + best.name + " (" + std::to_string(best.width) + "x" + std::to_string(best.height) + ")");
        
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
            LOG_INFO(LOG_TAG, "[Step 2] Check if H.265 supports original resolution");
            if (checkHevcSizeAndFrameRateSupported(origWidth, origHeight, origFps)) {
                LOG_INFO(LOG_TAG, "  H.265 supports original resolution, using H.265 directly");
                screenInfo.codec = "h265";
                return true;
            }
            
            LOG_INFO(LOG_TAG, "[Step 3] Find H.265 supported resolution from standard list");
            StandardResolution hevcRes = findCodecSupportedResolution("h265", origWidth, origHeight, origFps);
            if (hevcRes.name != "none") {
                LOG_INFO(LOG_TAG, "  Found H.265 supported resolution, using H.265");
                applyCodecConfig(screenInfo, hevcRes, origBitrate, origWidth, origHeight, "h265");
                return true;
            }
            
            LOG_INFO(LOG_TAG, "[Step 4] No H.265 resolution found, fallback to H.264");
        } else {
            LOG_INFO(LOG_TAG, "[Step 2] No H.265 encoder, using H.264");
        }
        
        StandardResolution avcRes = findCodecSupportedResolution("h264", origWidth, origHeight, origFps);
        if (avcRes.name != "none") {
            LOG_INFO(LOG_TAG, "  Found H.264 supported resolution, using H.264");
            applyCodecConfig(screenInfo, avcRes, origBitrate, origWidth, origHeight, "h264");
            return true;
        }
        
        LOG_INFO(LOG_TAG, "  No codec supports any standard resolution! Forcing default 720x1280 H.264");
        applyDefaultConfig(screenInfo);
        return true;
    }
    
private:
    bool initialize(const CommandLineArgs& args) {
        LOG_INFO(LOG_TAG, "Initializing modules...");
        if (!network_.initialize(port_)) {
            LOG_ERROR(LOG_TAG, "Initialize network module fail");
            return false;
        }

        ScreenInfo screenInfo;
        if (!getPrimaryScreenInfo(screenInfo)) {
            LOG_ERROR(LOG_TAG, "Get primary screen info fail");
            return false;
        }
        
		selectCodecAndResolution(screenInfo, screenInfo.width, screenInfo.height,
                                 screenInfo.fps, screenInfo.bitrate);

        screen_info_ = screenInfo;
        LOG_INFO(LOG_TAG, "------------------------------------------------------");
        LOG_INFO(LOG_TAG, "Final config: " + std::to_string(screen_info_.width) + "x" + std::to_string(screen_info_.height) + "@" + std::to_string(screen_info_.fps) + "fps, codec=" + screen_info_.codec + ", bitrate=" + std::to_string(screen_info_.bitrate) + "bps");
		LOG_INFO(LOG_TAG, "------------------------------------------------------");
        return true;
    }

    bool getPrimaryScreenInfo(ScreenInfo &info) {
        auto display = DisplayManager::GetInstance().GetDefaultDisplay();
        if (display == nullptr) {
            LOG_ERROR(LOG_TAG, "DisplayManager::GetDefaultDisplay fail");
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
            LOG_ERROR(LOG_TAG, "DisplayManager::GetDefaultDisplay fail");
            return;
        }

        LOG_INFO(LOG_TAG, "------------------------------------------------------");
        LOG_INFO(LOG_TAG, "PrimaryDisplayDetailsInfo: ");
        LOG_INFO(LOG_TAG, "  id: " + std::to_string(display->GetId()) + ", name: " + std::string(display->GetName()));
        LOG_INFO(LOG_TAG, "  width: " + std::to_string(display->GetWidth()) + ", height: " + std::to_string(display->GetHeight()));
        LOG_INFO(LOG_TAG, "  phyWidth: " + std::to_string(display->GetPhysicalWidth()) + ", phyHeight: " + std::to_string(display->GetPhysicalHeight()));
        LOG_INFO(LOG_TAG, "  refreshRate: " + std::to_string(display->GetRefreshRate()) + ", rotation: " + std::to_string(static_cast<int32_t>(display->GetRotation())));
        
        std::vector<uint32_t> hdrFormats;
        display->GetSupportedHDRFormats(hdrFormats);
        std::string hdrStr = "  HDRFormats: [";
        for (uint32_t i = 0; i < hdrFormats.size(); ++i) {
            hdrStr += std::to_string(hdrFormats[i]);
            if (i < hdrFormats.size() - 1) hdrStr += ", ";
        }
        hdrStr += "]";
        LOG_INFO(LOG_TAG, hdrStr);

        std::vector<uint32_t> colorSpaces;
        display->GetSupportedColorSpaces(colorSpaces);
        std::string colorStr = "  ColorSpaces: [";
        for (uint32_t i = 0; i < colorSpaces.size(); ++i) {
            colorStr += std::to_string(colorSpaces[i]);
            if (i < colorSpaces.size() - 1) colorStr += ", ";
        }
        colorStr += "]";
        LOG_INFO(LOG_TAG, colorStr);
        LOG_INFO(LOG_TAG, "------------------------------------------------------");
    }
    
    bool initStreaming() {
        LOG_INFO(LOG_TAG, "Initializing streaming modules (encoder & capturer)...");
        
        CodecConfig codecConfig;
        codecConfig.width = screen_info_.width;
        codecConfig.height = screen_info_.height;
        codecConfig.fps = screen_info_.fps;
        codecConfig.bitrate = screen_info_.bitrate;
        codecConfig.codec = screen_info_.codec;
        
        stream_context_->streamer = &network_;
        stream_context_->screen_info = screen_info_;
        stream_context_->params_sent = false;
        stream_context_->is_hevc = (screen_info_.codec == "h265");
        
        ErrorCode ret = encoder_.Create(codecConfig);
        if (ret != ErrorCode::SUCCESS) {
            LOG_ERROR(LOG_TAG, "Create video encoder failed");
            return false;
        }
        
        encoder_.SetOutputCallback([this](uint8_t* data, size_t size, bool isKeyframe) {
            this->handleEncodedData(data, size, isKeyframe);
        });
        
        CaptureConfig captureConfig;
        captureConfig.width = screen_info_.width;
        captureConfig.height = screen_info_.height;
        captureConfig.fps = screen_info_.fps;
        captureConfig.displayId = screen_info_.displayid;
        
        ret = capturer_.Create();
        if (ret != ErrorCode::SUCCESS) {
            LOG_ERROR(LOG_TAG, "Create screen capturer failed");
            encoder_.Destroy();
            return false;
        }
        
        ret = capturer_.Init(captureConfig);
        if (ret != ErrorCode::SUCCESS) {
            LOG_ERROR(LOG_TAG, "Initialize screen capturer failed");
            encoder_.Destroy();
            capturer_.Destroy();
            return false;
        }
        
        ret = encoder_.Start();
        if (ret != ErrorCode::SUCCESS) {
            LOG_ERROR(LOG_TAG, "Start video encoder failed");
            encoder_.Destroy();
            capturer_.Destroy();
            return false;
        }
        
        OHNativeWindow* surface = encoder_.GetSurface();
        if (!surface) {
            LOG_ERROR(LOG_TAG, "Get encoder surface failed");
            encoder_.Stop();
            encoder_.Destroy();
            capturer_.Destroy();
            return false;
        }
        
        ret = capturer_.StartWithSurface(surface);
        if (ret != ErrorCode::SUCCESS) {
            LOG_ERROR(LOG_TAG, "Start screen capture with surface failed");
            encoder_.Stop();
            encoder_.Destroy();
            capturer_.Destroy();
            return false;
        }
        
        DisplayManager::GetInstance().RegisterDisplayListener(display_listener_);
        
        LOG_INFO(LOG_TAG, "Initialize streaming modules successfully");
        return true;
    }
    
    void stopStreaming(bool exit = false) {
        LOG_INFO(LOG_TAG, "Stopping streaming modules...");
        g_streaming = false;
        DisplayManager::GetInstance().UnregisterDisplayListener(display_listener_);
        capturer_.Stop();
        encoder_.Stop();
        capturer_.Destroy();
        encoder_.Destroy();
        stream_context_->params_sent = false;
        stream_context_->frame_count = 0;
        LOG_INFO(LOG_TAG, "Stop streaming modules complete");
        LOG_INFO(LOG_TAG, "++++++++++++++++++++++++++++++++++++++++++++++++++++++");
        if (!exit) {
            LOG_INFO(LOG_TAG, "Waiting for client connection...");
        }
    }
    
    void handleEncodedData(uint8_t* data, size_t size, bool isKeyframe) {
        if (!stream_context_->streamer || !stream_context_->streamer->hasClient()) {
            return;
        }
        
        if (!stream_context_->params_sent.load()) {
            if (stream_context_->is_hevc) {
                if (!encoder_.GetVPSData().empty() && 
                    !encoder_.GetSPSData().empty() && 
                    !encoder_.GetPPSData().empty()) {
                    
                    if (!stream_context_->streamer->sendVideoConfig(stream_context_->screen_info)) {
                        LOG_ERROR(LOG_TAG, "Failed to send video config");
                        return;
                    }
                    
                    if (!stream_context_->streamer->sendPacket(encoder_.GetVPSData().data(),
                                                              encoder_.GetVPSData().size(),
                                                              PACKET_TYPE_VPS)) {
                        LOG_ERROR(LOG_TAG, "Failed to send VPS");
                        return;
                    }
                    
                    if (!stream_context_->streamer->sendPacket(encoder_.GetSPSData().data(),
                                                              encoder_.GetSPSData().size(),
                                                              PACKET_TYPE_SPS)) {
                        LOG_ERROR(LOG_TAG, "Failed to send SPS");
                        return;
                    }
                    
                    if (!stream_context_->streamer->sendPacket(encoder_.GetPPSData().data(),
                                                              encoder_.GetPPSData().size(),
                                                              PACKET_TYPE_PPS)) {
                        LOG_ERROR(LOG_TAG, "Failed to send PPS");
                        return;
                    }
                    
                    stream_context_->params_sent = true;
                }
            } else {
                if (!encoder_.GetSPSData().empty() && 
                    !encoder_.GetPPSData().empty()) {
                    
                    if (!stream_context_->streamer->sendVideoConfig(stream_context_->screen_info)) {
                        LOG_ERROR(LOG_TAG, "Failed to send video config");
                        return;
                    }
                    
                    if (!stream_context_->streamer->sendPacket(encoder_.GetSPSData().data(),
                                                              encoder_.GetSPSData().size(),
                                                              PACKET_TYPE_SPS)) {
                        LOG_ERROR(LOG_TAG, "Failed to send SPS");
                        return;
                    }
                    
                    if (!stream_context_->streamer->sendPacket(encoder_.GetPPSData().data(),
                                                              encoder_.GetPPSData().size(),
                                                              PACKET_TYPE_PPS)) {
                        LOG_ERROR(LOG_TAG, "Failed to send PPS");
                        return;
                    }
                    
                    stream_context_->params_sent = true;
                }
            }
        }
        
        uint32_t packet_type = isKeyframe ? PACKET_TYPE_KEYFRAME : PACKET_TYPE_FRAME;
        
        if (stream_context_->streamer->sendPacket(data, size, packet_type)) {
            stream_context_->frame_count++;
            
            if (stream_context_->frame_count % 100 == 0) {
                LOG_INFO(LOG_TAG, "Sent " + std::to_string(stream_context_->frame_count.load()) + " frames");
            }
        }
    }
    
    void mainLoop() {
        LOG_INFO(LOG_TAG, "Entering main loop...");
        LOG_INFO(LOG_TAG, "Waiting for client connection...");
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
                        LOG_INFO(LOG_TAG, "Client disconnected, stopping streaming...");
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
                LOG_INFO(LOG_TAG, "Starting handshake with client...");
                
                if (!network_.sendConfig(screen_info_)) {
                    LOG_ERROR(LOG_TAG, "SendConfig to client fail, disconnected.");
                    network_.disconnectClient();
                    handshake_completed = false;
                    continue;
                }
                LOG_INFO(LOG_TAG, "SendConfig to client complete, waiting for client's ACK...");
                
                if (!network_.receiveAck(5000)) {
                    LOG_ERROR(LOG_TAG, "Waiting client config ACK timeout, disconnected.");
                    network_.disconnectClient();
                    handshake_completed = false;
                    continue;
                }
                LOG_INFO(LOG_TAG, "Received config ACK from client, handshake successful.");
                handshake_completed = true;
                
                if (!initStreaming()) {
                    LOG_ERROR(LOG_TAG, "initStreaming fail, disconnected.");
                    stopStreaming();
                    network_.disconnectClient();
                    handshake_completed = false;
                    continue;
                }
                
                g_streaming = true;
                LOG_INFO(LOG_TAG, "Streaming pipeline initialized successfully, starting transmission.");
            }
            
            // 5. 握手完成且流已初始化，进入正常数据传输
            if (handshake_completed && g_streaming) {
                static uint64_t last_frame_count = 0;
                uint64_t frame_count = stream_context_->frame_count.load();
                now = std::chrono::steady_clock::now();
                auto stat_elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - last_stat_time);
                if ((stat_elapsed.count() >= 5) && (last_frame_count != frame_count)) {
                    LOG_INFO(LOG_TAG, "Streaming active, frames sent: " + std::to_string(frame_count));
                    last_stat_time = now;
                    last_frame_count = frame_count;
                }
            }

            usleep(10000);
        }
        LOG_INFO(LOG_TAG, "Exiting main loop...");
    }
    
    void cleanup() {
        LOG_INFO(LOG_TAG, "Cleaning up resources...");
        stopStreaming(true);
        network_.closeAll();
        LOG_INFO(LOG_TAG, "Cleanup completed");
    }
    
private:
    int port_;
    ScreenInfo screen_info_;
    NetworkStreamer network_;
    CaptureWrapper capturer_;
    CodecWrapper encoder_;
    std::unique_ptr<StreamContext> stream_context_;
    sptr<DisplayManager::IDisplayListener> display_listener_;
};

void DisplayResolutionListener::OnChange(DisplayId displayId) {
    if (scrcpy_server_ == nullptr) {
        return;
    }
    auto display = DisplayManager::GetInstance().GetDisplayById(displayId);
    if (display == nullptr) {
        LOG_ERROR(LOG_TAG, "DisplayManager::GetDisplayById fail");
        return;
    }
    
    auto width = display->GetWidth();
    auto height = display->GetHeight();
    scrcpy_server_->resetVideoOutput(displayId, width, height);
}

// 打印使用帮助
void print_usage(const char* program_name) {
    LOG_INFO(LOG_TAG, "Usage: " + std::string(program_name) + " [OPTIONS]");
    LOG_INFO(LOG_TAG, "");
    LOG_INFO(LOG_TAG, "Options:");
    LOG_INFO(LOG_TAG, "  -p, --port PORT         Specify the port to listen on (default: " + std::to_string(DEFAULT_PORT) + ")");
    LOG_INFO(LOG_TAG, "  -w, --width WIDTH       Screen width in pixels (default: " + std::to_string(DEFAULT_WIDTH) + ")");
    LOG_INFO(LOG_TAG, "  -h, --height HEIGHT     Screen height in pixels (default: " + std::to_string(DEFAULT_HEIGHT) + ")");
    LOG_INFO(LOG_TAG, "  -f, --framerate FPS     Frame rate in frames per second (default: " + std::to_string(DEFAULT_FPS) + ")");
    LOG_INFO(LOG_TAG, "  -b, --bitrate BITRATE   Video bitrate in bits per second (default: " + std::to_string(DEFAULT_BITRATE) + ")");
    LOG_INFO(LOG_TAG, "  -l, --log               Enable logging to /data/local/tmp/");
    LOG_INFO(LOG_TAG, "  -V, --version           Show version information");
    LOG_INFO(LOG_TAG, "  -H, --help              Show this help message");
    LOG_INFO(LOG_TAG, "");
    LOG_INFO(LOG_TAG, "Examples:");
    LOG_INFO(LOG_TAG, "  " + std::string(program_name) + "                         # Use default settings on port " + std::to_string(DEFAULT_PORT));
    LOG_INFO(LOG_TAG, "  " + std::string(program_name) + " -p 27184                # Listen on port 27184");
    LOG_INFO(LOG_TAG, "  " + std::string(program_name) + " -w 720 -h 1280          # Set resolution to 720x1280");
    LOG_INFO(LOG_TAG, "  " + std::string(program_name) + " -f 60 -b 8000000        # 60 fps, 8 Mbps bitrate");
    LOG_INFO(LOG_TAG, "  " + std::string(program_name) + " -w 720 -h 1280 -f 30    # 720x1280@30fps");
    LOG_INFO(LOG_TAG, "  " + std::string(program_name) + " -l                     # Enable logging");
    LOG_INFO(LOG_TAG, "");
}

// 打印版本信息
void print_version() {
    LOG_INFO(LOG_TAG, "====================================================================");
    LOG_INFO(LOG_TAG, "        OpenHarmony_Scrcpy Server - " + std::string(VERSION) + " (author: luodh0157)        ");
    LOG_INFO(LOG_TAG, "====================================================================");
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
                    LOG_ERROR(LOG_TAG, "Invalid port: " + std::string(optarg) + ", use default " + std::to_string(args.port));
                } else {
                    args.port = param;
                }
                break;
                
            case 'w':
                param = std::atoi(optarg);
                if (param <= 0) {
                    LOG_ERROR(LOG_TAG, "Invalid width: " + std::string(optarg) + ", use actual " + std::to_string(args.width));
                } else {
                    args.width = param;
                }
                break;
                
            case 'h':
                param = std::atoi(optarg);
                if (param <= 0) {
                    LOG_ERROR(LOG_TAG, "Invalid height: " + std::string(optarg) + ", use actual " + std::to_string(args.height));
                } else {
                    args.height = param;
                }
                break;
                
            case 'f':
                param = std::atoi(optarg);
                if (param <= 0) {
                    LOG_ERROR(LOG_TAG, "Invalid framerate: " + std::string(optarg) + ", use actual " + std::to_string(args.framerate));
                } else {
                    args.framerate = param;
                }
                break;
                
            case 'b':
                param = std::atoi(optarg);
                if (param <= 0) {
                    LOG_ERROR(LOG_TAG, "Invalid bitrate: " + std::string(optarg) + ", use actual " + std::to_string(args.bitrate));
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
        LOG_INFO(LOG_TAG, "Log file enabled: " + log_path);
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
        LOG_ERROR(LOG_TAG, "Start OHScrcpy server fail");
        return 1;
    }
    
    LOG_INFO(LOG_TAG, "OHScrcpy server exit");
    return 0;
}