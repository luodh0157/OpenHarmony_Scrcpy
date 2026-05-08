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

#include "../include/capture_wrapper.h"
#include "../include/error_codes.h"
#include "../include/logger.h"

namespace OHScrcpy {

CaptureWrapper::CaptureWrapper()
    : capture_(nullptr)
    , is_created_(false)
    , is_capturing_(false) {
}

CaptureWrapper::~CaptureWrapper() {
    Destroy();
}

ErrorCode CaptureWrapper::Create() {
    if (is_created_) {
        LOG_INFO("Server", "ScreenCapturer has been initialized");
        return ErrorCode::SUCCESS;
    }
    
    LOG_INFO("Server", "Initializing ScreenCapturer...");
    
    capture_ = OH_AVScreenCapture_Create();
    if (capture_ == nullptr) {
        LOG_ERROR("Server", "OH_AVScreenCapture_Create fail");
        return ErrorCode::CAPTURE_CREATE_FAILED;
    }
    
    is_created_ = true;
    return ErrorCode::SUCCESS;
}

ErrorCode CaptureWrapper::Init(const CaptureConfig& config) {
    if (!is_created_) {
        LOG_ERROR("Server", "ScreenCapturer has not been created");
        return ErrorCode::CAPTURE_CREATE_FAILED;
    }
    
    config_ = config;
    
    OH_VideoCaptureInfo videoCapInfo = {
        .videoFrameWidth = config.width,
        .videoFrameHeight = config.height,
        .videoSource = OH_VIDEO_SOURCE_SURFACE_RGBA
    };
    
    OH_VideoEncInfo videoEncInfo = {
        .videoCodec = OH_H264,
        .videoBitrate = 1500000,
        .videoFrameRate = config.fps
    };
    
    OH_VideoInfo videoInfo = {
        .videoCapInfo = videoCapInfo,
        .videoEncInfo = videoEncInfo
    };
    
    OH_AVScreenCaptureConfig screenConfig = {
        .captureMode = OH_CAPTURE_HOME_SCREEN,
        .dataType = OH_ORIGINAL_STREAM,
        .videoInfo = videoInfo
    };
    
    int32_t ret = OH_AVScreenCapture_Init(capture_, screenConfig);
    if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
        LOG_ERROR("Server", "OH_AVScreenCapture_Init fail, err: " + std::to_string(ret));
        return ErrorCode::CAPTURE_INIT_FAILED;
    }
    
    OH_AVScreenCapture_SetMicrophoneEnabled(capture_, false);
    
    ret = OH_AVScreenCapture_SetErrorCallback(capture_, &CaptureWrapper::OnError, this);
    if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
        LOG_ERROR("Server", "OH_AVScreenCapture_SetErrorCallback fail, err: " + std::to_string(ret));
        return ErrorCode::CAPTURE_SET_CALLBACK_FAILED;
    }
    
    ret = OH_AVScreenCapture_SetStateCallback(capture_, &CaptureWrapper::OnStateChange, this);
    if (ret != AV_SCREEN_CAPTURE_ERR_OK) {
        LOG_ERROR("Server", "OH_AVScreenCapture_SetStateCallback fail, err: " + std::to_string(ret));
        return ErrorCode::CAPTURE_SET_CALLBACK_FAILED;
    }
    
    LOG_INFO("Server", "Screen capturer initialized: " + std::to_string(config.width) + "x" + std::to_string(config.height));
    return ErrorCode::SUCCESS;
}

ErrorCode CaptureWrapper::StartWithSurface(OHNativeWindow* surface) {
    if (!is_created_ || capture_ == nullptr) {
        LOG_ERROR("Server", "ScreenCapturer has not been initialized");
        return ErrorCode::CAPTURE_CREATE_FAILED;
    }
    
    if (surface == nullptr) {
        LOG_ERROR("Server", "Surface is null");
        return ErrorCode::GENERAL_INVALID_PARAMETER;
    }
    
    int32_t ret = OH_AVScreenCapture_StartScreenCaptureWithSurface(capture_, surface);
    if (ret != 0) {
        LOG_ERROR("Server", "OH_AVScreenCapture_StartScreenCaptureWithSurface fail, err: " + std::to_string(ret));
        return ErrorCode::CAPTURE_START_FAILED;
    }
    
    is_capturing_ = true;
    LOG_INFO("Server", "Screen capture started");
    return ErrorCode::SUCCESS;
}

ErrorCode CaptureWrapper::Stop() {
    if (capture_ && is_capturing_) {
        OH_AVScreenCapture_StopScreenCapture(capture_);
        is_capturing_ = false;
        LOG_INFO("Server", "Screen capture stopped");
    }
    return ErrorCode::SUCCESS;
}

ErrorCode CaptureWrapper::Destroy() {
    if (capture_) {
        if (is_capturing_) {
            Stop();
        }
        OH_AVScreenCapture_Release(capture_);
        capture_ = nullptr;
        LOG_INFO("Server", "Screen capture released");
    }
    
    is_created_ = false;
    return ErrorCode::SUCCESS;
}

void CaptureWrapper::SetMicrophoneEnabled(bool enabled) {
    if (capture_) {
        OH_AVScreenCapture_SetMicrophoneEnabled(capture_, enabled);
    }
}

void CaptureWrapper::SetErrorCallback(ErrorCallback callback) {
    error_callback_ = callback;
}

void CaptureWrapper::SetStateCallback(StateCallback callback) {
    state_callback_ = callback;
}

bool CaptureWrapper::IsReady() const {
    return is_created_ && capture_ != nullptr;
}

bool CaptureWrapper::IsCapturing() const {
    return is_capturing_;
}

void CaptureWrapper::OnError(OH_AVScreenCapture* capture, int32_t errorCode, void* userData) {
    CaptureWrapper* self = static_cast<CaptureWrapper*>(userData);
    if (self) {
        self->HandleError(errorCode);
    }
}

void CaptureWrapper::OnStateChange(OH_AVScreenCapture* capture, OH_AVScreenCaptureStateCode stateCode, void* userData) {
    CaptureWrapper* self = static_cast<CaptureWrapper*>(userData);
    if (self) {
        self->HandleStateChange(stateCode);
    }
}

void CaptureWrapper::HandleError(int32_t errorCode) {
    LOG_ERROR("Server", "Screen capture error: " + std::to_string(errorCode));
    if (error_callback_) {
        error_callback_(errorCode);
    }
}

void CaptureWrapper::HandleStateChange(OH_AVScreenCaptureStateCode stateCode) {
    switch (stateCode) {
        case OH_SCREEN_CAPTURE_STATE_STARTED:
            LOG_INFO("Server", "Screen capture state: STARTED");
            break;
        case OH_SCREEN_CAPTURE_STATE_STOPPED_BY_CALL:
            LOG_INFO("Server", "Screen capture state: STOPPED_BY_CALL");
            break;
        case OH_SCREEN_CAPTURE_STATE_CANCELED:
            LOG_INFO("Server", "Screen capture state: CANCELED");
            break;
        default:
            LOG_INFO("Server", "Screen capture state code: " + std::to_string(static_cast<int32_t>(stateCode)));
            break;
    }
    
    if (state_callback_) {
        state_callback_(static_cast<int32_t>(stateCode));
    }
}

} // namespace OHScrcpy