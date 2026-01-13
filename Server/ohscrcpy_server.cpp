/**
 * OHScrcpy 服务端实现 - 基于OpenHarmony C-API
 */

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
#define PACKET_TYPE_CONFIG_DATA    0x00000006

// 版本信息
#define VERSION "v1.2"

// H.264 NALU类型
enum H264NaluType {
    NALU_TYPE_SPS = 7,
    NALU_TYPE_PPS = 8,
    NALU_TYPE_IDR = 5,
    NALU_TYPE_SEI = 6,
    NALU_TYPE_NON_IDR = 1
};

// 全局控制标志
std::atomic<bool> g_running(false);
std::atomic<bool> g_client_connected(false);
std::atomic<bool> g_streaming(false);

// 信号处理
void signal_handler(int signum) {
    std::cout << "Received signal " << signum << ", shutting down..." << std::endl;
    g_running = false;
    g_streaming = false;
}

// 屏幕信息结构
struct ScreenInfo {
    int32_t width = DEFAULT_WIDTH;
    int32_t height = DEFAULT_HEIGHT;
    int32_t fps = DEFAULT_FPS;
    int32_t bitrate = DEFAULT_BITRATE;
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
            std::cout << "NetworkStreamer has been initialized" << std::endl;
            return true;
        }
        
        // 创建socket
        server_fd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd_ < 0) {
            std::cerr << "Failed to create socket: " << strerror(errno) << std::endl;
            return false;
        }
        
        // 设置socket选项
        int opt = 1;
        if (setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
            std::cerr << "Failed to set SO_REUSEADDR: " << strerror(errno) << std::endl;
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
            std::cerr << "Failed to bind socket: " << strerror(errno) << std::endl;
            return false;
        }
        
        // 开始监听
        if (listen(server_fd_, MAX_CLIENTS) < 0) {
            std::cerr << "Failed to listen on socket: " << strerror(errno) << std::endl;
            return false;
        }
        
        std::cout << "Network streamer initialized on port " << port << std::endl;
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
                std::cerr << "Failed to accept client: " << strerror(errno) << std::endl;
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
        std::cout << "++++++++++++++++++++++++++++++++++++++++++++++++++++++" << std::endl;
        std::cout << "Client connected from " << client_ip << ":" 
                  << ntohs(client_addr_.sin_port) << std::endl;
        
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
            std::cout << "Client closed connection" << std::endl;
            disconnectClient();
            return false;
        } else if (n < 0) {
            if (errno != EWOULDBLOCK && errno != EAGAIN) {
                std::cout << "Socket error: " << strerror(errno) << std::endl;
                disconnectClient();
                return false;
            }
        }
        
        return true;
    }
    
    bool sendData(const void* data, size_t size) {
        if (client_fd_ < 0) {
            std::cerr << "Invalid client fd" << std::endl;
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
                    // 缓冲区满，等待
                    std::cout << "Buffer is full, wait a moment..." << std::endl;
                    usleep(1000);
                    continue;
                } else {
                    std::cerr << "Failed to send data: " << strerror(errno) << std::endl;
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
            std::cout << "Send packet: type=" << type_name << ", size=" << size << " bytes" << std::endl;
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
            std::cout << "sendConfig to client succ, " << config_str;
        } else {
            std::cout << "sendConfig to client fail, " << config_str;
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
                std::cerr << "receiveAck fail, received:" << received << " errno:" << errno << std::endl;
                break;
            }
            usleep(5000);  // 5ms
        }
        
        return false;
    }

    bool parseConfigAck(char *buffer, size_t size) {
        char *cfg_ack = strstr(buffer, "CONFIG_ACK");
        if (cfg_ack == nullptr) {
            std::cerr << "invalid ACK: no include CONFIG_ACK" << std::endl;
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
                std::cout << "Failed to send heartbeat, connection may be lost" << std::endl;
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
        std::cout << "Client disconnected" << std::endl;
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
                    std::cout << "Found SPS: " << sps.size() << " bytes" << std::endl;
                } else if (nalu_type == NALU_TYPE_PPS) {
                    pps = std::move(nalu);
                    found_pps = true;
                    std::cout << "Found PPS: " << pps.size() << " bytes" << std::endl;
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

// 视频编码器回调上下文
struct EncoderContext {
    NetworkStreamer* streamer;
    ScreenInfo screen_info;
    std::atomic<uint64_t> frame_count{0};
    std::vector<uint8_t> sps_data;
    std::vector<uint8_t> pps_data;
    std::atomic<bool> sps_pps_sent{false};
};

// 视频编码类
class VideoEncoder {
public:
    VideoEncoder() : encoder_(nullptr), surface_(nullptr), is_encoding_(false) {
        context_ = std::make_unique<EncoderContext>();
    }
    
    ~VideoEncoder() { release(); }

    void printAvcVideoCodecCapability() {
        std::cout << "------------------------------------------------------" << std::endl;
        std::cout << "AVC(H.264) Video Codec Capability Info: " << std::endl;
        OH_AVCapability *capability = OH_AVCodec_GetCapabilityByCategory(OH_AVCODEC_MIMETYPE_VIDEO_AVC, true, HARDWARE);
        if (capability == nullptr) {
            std::cerr << "OH_AVCodec_GetCapabilityByCategory fail" << std::endl;
            return;
        }
        // 获取H.264解码器名称
        const char *codecName = OH_AVCapability_GetName(capability);
        std::cout << "  CodecName: " << codecName << std::endl;

        bool isSupported = OH_AVCapability_IsEncoderBitrateModeSupported(capability, BITRATE_MODE_CBR);
        bool isSupported2 = OH_AVCapability_IsEncoderBitrateModeSupported(capability, BITRATE_MODE_VBR);
        bool isSupported3 = OH_AVCapability_IsEncoderBitrateModeSupported(capability, BITRATE_MODE_CQ);
        std::cout << "  BitRateModeSupported: CBR[" << isSupported << "], VBR[" << isSupported2 << "], CQ[" 
                  << isSupported3 << "]" << std::endl;

        // 获取码率范围
        OH_AVRange bitrateRange = {-1, -1};
        int32_t ret = OH_AVCapability_GetEncoderBitrateRange(capability, &bitrateRange);
        if (ret == AV_ERR_OK) {
            std::cout << "  BitRateRange: [" << bitrateRange.minVal << "~" << bitrateRange.maxVal << "]";
        }
        OH_AVRange qualityRange = {-1, -1};
        ret = OH_AVCapability_GetEncoderQualityRange(capability, &qualityRange);
        if (ret == AV_ERR_OK) {
            std::cout << "QualityRange: [" << qualityRange.minVal << "~" << qualityRange.maxVal << "]" << std::endl;
        }

        // 获取profile范围
        const int32_t *profiles = nullptr;
        uint32_t profileNum = 0;
        ret = OH_AVCapability_GetSupportedProfiles(capability, &profiles, &profileNum);
        if (ret == AV_ERR_OK) {
            std::cout << "  SupportedProfiles: [";
            for (uint32_t i = 0; i < profileNum; i++) {
                std::cout << profiles[i];
                if (i < profileNum - 1) std::cout << ",";
            }
            std::cout << "]" << std::endl;
        }

        // 获取AVC_PROFILE_MAIN对应的Level范围
        int32_t profile = OH_AVCProfile::AVC_PROFILE_MAIN;
        const int32_t *levels = nullptr;
        uint32_t levelNum = 0;
        ret = OH_AVCapability_GetSupportedLevelsForProfile(capability, profile, &levels, &levelNum);
        if (ret == AV_ERR_OK) {
            std::cout << "  SupportedLevelsForProfile " << profile << ": [";
            for (uint32_t i = 1; i < levelNum; i++) {
               std::cout << levels[i];
               if (i < levelNum - 1) std::cout << ",";
            }
            std::cout << "]" << std::endl;
        }

        // 获取支持的宽范围
        OH_AVRange widthRange = {-1, -1};
        ret = OH_AVCapability_GetVideoWidthRange(capability, &widthRange);
        if (ret == AV_ERR_OK) {
            std::cout << "  WidthRange: [" << widthRange.minVal << "," << widthRange.maxVal << "]";
        }
        // 获取支持的高范围
        OH_AVRange heightRange = {-1, -1};
        ret = OH_AVCapability_GetVideoHeightRange(capability, &heightRange);
        if (ret == AV_ERR_OK) {
            std::cout << ", HeightRange: [" << heightRange.minVal << "," << heightRange.maxVal << "]";
        }
        // 获取支持的帧率范围
        OH_AVRange frameRateRange = {-1, -1};
        ret = OH_AVCapability_GetVideoFrameRateRange(capability, &frameRateRange);
        if (ret == AV_ERR_OK) {
            std::cout << ", FrameRateRange: [" << frameRateRange.minVal << "," << frameRateRange.maxVal << "]" << std::endl;
        }

        // 获取宽对齐要求
        int32_t widthAlignment = 0;
        ret = OH_AVCapability_GetVideoWidthAlignment(capability, &widthAlignment);
        if (ret == AV_ERR_OK) {
            std::cout << "  WidthAlignment: " << widthAlignment;
        }
        // 获取高对齐要求
        int32_t heightAlignment = 0;
        ret = OH_AVCapability_GetVideoHeightAlignment(capability, &heightAlignment);
        if (ret == AV_ERR_OK) {
            std::cout << ", HeightAlignment: " << heightAlignment << std::endl;
        }

        // 获取支持的像素格式
        const int32_t *pixFormats = nullptr;
        uint32_t pixFormatNum = 0;
        ret = OH_AVCapability_GetVideoSupportedPixelFormats(capability, &pixFormats, &pixFormatNum);
        if (ret == AV_ERR_OK) {
            std::cout << "  SupportedPixelFormats: [";
            for (uint32_t i = 1; i < pixFormatNum; i++) {
               std::cout << pixFormats[i];
               if (i < pixFormatNum - 1) std::cout << ",";
            }
            std::cout << "]" << std::endl;
        }
        // 获取是否支持低时延特性
        isSupported = OH_AVCapability_IsFeatureSupported(capability, VIDEO_LOW_LATENCY);
        std::cout << "  IsFeatureSupported VIDEO_LOW_LATENCY: " << isSupported << std::endl;

        int32_t width = 720;
        int32_t height = 1280;
        // 获取指定视频宽高是否支持
        isSupported = OH_AVCapability_IsVideoSizeSupported(capability, width, height);
        std::cout << "  [720*1280] IsVideoSizeSupported: " << isSupported;
        // 获取指定视频尺寸支持的帧率范围
        frameRateRange = {-1, -1};
        ret = OH_AVCapability_GetVideoFrameRateRangeForSize(capability, width, height, &frameRateRange);
        if (ret == AV_ERR_OK) {
            std::cout << ", FrameRateRange: [" << frameRateRange.minVal << "," << frameRateRange.maxVal << "]" << std::endl;
        }

        std::cout << "------------------------------------------------------" << std::endl;
    }
    
    bool initialize(const ScreenInfo& info, NetworkStreamer* streamer) {
        if (encoder_ != nullptr) {
            std::cout << "VideoEncoder has been initialized" << std::endl;
            return true;
        }
        std::cout << "Initializing VideoEncoder..." << std::endl;

        printAvcVideoCodecCapability();
        
        // 创建H.264编码器实例
        encoder_ = OH_VideoEncoder_CreateByMime(OH_AVCODEC_MIMETYPE_VIDEO_AVC);
        if (encoder_ == nullptr) {
            std::cerr << "OH_VideoEncoder_CreateByMime fail" << std::endl;
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
            std::cerr << "OH_VideoEncoder_RegisterCallback fail, err: " << ret << std::endl;
            return false;
        }
        
        // 创建并配置编码格式
        OH_AVFormat* format = OH_AVFormat_Create();
        if (format == nullptr) {
            std::cerr << "OH_AVFormat_Create fail" << std::endl;
            return false;
        }
        // 设置编码参数
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_WIDTH, info.width);
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_HEIGHT, info.height);
        OH_AVFormat_SetDoubleValue(format, OH_MD_KEY_FRAME_RATE, info.fps);
        OH_AVFormat_SetLongValue(format, OH_MD_KEY_BITRATE, info.bitrate); // 必须配置，设置码率，单位为bps。
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_PIXEL_FORMAT, AV_PIXEL_FORMAT_RGBA);
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_VIDEO_ENCODE_BITRATE_MODE, OH_BitrateMode::BITRATE_MODE_VBR);
		OH_AVFormat_SetIntValue(format, OH_MD_KEY_PROFILE, OH_AVCProfile::AVC_PROFILE_MAIN);
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_I_FRAME_INTERVAL, 500); // 关键帧间隔，单位毫秒
        
        // 配置编码器
        ret = OH_VideoEncoder_Configure(encoder_, format);
        if (ret != AV_ERR_OK && ret != AV_ERR_INVALID_VAL) {
            std::cerr << "OH_VideoEncoder_Configure fail, err: " << ret << std::endl;
            OH_AVFormat_Destroy(format);
            return false;
        }
        OH_AVFormat_Destroy(format);
        
        // 获取编码器的Surface
        ret = OH_VideoEncoder_GetSurface(encoder_, &surface_);
        if (ret != AV_ERR_OK || surface_ == nullptr) {
            std::cerr << "OH_VideoEncoder_GetSurface fail, err: " << ret << std::endl;
            return false;
        }

        // 准备编码器
        ret = OH_VideoEncoder_Prepare(encoder_);
        if (ret != AV_ERR_OK) {
            std::cerr << "OH_VideoEncoder_Prepare fail, err: " << ret << std::endl;
            return false;
        }

        context_->streamer = streamer;
        context_->screen_info = info;
        context_->sps_pps_sent = false;
        std::cout << "VideoEncoder initialized successfully" << std::endl;
        return true;
    }
    
    bool start() {
        if (encoder_ == nullptr) {
            std::cerr << "VideoEncoder has not been initialized" << std::endl;
            return false;
        }
        
        is_encoding_ = true;
        int32_t ret = OH_VideoEncoder_Start(encoder_);
        if (ret != AV_ERR_OK) {
            std::cerr << "OH_VideoEncoder_Start fail, err: " << ret << std::endl;
            is_encoding_ = false;
            return false;
        }

        std::cout << "VideoEncoder started" << std::endl;
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
    
    bool sendSpsPps() {
        if (!context_->sps_data.empty() && !context_->pps_data.empty()) {
            std::cout << "Sending SPS (" << context_->sps_data.size() << " bytes) and PPS (" 
                    << context_->pps_data.size() << " bytes)" << std::endl;
            
            // 打印SPS/PPS详细信息
            std::cout << "SPS: ";
            for (size_t i = 0; i < context_->sps_data.size(); i++) {
                printf("%02x ", context_->sps_data[i]);
            }
            std::cout << std::endl;
            
            std::cout << "PPS: ";
            for (size_t i = 0; i < context_->pps_data.size(); i++) {
                printf("%02x ", context_->pps_data[i]);
            }
            std::cout << std::endl;
            
            // 发送SPS
            if (!context_->streamer->sendPacket(context_->sps_data.data(), 
                                            context_->sps_data.size(), 
                                            PACKET_TYPE_SPS)) {
                std::cerr << "Failed to send SPS" << std::endl;
                return false;
            }
            
            // 发送PPS
            if (!context_->streamer->sendPacket(context_->pps_data.data(), 
                                            context_->pps_data.size(), 
                                            PACKET_TYPE_PPS)) {
                std::cerr << "Failed to send PPS" << std::endl;
                return false;
            }
            
            // 发送视频配置信息
            if (!context_->streamer->sendVideoConfig(context_->screen_info)) {
                std::cerr << "Failed to send video config" << std::endl;
                return false;
            }
            
            context_->sps_pps_sent = true;
            return true;
        }
        
        std::cerr << "No SPS/PPS data to send" << std::endl;
        return false;
    }

    bool isEncoding() const { return is_encoding_; }
    uint64_t getFrameCount() const { return context_->frame_count; }
    bool isSpsPpsSent() const { return context_->sps_pps_sent.load(); }
    
    OH_AVCodec* getEncoder() const { return encoder_; }
    OHNativeWindow* getSurface() const { return surface_; }
    
    // 静态回调函数
    static void onError(OH_AVCodec* codec, int32_t errorCode, void* userData) {
        std::cerr << "VideoEncoder error: " << errorCode << std::endl;
    }
    
    static void onStreamChanged(OH_AVCodec* codec, OH_AVFormat* format, void* userData) {
        // Surface模式下，该回调函数在surface分辨率变化时触发
        (void)codec;
        (void)userData;
        int32_t width = 0, height = 0;
        OH_AVFormat_GetIntValue(format, OH_MD_KEY_WIDTH, &width);
        OH_AVFormat_GetIntValue(format, OH_MD_KEY_HEIGHT, &height);
        std::cout << "VideoEncoder stream changed: " << width << "x" << height << std::endl;
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
                std::cerr << "OH_AVBuffer_GetBufferAttr fail, err: " << ret << std::endl;
                return;
            }
            uint32_t no_need_flags = AVCODEC_BUFFER_FLAGS_DISCARD | AVCODEC_BUFFER_FLAGS_DISPOSABLE | 
                AVCODEC_BUFFER_FLAGS_EOS;
            if ((info.flags & no_need_flags) != 0) {
                if ((info.flags & AVCODEC_BUFFER_FLAGS_EOS) != 0) {
                    std::cout << "End-of-Stream frame" << std::endl;
                }
                OH_VideoEncoder_FreeOutputBuffer(codec, index);
                return;
            }
            uint8_t *addr = OH_AVBuffer_GetAddr(buffer);
            if (addr == nullptr) {
                std::cerr << "OH_AVBuffer_GetAddr fail" << std::endl;
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
            std::cerr << "Invalid codec or buffer in callback" << std::endl;
            return false;
        }
        
        VideoEncoder* self = static_cast<VideoEncoder*>(userData);
        if (!self || !self->context_ || !self->context_->streamer) {
            std::cerr << "Invalid context in output buffer callback" << std::endl;
            return false;
        }
        
        if (!self->isEncoding()) {
            std::cout << "Encoder not in encoding state, skipping frame" << std::endl;
            return false;
        }
        return true;
    }

    static void handleCofingFrame(VideoEncoder* self, uint8_t *addr, size_t size) {
        std::cout << "Received codec config data: " << size << " bytes" << std::endl;
        
        // 尝试提取SPS和PPS
        std::vector<uint8_t> sps, pps;
        if (H264Utils::extractSpsPpsAnnexB(addr, size, sps, pps)) {
            self->context_->sps_data = std::move(sps);
            self->context_->pps_data = std::move(pps);
            
            // 立即发送SPS/PPS
            if (self->context_->streamer->hasClient()) {
                self->sendSpsPps();
            }
        } else {
            std::cout << "Could not extract SPS/PPS from config data, sending raw config" << std::endl;
            
            // 如果无法提取，直接发送配置数据
            if (self->context_->streamer->hasClient()) {
                self->context_->streamer->sendPacket((const void*)addr, size, PACKET_TYPE_SPS);
            }
        }
    }

    static void handleNormalFrame(VideoEncoder* self, uint8_t *addr, size_t size, uint32_t flags) {
        // 处理视频帧数据
        bool is_keyframe = (flags & AVCODEC_BUFFER_FLAGS_SYNC_FRAME) > 0;
        uint32_t packet_type = is_keyframe ? PACKET_TYPE_KEYFRAME : PACKET_TYPE_FRAME;
        if ((flags & AVCODEC_BUFFER_FLAGS_INCOMPLETE_FRAME) > 0) {
            std::cout << "Recv INCOMPLETE_FRAME" << std::endl;
        }
        
        // 如果SPS/PPS尚未发送，尝试从帧数据中提取
        if (is_keyframe && !self->context_->sps_pps_sent.load()) {
            std::vector<uint8_t> sps, pps;
            if (H264Utils::extractSpsPpsAnnexB(addr, size, sps, pps)) {
                self->context_->sps_data = std::move(sps);
                self->context_->pps_data = std::move(pps);
                self->sendSpsPps();
            } else {
                std::cerr << "Failed to extract SPS/PPS from keyframe" << std::endl;
            }
        }
        
        // 发送视频数据
        if (self->context_->streamer->hasClient()) {
            self->context_->streamer->sendPacket((const void*)addr, size, packet_type);
            self->context_->frame_count++;
            
            // 每100帧打印一次统计信息
            static uint64_t last_frame_count = 0;
            if ((last_frame_count != self->context_->frame_count) && (self->context_->frame_count % 100 == 0)) {
                std::cout << "Sent " << self->context_->frame_count << " frames" << std::endl;
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
            std::cout << "ScreenCapturer has been initialized" << std::endl;
            return true;
        }
        std::cout << "Initializing ScreenCapturer..." << std::endl;
        
        // 创建屏幕捕获实例
        capture_ = OH_AVScreenCapture_Create();
        if (capture_ == nullptr) {
            std::cerr << "OH_AVScreenCapture_Create fail" << std::endl;
            return false;
        }
        
        // 配置视频捕获信息
        OH_VideoCaptureInfo videoCapInfo = {
            .videoFrameWidth = info.width,
            .videoFrameHeight = info.height,
            .videoSource = OH_VIDEO_SOURCE_SURFACE_RGBA
        };
        
        // 配置视频编码信息
        OH_VideoEncInfo videoEncInfo = {
            .videoCodec = OH_VideoCodecFormat::OH_H264,
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
            std::cerr << "OH_AVScreenCapture_Init fail, err: " << ret << std::endl;
            return false;
        }

        // 关闭MIC
        OH_AVScreenCapture_SetMicrophoneEnabled(capture_, false);
        
        // 设置错误回调
        ret = OH_AVScreenCapture_SetErrorCallback(capture_, &ScreenCapturer::onError, this);
        if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
            std::cerr << "OH_AVScreenCapture_SetErrorCallback fail, err: " << ret << std::endl;
            return false;
        }
        
        // 设置状态回调
        ret = OH_AVScreenCapture_SetStateCallback(capture_, &ScreenCapturer::onStateChange, this);
        if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
            std::cerr << "OH_AVScreenCapture_SetStateCallback fail, err: " << ret << std::endl;
            return false;
        }
        
        // 设置数据回调
        ret = OH_AVScreenCapture_SetDataCallback(capture_, &ScreenCapturer::onBufferAvailable, this);
        if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
            std::cerr << "OH_AVScreenCapture_SetDataCallback fail, err: " << ret << std::endl;
            return false;
        }
        
        // 保存上下文
        encoder_ = encoder;
        streamer_ = streamer;
        screen_info_ = info;
        std::cout << "Screen capturer initialized: " 
                  << info.width << "x" << info.height 
                  << "@" << info.fps << "fps" << std::endl;
        return true;
    }
    
    bool start() {
        if (capture_ == nullptr || encoder_ == nullptr) {
            std::cerr << "ScreenCapturer has not been initialized" << std::endl;
            return false;
        }
        
        // 以Surface模式开始屏幕录制
        int32_t ret = OH_AVScreenCapture_StartScreenCaptureWithSurface(capture_, encoder_->getSurface());
        if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
            std::cerr << "OH_AVScreenCapture_StartScreenCaptureWithSurface fail, err: " << ret << std::endl;
            return false;
        }
        
        is_capturing_ = true;
        std::cout << "Screen capture started" << std::endl;
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
        std::cerr << "Screen capture error: " << errorCode << std::endl;
    }
    
    void handleStateChange(OH_AVScreenCapture* capture, OH_AVScreenCaptureStateCode stateCode) {
        if (stateCode == OH_SCREEN_CAPTURE_STATE_STARTED) {
            std::cout << "Screen capture state: STARTED" << std::endl;
        } else if (stateCode == OH_SCREEN_CAPTURE_STATE_STOPPED_BY_CALL) {
            std::cout << "Screen capture state: STOPPED_BY_CALL" << std::endl;
            is_capturing_ = false;
        } else if (stateCode == OH_SCREEN_CAPTURE_STATE_CANCELED) {
            std::cout << "Screen capture state: CANCELED" << std::endl;
            is_capturing_ = false;
        } else {
            std::cout << "Screen capture state code:" << stateCode << std::endl;
        }
    }
    
    void handleBufferAvailable(OH_AVScreenCapture* capture, OH_AVBuffer* buffer, 
                              OH_AVScreenCaptureBufferType bufferType, int64_t timestamp) {
        std::cout << "Enter handleBufferAvailable" << std::endl;
        // 使用Surface模式，这个回调主要用于音频数据处理
        // 对于视频数据，通过Surface直接传递给编码器
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

// 主服务类
class OHScrcpyServer {
public:
    OHScrcpyServer() : port_(DEFAULT_PORT), screen_info_{} {}
    
    bool start(const CommandLineArgs& args, bool isUserCfg = false) {
        // 设置端口
        port_ = args.port;
        
        if (!initialize(args, isUserCfg)) {
            std::cerr << "OHScrcpyServer initialize fail" << std::endl;
            return false;
        }
        
        g_running = true;
        mainLoop();
        return true;
    }
    
    void stop() {
        std::cout << "Stopping OHScrcpy Server..." << std::endl;
        g_running = false;
        g_streaming = false;
        cleanup();
    }
    
private:
    bool initialize(const CommandLineArgs& args, bool isUserCfg = false) {
        std::cout << "Initializing modules..." << std::endl;
        // 1. 初始化网络模块
        if (!network_.initialize(port_)) {
            std::cerr << "Initialize network module fail" << std::endl;
            return false;
        }

        // 2. 设置屏幕显示信息
        if (!isUserCfg) {
            getPrimaryScreenInfo(screen_info_);
        } else {
            screen_info_.width = args.width;
            screen_info_.height = args.height;
            screen_info_.fps = args.framerate;
            screen_info_.bitrate = args.bitrate;
        }

        std::cout << "Configuration info: " << screen_info_.width << "x" 
                  << screen_info_.height << "@" << screen_info_.fps << "fps" 
                  << " bitrate:" << screen_info_.bitrate << std::endl;
        return true;
    }

    bool getPrimaryScreenInfo(ScreenInfo &info) {
        auto display = OHOS::Rosen::DisplayManager::GetInstance().GetDefaultDisplay();
        if (display == nullptr) {
            std::cerr << "DisplayManager::GetDefaultDisplay fail" << std::endl;
            // 使用默认值
            info.width = DEFAULT_WIDTH;
            info.height = DEFAULT_HEIGHT;
            info.fps = DEFAULT_FPS;
            info.bitrate = DEFAULT_BITRATE;
            info.codec = "h264";
            return false;
        }
        
        info.width = display->GetWidth();
        info.height = display->GetHeight();
        info.fps = DEFAULT_FPS;
        info.bitrate = DEFAULT_BITRATE;
        info.codec = "h264";
        return true;
    }

    void printScreenDetailsInfo() {
        auto display = OHOS::Rosen::DisplayManager::GetInstance().GetDefaultDisplay();
        if (display == nullptr) {
            std::cerr << "DisplayManager::GetDefaultDisplay fail" << std::endl;
            return;
        }

        std::cout << "------------------------------------------------------" << std::endl;
        std::cout << "PrimaryDisplayDetailsInfo: " << std::endl;
        std::cout << "  RefreshRate: " << display->GetRefreshRate()
                  << " ,Rotation: " << static_cast<int32_t>(display->GetRotation()) << std::endl;
        std::vector<uint32_t> hdrFormats;
        display->GetSupportedHDRFormats(hdrFormats);
        std::cout << "  HDRFormats: [";
        for (uint32_t i = 0; i < hdrFormats.size(); ++i) {
            std::cout << hdrFormats[i];
            if (i < hdrFormats.size() - 1) std::cout << ", ";
        }
        std::cout << "]" << std::endl;

        std::vector<uint32_t> colorSpaces;
        display->GetSupportedColorSpaces(colorSpaces);
        std::cout << "  ColorSpaces: [";
        for (uint32_t i = 0; i < colorSpaces.size(); ++i) {
            std::cout << colorSpaces[i];
            if (i < colorSpaces.size() - 1) std::cout << ", ";
        }
        std::cout << "]" << std::endl;

        std::string capability;
        display->GetDisplayCapability(capability);
        std::cout << "  DisplayCapability: " << capability << std::endl;
        std::cout << "------------------------------------------------------" << std::endl;
    }
    
    bool initStreaming() {
        std::cout << "Initializing streaming modules (encoder & capturer)..." << std::endl;
        
        // 1. 初始化视频编码器
        if (!encoder_.initialize(screen_info_, &network_)) {
            std::cerr << "Initialize video encoder fail" << std::endl;
            return false;
        }

        // 2. 初始化屏幕捕获器
        if (!capturer_.initialize(screen_info_, &encoder_, &network_)) {
            std::cerr << "Initialize screen capturer fail" << std::endl;
            encoder_.release();
            return false;
        }

        // 3. 开始编码
        if (!encoder_.start()) {
            std::cerr << "Failed to start video encoder" << std::endl;
            capturer_.release();
            encoder_.release();
            return false;
        }
        
        // 4. 开始捕获
        if (!capturer_.start()) {
            std::cerr << "Failed to start screen capture" << std::endl;
            encoder_.stop();
            capturer_.release();
            encoder_.release();
            return false;
        }

        std::cout << "Initialize streaming modules successfully" << std::endl;
        return true;
    }
    
    void stopStreaming(bool exit = false) {
        std::cout << "Stopping streaming modules..." << std::endl;
        g_streaming = false;
        capturer_.stop();
        encoder_.stop();
        capturer_.release();
        encoder_.release();
        std::cout << "Stop streaming modules complete" << std::endl;
        std::cout << "++++++++++++++++++++++++++++++++++++++++++++++++++++++" << std::endl;
        if (!exit) {
            std::cout << std::endl << "Waiting for client connection..." << std::endl;
        }
    }
    
    void mainLoop() {
        std::cout << "Entering main loop..." << std::endl;
        std::cout << "Waiting for client connection..." << std::endl;
        auto last_stat_time = std::chrono::steady_clock::now();
        auto last_heartbeat_time = std::chrono::steady_clock::now();
        auto last_connection_check = std::chrono::steady_clock::now();
        
        // 用于跟踪是否已完成初始握手的标志
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
                        std::cout << "Client disconnected, stopping streaming..." << std::endl;
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
                std::cout << "Starting handshake with client..." << std::endl;
                
                // 4.1 发送配置信息
                if (!network_.sendConfig(screen_info_)) {
                    std::cerr << "SendConfig to client fail, disconnected." << std::endl;
                    network_.disconnectClient();
                    handshake_completed = false;
                    continue;
                }
                std::cout << "SendConfig to client complete, waiting for client's ACK..." << std::endl;
                
                // 4.2 等待客户端确认 (CONFIG_ACK)
                if (!network_.receiveAck(5000)) {
                    std::cerr << "Waiting client config ACK timeout, disconnected." << std::endl;
                    network_.disconnectClient();
                    handshake_completed = false;
                    continue;
                }
                std::cout << "Received config ACK from client, handshake successful." << std::endl;
                handshake_completed = true;
                
                // 4.3 握手成功后，立即尝试初始化流媒体模块
                if (!initStreaming()) {
                    std::cerr << "initStreaming fail, disconnected." << std::endl;
                    stopStreaming();
                    network_.disconnectClient();
                    handshake_completed = false;
                    continue;
                }
                
                // 流媒体初始化成功
                g_streaming = true;
                std::cout << "Streaming pipeline initialized successfully, starting transmission." << std::endl;
            }
            
            // 5. 握手完成且流已初始化，进入正常数据传输
            if (handshake_completed && g_streaming) {
                // 定期打印统计信息
                static uint64_t last_frame_count = 0;
                uint64_t frame_count = encoder_.getFrameCount();
                auto now = std::chrono::steady_clock::now();
                auto stat_elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - last_stat_time);
                if ((stat_elapsed.count() >= 5) && (last_frame_count != frame_count)) {
                    std::cout << "Streaming active, frames sent: " << frame_count << std::endl;
                    last_stat_time = now;
                    last_frame_count = frame_count;
                }
            }

            usleep(10000); // 10ms
        }
        std::cout << "Exiting main loop..." << std::endl;
    }
    
    void cleanup() {
        std::cout << "Cleaning up resources..." << std::endl;
        stopStreaming(true);
        network_.closeAll();
        std::cout << "Cleanup completed" << std::endl;
    }
    
