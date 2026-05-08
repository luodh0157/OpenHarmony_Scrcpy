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

#include "codec_wrapper.h"
#include "error_codes.h"
#include "logger.h"

#include <cstring>

const std::string LOG_TAG = "Codec";

namespace OHScrcpy {

CodecWrapper::CodecWrapper()
    : encoder_(nullptr)
    , surface_(nullptr)
    , is_created_(false)
    , is_started_(false) {
}

CodecWrapper::~CodecWrapper() {
    Destroy();
}

ErrorCode CodecWrapper::Create(const CodecConfig& config) {
    if (is_created_) {
        LOG_INFO(LOG_TAG, "CodecWrapper already created");
        return ErrorCode::SUCCESS;
    }
    
    config_ = config;
    
    const char* mimeType = nullptr;
    if (config.codec == "h265") {
        mimeType = OH_AVCODEC_MIMETYPE_VIDEO_HEVC;
    } else {
        mimeType = OH_AVCODEC_MIMETYPE_VIDEO_AVC;
    }
    
    encoder_ = OH_VideoEncoder_CreateByMime(mimeType);
    if (encoder_ == nullptr) {
        LOG_ERROR(LOG_TAG, "OH_VideoEncoder_CreateByMime fail for codec: " + config.codec);
        return ErrorCode::ENCODER_CREATE_FAILED;
    }
    
    OH_AVCodecCallback callback = {
        .onError = &CodecWrapper::OnError,
        .onStreamChanged = &CodecWrapper::OnStreamChanged,
        .onNeedInputBuffer = &CodecWrapper::OnNeedInputBuffer,
        .onNewOutputBuffer = &CodecWrapper::OnNewOutputBuffer,
    };
    
    int32_t ret = OH_VideoEncoder_RegisterCallback(encoder_, callback, this);
    if (ret != 0) {
        LOG_ERROR(LOG_TAG, "OH_VideoEncoder_RegisterCallback fail, err: " + std::to_string(ret));
        OH_VideoEncoder_Destroy(encoder_);
        encoder_ = nullptr;
        return ErrorCode::ENCODER_REGISTER_CALLBACK_FAILED;
    }
    
    OH_AVFormat* format = OH_AVFormat_Create();
    if (format == nullptr) {
        LOG_ERROR(LOG_TAG, "OH_AVFormat_Create fail");
        OH_VideoEncoder_Destroy(encoder_);
        encoder_ = nullptr;
        return ErrorCode::ENCODER_CONFIGURE_FAILED;
    }
    
    OH_AVFormat_SetIntValue(format, OH_MD_KEY_WIDTH, config.width);
    OH_AVFormat_SetIntValue(format, OH_MD_KEY_HEIGHT, config.height);
    OH_AVFormat_SetDoubleValue(format, OH_MD_KEY_FRAME_RATE, config.fps);
    OH_AVFormat_SetLongValue(format, OH_MD_KEY_BITRATE, config.bitrate);
    OH_AVFormat_SetIntValue(format, OH_MD_KEY_PIXEL_FORMAT, AV_PIXEL_FORMAT_RGBA);
    OH_AVFormat_SetIntValue(format, OH_MD_KEY_VIDEO_ENCODE_BITRATE_MODE, OH_BitrateMode::BITRATE_MODE_VBR);
    
    if (config.codec == "h265") {
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_PROFILE, OH_HEVCProfile::HEVC_PROFILE_MAIN);
    } else {
        OH_AVFormat_SetIntValue(format, OH_MD_KEY_PROFILE, OH_AVCProfile::AVC_PROFILE_MAIN);
    }
    
    OH_AVFormat_SetIntValue(format, OH_MD_KEY_I_FRAME_INTERVAL, 500);
    
    ret = OH_VideoEncoder_Configure(encoder_, format);
    if (ret != 0) {
        LOG_ERROR(LOG_TAG, "OH_VideoEncoder_Configure fail, err: " + std::to_string(ret));
        OH_AVFormat_Destroy(format);
        OH_VideoEncoder_Destroy(encoder_);
        encoder_ = nullptr;
        return ErrorCode::ENCODER_CONFIGURE_FAILED;
    }
    
