import dotenv from "dotenv";
dotenv.config();

import axios from "axios";
const FASTAPI_URL = process.env.FASTAPI_URL;

export const getSessions  = async (req,res) => {
    try{
        console.log(`📋 Fetching sessions for user: ${req.user.id}`);
        const response = await axios.get(`${FASTAPI_URL}/chats/sessions`, {
            params: { user_id: req.user.id }
        });
        console.log(`✅ Found ${response.data?.length || 0} sessions`);
        res.json(response.data);
    }catch (err){
        console.error('❌ Error fetching sessions:', err.response?.data || err.message);
        res.status(err.response?.status || 500).json({
        error : 'Failed to fetch sessions',
        detail: err.response?.data?.detail || err.message});
    }
}

export const getChat = async (req,res) =>{
    try{
        const id = req.params.id;
        console.log(`📖 Fetching chat session: ${id} for user: ${req.user.id}`);
        const response = await axios.get(`${FASTAPI_URL}/chats/sessions/${id}`, {
            params: { user_id: req.user.id }
        });
        console.log(`✅ Retrieved session: ${id}`);
        res.json(response.data);
    }catch(err){
        console.error('❌ Error fetching chat:', err.response?.data || err.message);
        res.status(err.response?.status || 500).json({
            error:"Failed to fetch chats",
            detail: err.response?.data?.detail || err.message
        });
    }
}

export const resumeChat = async (req,res)=>{
    try{
        const id = req.params.id;
        console.log(`💬 Resume chat request - session: ${id}, user: ${req.user.id}, video: ${req.body.video_id}`);
        const response = await axios.post(`${FASTAPI_URL}/chats/sessions/${id}`, {
            ...req.body,
            user_id: req.user.id
        });
        console.log(`✅ Chat resumed successfully for session: ${id}`);
        res.json(response.data);
    }catch(err){
        console.error('❌ Error resuming chat:', err.response?.data || err.message);
        res.status(err.response?.status || 500).json({
            error:'Failed to resume the chat',
            detail: err.response?.data?.detail || err.message
        });
    }
}

export const newChat = async (req, res) => {
  try {
    console.log(`💬 New chat request for user: ${req.user.id}, video: ${req.body.video_id}`);
    const response = await axios.post(`${FASTAPI_URL}/chats/sessions`, {
      ...req.body,
      user_id: req.user.id
    });
    console.log(`✅ New chat created with session_id: ${response.data?.session_id}`);
    res.json(response.data);
  } catch (err) {
    console.error('❌ Error starting new chat:', err.response?.data || err.message);
    res.status(err.response?.status || 500).json({ 
      error: 'Failed to start new chat', 
      detail: err.response?.data?.detail || err.message 
    });
  }
};

export const deleteChat = async (req, res) => {
  try {
    const id = req.params.id;
    const response = await axios.delete(`${FASTAPI_URL}/chats/sessions/${id}`, {
      params: { user_id: req.user.id }
    });
    res.json(response.data);
  } catch (err) {
    console.error('Error deleting chat:', err.message);
    res.status(500).json({ error: 'Failed to delete chat', details: err.message });
  }
};