private:
    int port_;
    ScreenInfo screen_info_;
    NetworkStreamer network_;
    ScreenCapturer capturer_;
    VideoEncoder encoder_;
};

// 打印使用帮助
void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " [OPTIONS]" << std::endl;
    std::cout << std::endl;
    std::cout << "Options:" << std::endl;
    std::cout << "  -p, --port PORT         Specify the port to listen on (default: " << DEFAULT_PORT << ")" << std::endl;
    std::cout << "  -w, --width WIDTH       Screen width in pixels (default: " << DEFAULT_WIDTH << ")" << std::endl;
    std::cout << "  -h, --height HEIGHT     Screen height in pixels (default: " << DEFAULT_HEIGHT << ")" << std::endl;
    std::cout << "  -f, --framerate FPS     Frame rate in frames per second (default: " << DEFAULT_FPS << ")" << std::endl;
    std::cout << "  -b, --bitrate BITRATE   Video bitrate in bits per second (default: " << DEFAULT_BITRATE << ")" << std::endl;
    std::cout << "  -V, --version           Show version information" << std::endl;
    std::cout << "  -H, --help              Show this help message" << std::endl;
    std::cout << std::endl;
    std::cout << "Examples:" << std::endl;
    std::cout << "  " << program_name << "                         # Use default settings on port " << DEFAULT_PORT << std::endl;
    std::cout << "  " << program_name << " -p 27184                # Listen on port 27184" << std::endl;
    std::cout << "  " << program_name << " -w 720 -h 1280          # Set resolution to 720x1280" << std::endl;
    std::cout << "  " << program_name << " -f 60 -b 8000000        # 60 fps, 8 Mbps bitrate" << std::endl;
    std::cout << "  " << program_name << " -w 720 -h 1280 -f 30    # 720x1280@30fps" << std::endl;
    std::cout << std::endl;
}