    OH_AVFormat_Destroy(format);
    
    ret = OH_VideoEncoder_GetSurface(encoder_, &surface_);
    if (ret != 0) {
        LOG_ERROR(LOG_TAG, "OH_VideoEncoder_GetSurface fail, err: " + std::to_string(ret));
        OH_VideoEncoder_Destroy(encoder_);
        encoder_ = nullptr;
        return ErrorCode::ENCODER_GET_SURFACE_FAILED;
    }
    
    ret = OH_VideoEncoder_Prepare(encoder_);
    if (ret != 0) {
        LOG_ERROR(LOG_TAG, "OH_VideoEncoder_Prepare fail, err: " + std::to_string(ret));
        OH_VideoEncoder_Destroy(encoder_);
        encoder_ = nullptr;
        return ErrorCode::ENCODER_PREPARE_FAILED;
    }
    
    is_created_ = true;
    LOG_INFO(LOG_TAG, "VideoEncoder initialized successfully for codec: " + config.codec);
    return ErrorCode::SUCCESS;
}

ErrorCode CodecWrapper::Start() {
    if (!is_created_) {
        LOG_ERROR(LOG_TAG, "VideoEncoder has not been initialized");
        return ErrorCode::ENCODER_CREATE_FAILED;
    }
    
    if (is_started_) {
        return ErrorCode::SUCCESS;
    }
    
    int32_t ret = OH_VideoEncoder_Start(encoder_);
    if (ret != 0) {
        LOG_ERROR(LOG_TAG, "OH_VideoEncoder_Start fail, err: " + std::to_string(ret));
        return ErrorCode::ENCODER_START_FAILED;
    }
    
    is_started_ = true;
    LOG_INFO(LOG_TAG, "VideoEncoder started");
    return ErrorCode::SUCCESS;
}

ErrorCode CodecWrapper::Stop() {
    if (!is_started_) {
        return ErrorCode::SUCCESS;
    }
    
    OH_VideoEncoder_NotifyEndOfStream(encoder_);
    int32_t ret = OH_VideoEncoder_Stop(encoder_);
    if (ret != 0) {
        LOG_ERROR(LOG_TAG, "OH_VideoEncoder_Stop fail, err: " + std::to_string(ret));
        return ErrorCode::ENCODER_STOP_FAILED;
    }
    
    is_started_ = false;
    LOG_INFO(LOG_TAG, "VideoEncoder stopped");
    return ErrorCode::SUCCESS;
}

ErrorCode CodecWrapper::Destroy() {
    if (encoder_) {
        if (is_started_) {
            Stop();
        }
        OH_VideoEncoder_Destroy(encoder_);
        encoder_ = nullptr;
        surface_ = nullptr;
        LOG_INFO(LOG_TAG, "VideoEncoder destroyed");
    }
    
    is_created_ = false;
    return ErrorCode::SUCCESS;
}

OHNativeWindow* CodecWrapper::GetSurface() {
    return surface_;
}

bool CodecWrapper::IsReady() const {
    return is_created_ && encoder_ != nullptr;
}

void CodecWrapper::SetOutputCallback(OnOutputCallback callback) {
    output_callback_ = callback;
}

void CodecWrapper::OnError(OH_AVCodec* codec, int32_t errorCode, void* userData) {
    CodecWrapper* self = static_cast<CodecWrapper*>(userData);
    if (self) {
        self->HandleError(errorCode);
    }
}

void CodecWrapper::OnStreamChanged(OH_AVCodec* codec, OH_AVFormat* format, void* userData) {
    CodecWrapper* self = static_cast<CodecWrapper*>(userData);
    if (self && format) {
        self->HandleStreamChanged(format);
    }
}

