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
#include <iostream>
#include <fstream>
#include <mutex>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <functional>

namespace OHScrcpy {

/**
 * Log level definitions
 */
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
    
    static Logger& Instance() {
        static Logger instance;
        return instance;
    }
    
    void SetLevel(LogLevel level) {
        std::lock_guard<std::mutex> lock(mutex_);
        level_ = level;
    }
    
    LogLevel GetLevel() const {
        return level_;
    }
    
    void SetLogFile(const std::string& filepath) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (file_.is_open()) {
            file_.close();
        }
        file_.open(filepath, std::ios::out | std::ios::app);
        if (file_.is_open()) {
            file_enabled_ = true;
        }
    }
    
    void EnableFile(bool enable) {
        std::lock_guard<std::mutex> lock(mutex_);
        file_enabled_ = enable;
    }
    
    void EnableConsole(bool enable) {
        std::lock_guard<std::mutex> lock(mutex_);
        console_enabled_ = enable;
    }
    
    void SetSendLogCallback(SendLogCallback callback) {
        std::lock_guard<std::mutex> lock(mutex_);
        send_log_callback_ = callback;
    }
    
    void EnableSendToClient(bool enable) {
        std::lock_guard<std::mutex> lock(mutex_);
        send_to_client_enabled_ = enable;
    }
    
    void Log(LogLevel level, const std::string& tag, const std::string& message) {
        if (level < level_) {
            return;
        }
        
        std::lock_guard<std::mutex> lock(mutex_);
        
        // Console output (simplified format, no date)
        if (console_enabled_) {
            std::string levelStr = GetLevelString(level);
            std::string consoleOutput = "[" + levelStr + "][" + tag + "] " + message;
            if (level >= LogLevel::ERROR) {
                std::cerr << consoleOutput << std::endl;
            } else {
                std::cout << consoleOutput << std::endl;
            }
        }
        
        // Full format for file and client
        std::string timestamp = GetTimestamp();
        std::string levelStr = GetLevelString(level);
        std::string fullOutput = "[" + timestamp + "][" + levelStr + "][" + tag + "] " + message;
        
        // File output (full format)
        if (file_enabled_ && file_.is_open()) {
            file_ << fullOutput << std::endl;
            file_.flush();
        }
        
        // Send to client
        if (send_to_client_enabled_ && send_log_callback_) {
            send_log_callback_(fullOutput);
        }
    }
    
    void Debug(const std::string& tag, const std::string& message) {
        Log(LogLevel::DEBUG, tag, message);
    }
    
    void Info(const std::string& tag, const std::string& message) {
        Log(LogLevel::INFO, tag, message);
    }
    
    void Warn(const std::string& tag, const std::string& message) {
        Log(LogLevel::WARN, tag, message);
    }
    
    void Error(const std::string& tag, const std::string& message) {
        Log(LogLevel::ERROR, tag, message);
    }
    
    void Fatal(const std::string& tag, const std::string& message) {
        Log(LogLevel::FATAL, tag, message);
    }

private:
    Logger() : level_(LogLevel::INFO), console_enabled_(true), file_enabled_(false),
               send_to_client_enabled_(false), send_log_callback_(nullptr) {}
    ~Logger() {
        if (file_.is_open()) {
            file_.close();
        }
    }
    
    Logger(const Logger&) = delete;
    Logger& operator=(const Logger&) = delete;
    
    std::string GetTimestamp() {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()) % 1000;
        
        std::stringstream ss;
        ss << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S");
        ss << '.' << std::setfill('0') << std::setw(3) << ms.count();
        return ss.str();
    }
    
    std::string GetLevelString(LogLevel level) {
        switch (level) {
            case LogLevel::DEBUG: return "DEBUG";
            case LogLevel::INFO:  return "INFO";
            case LogLevel::WARN:  return "WARN";
            case LogLevel::ERROR: return "ERROR";
            case LogLevel::FATAL: return "FATAL";
            default: return "UNKNOWN";
        }
    }
    
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