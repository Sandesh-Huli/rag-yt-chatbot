/**
 * Structured logging configuration (Issue 40) and Audit logging (Issue 34).
 * 
 * Features:
 * - JSON structured logging format
 * - Configurable log levels via environment variables
 * - Audit logging for security events
 * - Request/response middleware logging
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Log levels matching Python logging module
const LOG_LEVELS = {
    DEBUG: 10,
    INFO: 20,
    WARNING: 30,
    ERROR: 40,
    CRITICAL: 50,
};

const LEVEL_NAMES = {
    10: 'DEBUG',
    20: 'INFO',
    30: 'WARNING',
    40: 'ERROR',
    50: 'CRITICAL',
};

/**
 * Get current log level from environment (default: INFO)
 */
function getLogLevel() {
    const logLevelStr = (process.env.LOG_LEVEL || 'INFO').toUpperCase();
    return LOG_LEVELS[logLevelStr] || LOG_LEVELS.INFO;
}

/**
 * Format timestamp in ISO format
 */
function formatTimestamp() {
    return new Date().toISOString();
}

/**
 * Structured logger for JSON output (Issue 40)
 */
class StructuredLogger {
    constructor(loggerName = 'yt-chatbot') {
        this.name = loggerName;
        this.logLevel = getLogLevel();
        this.auditLogFile = process.env.AUDIT_LOG_FILE || null;
        
        // Ensure audit log directory exists
        if (this.auditLogFile) {
            const logDir = path.dirname(this.auditLogFile);
            if (!fs.existsSync(logDir)) {
                fs.mkdirSync(logDir, { recursive: true });
            }
        }
    }

    /**
     * Format and output log message (Issue 40)
     */
    _log(level, message, extraData = {}) {
        if (level < this.logLevel) return;

        const logEntry = {
            timestamp: formatTimestamp(),
            level: LEVEL_NAMES[level] || 'INFO',
            logger: this.name,
            message,
            ...extraData,
        };

        const logOutput = JSON.stringify(logEntry);
        
        // Output based on log format preference
        const logFormat = (process.env.LOG_FORMAT || 'json').toLowerCase();
        
        if (logFormat === 'json') {
            console.log(logOutput);
        } else {
            // Text format fallback
            console.log(
                `[${logEntry.timestamp}] [${logEntry.level}] ${message}`
            );
        }

        // Write to audit log file if configured and level permits
        if (this.auditLogFile && level >= LOG_LEVELS.INFO) {
            this._writeToAuditLog(logOutput);
        }
    }

    /**
     * Write log to file
     */
    _writeToAuditLog(logOutput) {
        try {
            fs.appendFileSync(this.auditLogFile, logOutput + '\n');
        } catch (error) {
            console.error('Failed to write audit log:', error.message);
        }
    }

    debug(message, extraData = {}) {
        this._log(LOG_LEVELS.DEBUG, message, extraData);
    }

    info(message, extraData = {}) {
        this._log(LOG_LEVELS.INFO, message, extraData);
    }

    warning(message, extraData = {}) {
        this._log(LOG_LEVELS.WARNING, message, extraData);
    }

    error(message, extraData = {}) {
        this._log(LOG_LEVELS.ERROR, message, extraData);
    }

    critical(message, extraData = {}) {
        this._log(LOG_LEVELS.CRITICAL, message, extraData);
    }
}

/**
 * Audit logger for security events (Issue 34)
 */
class AuditLogger {
    constructor(loggerName = 'audit') {
        this.logger = new StructuredLogger(loggerName);
    }

    /**
     * Log authentication attempt (Issue 34)
     */
    logAuthAttempt({
        email,
        action = 'login', // 'login', 'register', 'logout'
        success,
        ipAddress = null,
        userAgent = null,
        error = null,
    }) {
        const auditData = {
            event_type: 'auth_attempt',
            action,
            email,
            success,
            ip_address: ipAddress,
            user_agent: userAgent,
            timestamp: formatTimestamp(),
        };

        if (error) {
            auditData.error = error;
        }

        this.logger.info(
            `Auth ${action}: ${email} - ${success ? 'success' : 'failed'}`,
            auditData
        );
    }

    /**
     * Log resource access (Issue 34)
     */
    logResourceAccess({
        userId = null,
        resource,
        action = 'read', // 'read', 'write', 'delete'
        success,
        ipAddress = null,
        error = null,
    }) {
        const auditData = {
            event_type: 'resource_access',
            user_id: userId,
            resource,
            action,
            success,
            ip_address: ipAddress,
            timestamp: formatTimestamp(),
        };

        if (error) {
            auditData.error = error;
        }

        this.logger.info(
            `Access ${resource}: ${action} - ${success ? 'success' : 'failed'}`,
            auditData
        );
    }

    /**
     * Log security event (Issue 34)
     */
    logSecurityEvent({
        eventType,
        severity = 'medium', // 'low', 'medium', 'high', 'critical'
        userId = null,
        ipAddress = null,
        description = null,
        additionalData = {},
    }) {
        const severityLevelMap = {
            'low': LOG_LEVELS.INFO,
            'medium': LOG_LEVELS.WARNING,
            'high': LOG_LEVELS.ERROR,
            'critical': LOG_LEVELS.CRITICAL,
        };

        const auditData = {
            event_type: 'security_event',
            security_event_type: eventType,
            severity,
            user_id: userId,
            ip_address: ipAddress,
            description,
            timestamp: formatTimestamp(),
            ...additionalData,
        };

        const level = severityLevelMap[severity] || LOG_LEVELS.INFO;
        const levelName = LEVEL_NAMES[level] || 'INFO';

        // Log using appropriate level
        this.logger._log(
            level,
            `Security event [${severity.toUpperCase()}]: ${eventType}`,
            auditData
        );
    }
}

/**
 * Express middleware for request/response logging (Issue 40)
 */
export function requestLoggingMiddleware(app) {
    const logger = new StructuredLogger('express');

    app.use((req, res, next) => {
        const startTime = Date.now();
        const originalSend = res.send;

        // Override send to log response
        res.send = function(data) {
            const duration = Date.now() - startTime;
            
            logger.info(`${req.method} ${req.path}`, {
                event_type: 'http_request',
                method: req.method,
                path: req.path,
                status: res.statusCode,
                duration_ms: duration,
                ip_address: req.ip,
                user_agent: req.get('user-agent'),
            });

            originalSend.call(this, data);
        };

        next();
    });
}

/**
 * Express middleware for error logging (Issue 40)
 */
export function errorLoggingMiddleware(app) {
    const logger = new StructuredLogger('express.error');

    app.use((error, req, res, next) => {
        logger.error(`Error in ${req.method} ${req.path}`, {
            event_type: 'http_error',
            method: req.method,
            path: req.path,
            status: error.status || 500,
            error_message: error.message,
            error_type: error.name,
            ip_address: req.ip,
            stack: error.stack,
        });

        res.status(error.status || 500).json({
            success: false,
            message: error.message,
        });
    });
}

// Export singletons
export const logger = new StructuredLogger('yt-chatbot');
export const auditLogger = new AuditLogger('audit');

export { StructuredLogger, AuditLogger, LOG_LEVELS };