void CodecWrapper::OnNeedInputBuffer(OH_AVCodec* codec, uint32_t index, OH_AVBuffer* buffer, void* userData) {
}

void CodecWrapper::OnNewOutputBuffer(OH_AVCodec* codec, uint32_t index, OH_AVBuffer* buffer, void* userData) {
    CodecWrapper* self = static_cast<CodecWrapper*>(userData);
    if (self) {
        self->HandleOutputBuffer(index, buffer);
        OH_VideoEncoder_FreeOutputBuffer(codec, index);
    }
}

void CodecWrapper::HandleError(int32_t errorCode) {
    LOG_ERROR(LOG_TAG, "VideoEncoder error: " + std::to_string(errorCode));
}

void CodecWrapper::HandleStreamChanged(OH_AVFormat* format) {
    int32_t width = 0, height = 0;
    OH_AVFormat_GetIntValue(format, OH_MD_KEY_WIDTH, &width);
    OH_AVFormat_GetIntValue(format, OH_MD_KEY_HEIGHT, &height);
    LOG_INFO(LOG_TAG, "VideoEncoder stream changed: " + std::to_string(width) + "x" + std::to_string(height));
}

void CodecWrapper::HandleOutputBuffer(uint32_t index, OH_AVBuffer* buffer) {
    if (!buffer || !output_callback_) {
        return;
    }
    
    OH_AVCodecBufferAttr info;
    int32_t ret = OH_AVBuffer_GetBufferAttr(buffer, &info);
    if (ret != 0) {
        LOG_ERROR(LOG_TAG, "OH_AVBuffer_GetBufferAttr fail, err: " + std::to_string(ret));
        return;
    }
    
    if (info.flags & AVCODEC_BUFFER_FLAGS_EOS) {
        LOG_INFO(LOG_TAG, "End-of-Stream frame");
        return;
    }
    
    uint8_t* addr = OH_AVBuffer_GetAddr(buffer);
    if (addr == nullptr) {
        LOG_ERROR(LOG_TAG, "OH_AVBuffer_GetAddr fail");
        return;
    }
    
    bool isKeyframe = (info.flags & AVCODEC_BUFFER_FLAGS_SYNC_FRAME) != 0;
    
    if (info.size > 0) {
        ParseParameterSets(addr, info.size);
        output_callback_(addr, info.size, isKeyframe);
    }
}

void CodecWrapper::ParseParameterSets(uint8_t* data, size_t size) {
    if (size < 4) return;
    
    size_t pos = 0;
    
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
            
            if (config_.codec == "h265") {
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
                
                if (nalu_type == 32) {
                    vps_data_.assign(data + pos, data + nalu_end);
                    LOG_INFO(LOG_TAG, "Found VPS: " + std::to_string(vps_data_.size()) + " bytes");
                } else if (nalu_type == 33) {
                    sps_data_.assign(data + pos, data + nalu_end);
                    LOG_INFO(LOG_TAG, "Found SPS: " + std::to_string(sps_data_.size()) + " bytes");
                } else if (nalu_type == 34) {
                    pps_data_.assign(data + pos, data + nalu_end);
                    LOG_INFO(LOG_TAG, "Found PPS: " + std::to_string(pps_data_.size()) + " bytes");
                }
                
                pos = nalu_end;
            } else {
                uint8_t nalu_type = data[nalu_start] & 0x1F;
                
                size_t next_start = nalu_start + 1;
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
                
                if (nalu_type == 7) {
                    sps_data_.assign(data + pos, data + nalu_end);
                    LOG_INFO(LOG_TAG, "Found SPS: " + std::to_string(sps_data_.size()) + " bytes");
                } else if (nalu_type == 8) {
                    pps_data_.assign(data + pos, data + nalu_end);
                    LOG_INFO(LOG_TAG, "Found PPS: " + std::to_string(pps_data_.size()) + " bytes");
                }
                
                pos = nalu_end;
            }
        } else {
            pos++;
        }
    }
}

} // namespace OHScrcpy