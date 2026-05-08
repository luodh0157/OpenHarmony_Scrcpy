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

#include "logger.h"

#include <iostream>
#include <fstream>
#include <mutex>
#include <chrono>
#include <iomanip>
#include <sstream>

namespace OHScrcpy {

Logger& Logger::Instance() {
    static Logger instance;
    return instance;
}

Logger::Logger() 
    : level_(LogLevel::INFO)
    , console_enabled_(true)
    , file_enabled_(false)
    , send_to_client_enabled_(false)
    , send_log_callback_(nullptr) {
}

Logger::~Logger() {
    if (file_.is_open()) {
        file_.close();
    }
}

void Logger::SetLevel(LogLevel level) {
    std::lock_guard<std::mutex> lock(mutex_);
    level_ = level;
}

LogLevel Logger::GetLevel() const {
    return level_;
}

void Logger::SetLogFile(const std::string& filepath) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (file_.is_open()) {
        file_.close();
    }
    file_.open(filepath, std::ios::out | std::ios::app);
    if (file_.is_open()) {
        file_enabled_ = true;
    }
}

void Logger::EnableFile(bool enable) {
    std::lock_guard<std::mutex> lock(mutex_);
    file_enabled_ = enable;
}

void Logger::EnableConsole(bool enable) {
    std::lock_guard<std::mutex> lock(mutex_);
    console_enabled_ = enable;
}

void Logger::SetSendLogCallback(SendLogCallback callback) {
    std::lock_guard<std::mutex> lock(mutex_);
    send_log_callback_ = callback;
}

void Logger::EnableSendToClient(bool enable) {
    std::lock_guard<std::mutex> lock(mutex_);
    send_to_client_enabled_ = enable;
}

void Logger::Log(LogLevel level, const std::string& tag, const std::string& message) {
    if (level < level_) {
        return;
    }
    
    std::lock_guard<std::mutex> lock(mutex_);
    
    if (console_enabled_) {
        std::string consoleOutput = GetFormatLogStr(level, tag, message, false);
        if (level >= LogLevel::ERROR) {
            std::cerr << consoleOutput << std::endl;
        } else {
            std::cout << consoleOutput << std::endl;
        }
    }
    
    std::string fullOutput;
    if (file_enabled_ && file_.is_open()) {
        fullOutput = GetFormatLogStr(level, tag, message, true);
        file_ << fullOutput << std::endl;
        file_.flush();
    }
    
    if (send_to_client_enabled_ && send_log_callback_) {
        if (fullOutput.empty()) {
            fullOutput = GetFormatLogStr(level, tag, message, true);
        }
        send_log_callback_(fullOutput);
    }
}

void Logger::Debug(const std::string& tag, const std::string& message) {
    Log(LogLevel::DEBUG, tag, message);
}

void Logger::Info(const std::string& tag, const std::string& message) {
    Log(LogLevel::INFO, tag, message);
}

void Logger::Warn(const std::string& tag, const std::string& message) {
    Log(LogLevel::WARN, tag, message);
}

void Logger::Error(const std::string& tag, const std::string& message) {
    Log(LogLevel::ERROR, tag, message);
}

void Logger::Fatal(const std::string& tag, const std::string& message) {
    Log(LogLevel::FATAL, tag, message);
}

std::string Logger::GetFormatLogStr(LogLevel level, const std::string& tag, 
                                    const std::string& message, bool need_time) {
    std::string outputStr;
    if (!need_time) {
        outputStr = "[" + GetLevelString(level) + "] " + message;
    } else {
        outputStr = "[" + GetTimestamp() + "][" + GetLevelString(level) + "][" + tag + "] " + message;
    }
    return outputStr;
}

std::string Logger::GetTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;
    
    std::stringstream ss;
    ss << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S");
    ss << '.' << std::setfill('0') << std::setw(3) << ms.count();
    return ss.str();
}

std::string Logger::GetLevelString(LogLevel level) {
    switch (level) {
        case LogLevel::DEBUG: return "DEBUG";
        case LogLevel::INFO:  return "INFO";
        case LogLevel::WARN:  return "WARN";
        case LogLevel::ERROR: return "ERROR";
        case LogLevel::FATAL: return "FATAL";
        default: return "UNKNOWN";
    }
}

} // namespace OHScrcpy