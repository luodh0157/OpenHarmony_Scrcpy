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

#ifndef OHSCRCPY_ERROR_CODES_H
#define OHSCRCPY_ERROR_CODES_H

#include <string>
#include <map>

namespace OHScrcpy {

enum class ErrorCode {
    SUCCESS = 0,
    
    NETWORK_ERRORS_START = 100,
    NETWORK_SOCKET_CREATE_FAILED = 101,
    NETWORK_SOCKET_BIND_FAILED = 102,
    NETWORK_SOCKET_LISTEN_FAILED = 103,
    NETWORK_CLIENT_ACCEPT_FAILED = 104,
    NETWORK_CONNECTION_LOST = 105,
    NETWORK_SEND_FAILED = 106,
    NETWORK_RECEIVE_FAILED = 107,
    NETWORK_PORT_IN_USE = 108,
    NETWORK_ERRORS_END = 109,
    
    CAPTURE_ERRORS_START = 200,
    CAPTURE_CREATE_FAILED = 201,
    CAPTURE_INIT_FAILED = 202,
    CAPTURE_START_FAILED = 203,
    CAPTURE_STOP_FAILED = 204,
    CAPTURE_RELEASE_FAILED = 205,
    CAPTURE_SET_CALLBACK_FAILED = 206,
    CAPTURE_ERRORS_END = 209,
    
    ENCODER_ERRORS_START = 300,
    ENCODER_CREATE_FAILED = 301,
    ENCODER_CONFIGURE_FAILED = 302,
    ENCODER_START_FAILED = 303,
    ENCODER_STOP_FAILED = 304,
    ENCODER_DESTROY_FAILED = 305,
    ENCODER_REGISTER_CALLBACK_FAILED = 306,
    ENCODER_GET_SURFACE_FAILED = 307,
    ENCODER_PREPARE_FAILED = 308,
    ENCODER_ERRORS_END = 309,
    
    GENERAL_ERRORS_START = 500,
    GENERAL_THREAD_CREATE_FAILED = 501,
    GENERAL_BUFFER_ALLOC_FAILED = 502,
    GENERAL_INVALID_PARAMETER = 503,
    GENERAL_UNKNOWN_ERROR = 504,
    GENERAL_ERRORS_END = 505
};

class ErrorCodes {
public:
    static std::string GetDescription(ErrorCode code) {
        static const std::map<ErrorCode, std::string> descriptions = {
            {ErrorCode::SUCCESS, "Success"},
            {ErrorCode::NETWORK_SOCKET_CREATE_FAILED, "Failed to create socket"},
            {ErrorCode::NETWORK_SOCKET_BIND_FAILED, "Failed to bind socket"},
            {ErrorCode::NETWORK_SOCKET_LISTEN_FAILED, "Failed to listen on socket"},
            {ErrorCode::NETWORK_CLIENT_ACCEPT_FAILED, "Failed to accept client connection"},
            {ErrorCode::NETWORK_CONNECTION_LOST, "Connection lost"},
            {ErrorCode::NETWORK_SEND_FAILED, "Failed to send data"},
            {ErrorCode::NETWORK_RECEIVE_FAILED, "Failed to receive data"},
            {ErrorCode::NETWORK_PORT_IN_USE, "Port is already in use"},
            {ErrorCode::CAPTURE_CREATE_FAILED, "Failed to create screen capture"},
            {ErrorCode::CAPTURE_INIT_FAILED, "Failed to init screen capture"},
            {ErrorCode::CAPTURE_START_FAILED, "Failed to start screen capture"},
            {ErrorCode::CAPTURE_STOP_FAILED, "Failed to stop screen capture"},
            {ErrorCode::CAPTURE_RELEASE_FAILED, "Failed to release screen capture"},
            {ErrorCode::CAPTURE_SET_CALLBACK_FAILED, "Failed to set callback"},
            {ErrorCode::ENCODER_CREATE_FAILED, "Failed to create encoder"},
            {ErrorCode::ENCODER_CONFIGURE_FAILED, "Failed to configure encoder"},
            {ErrorCode::ENCODER_START_FAILED, "Failed to start encoder"},
            {ErrorCode::ENCODER_STOP_FAILED, "Failed to stop encoder"},
            {ErrorCode::ENCODER_DESTROY_FAILED, "Failed to destroy encoder"},
            {ErrorCode::ENCODER_REGISTER_CALLBACK_FAILED, "Failed to register callback"},
            {ErrorCode::ENCODER_GET_SURFACE_FAILED, "Failed to get surface"},
            {ErrorCode::ENCODER_PREPARE_FAILED, "Failed to prepare encoder"},
            {ErrorCode::GENERAL_THREAD_CREATE_FAILED, "Failed to create thread"},
            {ErrorCode::GENERAL_BUFFER_ALLOC_FAILED, "Failed to allocate buffer"},
            {ErrorCode::GENERAL_INVALID_PARAMETER, "Invalid parameter"},
            {ErrorCode::GENERAL_UNKNOWN_ERROR, "Unknown error"}
        };
        auto it = descriptions.find(code);
        return it != descriptions.end() ? it->second : "Unknown error code";
    }
    
    static bool IsSuccess(ErrorCode code) {
        return code == ErrorCode::SUCCESS;
    }
};

} // namespace OHScrcpy

#endif // OHSCRCPY_ERROR_CODES_H