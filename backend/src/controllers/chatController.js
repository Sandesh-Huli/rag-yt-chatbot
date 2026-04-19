import dotenv from "dotenv";
dotenv.config();

import axios from "axios";
import { logger, auditLogger } from "../logging/structuredLogger.js";

const FASTAPI_URL = process.env.FASTAPI_URL;

export const getSessions = async (req, res) => {
    try {
        logger.info("Fetching chat sessions", {
            event_type: "get_sessions_start",
            user_id: req.user.id,
        });
        
        const response = await axios.request({
            method: 'GET',
            url: `${FASTAPI_URL}/chats/sessions`,
            params: { user_id: req.user.id },
            headers: {
                'Authorization': `Bearer ${req.headers.authorization?.split(' ')[1] || ''}`,
            }
        });
        
        logger.info("Chat sessions retrieved successfully", {
            event_type: "get_sessions_success",
            user_id: req.user.id,
            session_count: response.data?.length || 0,
        });
        
        res.json(response.data);
    } catch (err) {
        logger.error("Failed to fetch chat sessions", {
            event_type: "get_sessions_error",
            user_id: req.user.id,
            error: err.message,
            error_type: err.name,
            status: err.response?.status,
            fastapi_error: err.response?.data?.detail,
        });
        
        res.status(err.response?.status || 500).json({
            error: 'Failed to fetch sessions',
            detail: err.response?.data?.detail || err.message
        });
    }
}

export const getChat = async (req, res) => {
    try {
        const id = req.params.id;
        
        logger.info("Fetching chat session", {
            event_type: "get_chat_start",
            session_id: id,
            user_id: req.user.id,
        });
        
        const response = await axios.request({
            method: 'GET',
            url: `${FASTAPI_URL}/chats/sessions/${id}`,
            params: { user_id: req.user.id },
            headers: {
                'Authorization': `Bearer ${req.headers.authorization?.split(' ')[1] || ''}`,
            }
        });
        
        logger.info("Chat session retrieved successfully", {
            event_type: "get_chat_success",
            session_id: id,
            user_id: req.user.id,
        });
        
        res.json(response.data);
    } catch (err) {
        logger.error("Failed to fetch chat session", {
            event_type: "get_chat_error",
            session_id: req.params.id,
            user_id: req.user.id,
            error: err.message,
            status: err.response?.status,
            fastapi_error: err.response?.data?.detail,
        });
        
        res.status(err.response?.status || 500).json({
            error: "Failed to fetch chat",
            detail: err.response?.data?.detail || err.message
        });
    }
}

export const resumeChat = async (req, res) => {
    try {
        const id = req.params.id;
        
        logger.info("Resuming chat session", {
            event_type: "resume_chat_start",
            session_id: id,
            user_id: req.user.id,
            video_id: req.body.video_id,
            query: req.body.query?.substring(0, 100),
        });
        
        const response = await axios.request({
            method: 'POST',
            url: `${FASTAPI_URL}/chats/sessions/${id}`,
            data: {
                ...req.body,
                user_id: req.user.id
            },
            headers: {
                'Authorization': `Bearer ${req.headers.authorization?.split(' ')[1] || ''}`,
            }
        });
        
        logger.info("Chat session resumed successfully", {
            event_type: "resume_chat_success",
            session_id: id,
            user_id: req.user.id,
        });
        
        res.json(response.data);
    } catch (err) {
        logger.error("Failed to resume chat session", {
            event_type: "resume_chat_error",
            session_id: req.params.id,
            user_id: req.user.id,
            error: err.message,
            status: err.response?.status,
            fastapi_error: err.response?.data?.detail,
        });
        
        res.status(err.response?.status || 500).json({
            error: 'Failed to resume the chat',
            detail: err.response?.data?.detail || err.message
        });
    }
}

export const newChat = async (req, res) => {
  try {
    logger.info("Creating new chat session", {
        event_type: "new_chat_start",
        user_id: req.user.id,
        video_id: req.body.video_id,
        language: req.body.lang,
    });
    
    const response = await axios.request({
        method: 'POST',
        url: `${FASTAPI_URL}/chats/sessions`,
        data: {
            ...req.body,
            user_id: req.user.id
        },
        headers: {
            'Authorization': `Bearer ${req.headers.authorization?.split(' ')[1] || ''}`,
        }
    });
    
    logger.info("New chat session created successfully", {
        event_type: "new_chat_success",
        session_id: response.data?.session_id,
        user_id: req.user.id,
        video_id: req.body.video_id,
    });
    
    res.json(response.data);
  } catch (err) {
    logger.error("Failed to create new chat", {
        event_type: "new_chat_error",
        user_id: req.user.id,
        video_id: req.body.video_id,
        error: err.message,
        status: err.response?.status,
        fastapi_error: err.response?.data?.detail,
    });
    
    res.status(err.response?.status || 500).json({ 
      error: 'Failed to start new chat', 
      detail: err.response?.data?.detail || err.message 
    });
  }
};

export const deleteChat = async (req, res) => {
  try {
    const id = req.params.id;
    
    logger.info("Deleting chat session", {
        event_type: "delete_chat_start",
        session_id: id,
        user_id: req.user.id,
    });
    
    const response = await axios.request({
        method: 'DELETE',
        url: `${FASTAPI_URL}/chats/sessions/${id}`,
        params: { user_id: req.user.id },
        headers: {
            'Authorization': `Bearer ${req.headers.authorization?.split(' ')[1] || ''}`,
        }
    });
    
    logger.info("Chat session deleted successfully", {
        event_type: "delete_chat_success",
        session_id: id,
        user_id: req.user.id,
    });
    
    res.json(response.data);
  } catch (err) {
    logger.error("Failed to delete chat session", {
        event_type: "delete_chat_error",
        session_id: req.params.id,
        user_id: req.user.id,
        error: err.message,
        status: err.response?.status,
    });
    
    res.status(err.response?.status || 500).json({ 
        error: 'Failed to delete chat', 
        detail: err.response?.data?.detail || err.message 
    });
  }
};