// 打印版本信息
void print_version() {
    std::cout << "====================================================================" << std::endl;
    std::cout << "        OpenHarmony_Scrcpy Server - " << VERSION << " (author: luodh0157)        " << std::endl;
    std::cout << "====================================================================" << std::endl;
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
        {"version", no_argument, 0, 'V'},
        {"help", no_argument, 0, 'H'},
        {0, 0, 0, 0}
    };
    
    int opt;
    int option_index = 0;
    
    while ((opt = getopt_long(argc, argv, "p:w:h:f:b:V:H:?", long_options, &option_index)) != -1) {
        switch (opt) {
            case 'p':
                args.port = std::atoi(optarg);
                if (args.port <= 0 || args.port > 65535) {
                    std::cerr << "Invalid port: " << optarg << ", use default " << DEFAULT_PORT << std::endl;
                    args.port = DEFAULT_PORT;
                }
                break;
                
            case 'w':
                args.width = std::atoi(optarg);
                if (args.width <= 0) {
                    std::cerr << "Invalid width: " << optarg << ", use default " << DEFAULT_WIDTH << std::endl;
                    args.width = DEFAULT_WIDTH;
                }
                break;
                
            case 'h':
                args.height = std::atoi(optarg);
                if (args.height <= 0) {
                    std::cerr << "Invalid height: " << optarg << ", use default " << DEFAULT_HEIGHT << std::endl;
                    args.height = DEFAULT_HEIGHT;
                }
                break;
                
            case 'f':
                args.framerate = std::atoi(optarg);
                if (args.framerate <= 0) {
                    std::cerr << "Invalid framerate: " << optarg << ", use default " << DEFAULT_FPS << std::endl;
                    args.framerate = DEFAULT_FPS;
                }
                break;
                
            case 'b':
                args.bitrate = std::atoi(optarg);
                if (args.bitrate <= 0) {
                    std::cerr << "Invalid bitrate: " << optarg << ", use default " << DEFAULT_BITRATE << std::endl;
                    args.bitrate = DEFAULT_BITRATE;
                }
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

    // 解析命令行参数
    CommandLineArgs args;
    parse_arguments(argc, argv, args);
    if (args.show_help) {
        print_usage(argv[0]);
        return 0;
    }
    if (args.show_version) {
        return 0;
    }
    
    // 创建并启动服务
    OHScrcpyServer server;
    bool isUserCfg = (argc > 1);
    if (!server.start(args, isUserCfg)) {
        std::cerr << "Start OHScrcpy server fail" << std::endl;
        return 1;
    }
    
    std::cout << "OHScrcpy server exit" << std::endl;
    return 0;
}