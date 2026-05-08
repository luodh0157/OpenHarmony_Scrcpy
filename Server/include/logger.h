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

#ifndef OHSCRCPY_LOGGER_H
#define OHSCRCPY_LOGGER_H

#include <string>
#include <functional>
#include <fstream>
#include <mutex>

namespace OHScrcpy {

enum class LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3,
    FATAL = 4
};

/**
 * Logger class for OHScrcpy Server
 * 
 * Features:
 * - Log level filtering
 * - Console output (simplified format)
 * - File output (full format with date)
 * - Send log to client via network
 * - Thread-safe
 * - Timestamp formatting
 */
class Logger {
public:
    using SendLogCallback = std::function<void(const std::string& logLine)>;
    
    static Logger& Instance();
    
    void SetLevel(LogLevel level);
    LogLevel GetLevel() const;
    
    void SetLogFile(const std::string& filepath);
    void EnableFile(bool enable);
    void EnableConsole(bool enable);
    
    void SetSendLogCallback(SendLogCallback callback);
    void EnableSendToClient(bool enable);
    
    void Log(LogLevel level, const std::string& tag, const std::string& message);
    
    void Debug(const std::string& tag, const std::string& message);
    void Info(const std::string& tag, const std::string& message);
    void Warn(const std::string& tag, const std::string& message);
    void Error(const std::string& tag, const std::string& message);
    void Fatal(const std::string& tag, const std::string& message);

private:
    Logger();
    ~Logger();
    
    Logger(const Logger&) = delete;
    Logger& operator=(const Logger&) = delete;

    std::string GetFormatLogStr(LogLevel level, const std::string& tag, 
                                const std::string& message, bool need_time);
    std::string GetTimestamp();
    std::string GetLevelString(LogLevel level);
    
    LogLevel level_;
    bool console_enabled_;
    bool file_enabled_;
    bool send_to_client_enabled_;
    SendLogCallback send_log_callback_;
    std::ofstream file_;
    std::mutex mutex_;
};

/**
 * Convenient macros for logging
 */
#define LOG_DEBUG(tag, msg) OHScrcpy::Logger::Instance().Debug(tag, msg)
#define LOG_INFO(tag, msg)  OHScrcpy::Logger::Instance().Info(tag, msg)
#define LOG_WARN(tag, msg)  OHScrcpy::Logger::Instance().Warn(tag, msg)
#define LOG_ERROR(tag, msg) OHScrcpy::Logger::Instance().Error(tag, msg)
#define LOG_FATAL(tag, msg) OHScrcpy::Logger::Instance().Fatal(tag, msg)

} // namespace OHScrcpy

#endif // OHSCRCPY_LOGGER_H