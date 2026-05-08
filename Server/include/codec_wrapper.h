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

#ifndef OHSCRCPY_CODEC_WRAPPER_H
#define OHSCRCPY_CODEC_WRAPPER_H

#include "error_codes.h"
#include "logger.h"

#include <memory>
#include <string>
#include <functional>
#include <vector>

// OpenHarmony多媒体C-API头文件
#include <native_avcodec_videoencoder.h>
#include <native_avcodec_base.h>
#include <native_avformat.h>
#include <native_avbuffer.h>

namespace OHScrcpy {

struct CodecConfig {
    int width;
    int height;
    int fps;
    int bitrate;
    std::string codec;  // "h264" or "h265"
};

/**
 * RAII wrapper for OH_VideoEncoder
 * 
 * Based on real OpenHarmony API:
 * - OH_VideoEncoder_CreateByMime
 * - OH_VideoEncoder_RegisterCallback
 * - OH_VideoEncoder_Configure
 * - OH_VideoEncoder_GetSurface
 * - OH_VideoEncoder_Prepare
 * - OH_VideoEncoder_Start/Stop/Destroy
 */
class CodecWrapper {
public:
    using OnOutputCallback = std::function<void(uint8_t* data, size_t size, bool isKeyframe)>;
    
    CodecWrapper();
    ~CodecWrapper();
    
    ErrorCode Create(const CodecConfig& config);
    ErrorCode Start();
    ErrorCode Stop();
    ErrorCode Destroy();
    
    OHNativeWindow* GetSurface();
    bool IsReady() const;
    
    void SetOutputCallback(OnOutputCallback callback);
    
    const std::vector<uint8_t>& GetVPSData() const { return vps_data_; }
    const std::vector<uint8_t>& GetSPSData() const { return sps_data_; }
    const std::vector<uint8_t>& GetPPSData() const { return pps_data_; }
    
    const CodecConfig& GetConfig() const { return config_; }

private:
    static void OnError(OH_AVCodec* codec, int32_t errorCode, void* userData);
    static void OnStreamChanged(OH_AVCodec* codec, OH_AVFormat* format, void* userData);
    static void OnNeedInputBuffer(OH_AVCodec* codec, uint32_t index, OH_AVBuffer* buffer, void* userData);
    static void OnNewOutputBuffer(OH_AVCodec* codec, uint32_t index, OH_AVBuffer* buffer, void* userData);
    
    void HandleError(int32_t errorCode);
    void HandleStreamChanged(OH_AVFormat* format);
    void HandleOutputBuffer(uint32_t index, OH_AVBuffer* buffer);
    void ParseParameterSets(uint8_t* data, size_t size);
    
    OH_AVCodec* encoder_;
    OHNativeWindow* surface_;
    CodecConfig config_;
    
    std::vector<uint8_t> vps_data_;
    std::vector<uint8_t> sps_data_;
    std::vector<uint8_t> pps_data_;
    
    OnOutputCallback output_callback_;
    
    bool is_created_;
    bool is_started_;
};

} // namespace OHScrcpy

#endif // OHSCRCPY_CODEC_WRAPPER_H