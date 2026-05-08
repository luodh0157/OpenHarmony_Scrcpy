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

#ifndef OHSCRCPY_CAPTURE_WRAPPER_H
#define OHSCRCPY_CAPTURE_WRAPPER_H

#include "error_codes.h"
#include "logger.h"

#include <memory>
#include <string>
#include <functional>

// OpenHarmony屏幕捕获C-API头文件
#include <native_avscreen_capture.h>
#include <native_avscreen_capture_base.h>
#include <native_avscreen_capture_errors.h>
#include <native_avbuffer.h>

namespace OHScrcpy {

struct CaptureConfig {
    int width;
    int height;
    int fps;
    uint64_t displayId;
};

/**
 * RAII wrapper for OH_AVScreenCapture
 * 
 * Based on real OpenHarmony API:
 * - OH_AVScreenCapture_Create
 * - OH_AVScreenCapture_Init
 * - OH_AVScreenCapture_SetMicrophoneEnabled
 * - OH_AVScreenCapture_SetErrorCallback
 * - OH_AVScreenCapture_SetStateCallback
 * - OH_AVScreenCapture_SetDataCallback
 * - OH_AVScreenCapture_StartScreenCaptureWithSurface
 * - OH_AVScreenCapture_StopScreenCapture
 * - OH_AVScreenCapture_Release
 */
class CaptureWrapper {
public:
    using ErrorCallback = std::function<void(int32_t errorCode)>;
    using StateCallback = std::function<void(int32_t stateCode)>;
    
    CaptureWrapper();
    ~CaptureWrapper();
    
    ErrorCode Create();
    ErrorCode Init(const CaptureConfig& config);
    ErrorCode StartWithSurface(OHNativeWindow* surface);
    ErrorCode Stop();
    ErrorCode Destroy();
    
    void SetMicrophoneEnabled(bool enabled);
    void SetErrorCallback(ErrorCallback callback);
    void SetStateCallback(StateCallback callback);
    
    bool IsReady() const;
    bool IsCapturing() const;
    
    OH_AVScreenCapture* GetCapture() const { return capture_; }
    const CaptureConfig& GetConfig() const { return config_; }

private:
    static void OnError(OH_AVScreenCapture* capture, int32_t errorCode, void* userData);
    static void OnStateChange(OH_AVScreenCapture* capture, OH_AVScreenCaptureStateCode stateCode, void* userData);
    
    void HandleError(int32_t errorCode);
    void HandleStateChange(OH_AVScreenCaptureStateCode stateCode);
    
    OH_AVScreenCapture* capture_;
    CaptureConfig config_;
    
    ErrorCallback error_callback_;
    StateCallback state_callback_;
    
    bool is_created_;
    bool is_capturing_;
};

} // namespace OHScrcpy

#endif // OHSCRCPY_CAPTURE_WRAPPER_H