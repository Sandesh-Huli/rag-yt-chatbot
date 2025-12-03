import dotenv from "dotenv";
dotenv.config();

import axios from "axios";
const FASTAPI_URL = process.env.FASTAPI_URL;

export const getSessions  = async (req,res) => {
    try{
        const response = await axios.get(`${FASTAPI_URL}/chats/sessions`, {
            params: { user_id: req.user.id }
        });
        res.json(response.data);
    }catch (err){
        console.error('Error fetching sessions:', err.message);
        res.status(500).json({
        error : 'Failed to fetch sessions',
        details : err.message});
    }
}

export const getChat = async (req,res) =>{
    try{
        const id = req.params.id;
        const response = await axios.get(`${FASTAPI_URL}/chats/sessions/${id}`, {
            params: { user_id: req.user.id }
        });
        res.json(response.data);
    }catch(err){
        console.error('Error fetching chat:', err.message);
        res.status(500).json({error:"Failed to fetch chats",details:err.message});
    }
}

export const resumeChat = async (req,res)=>{
    try{
        const id = req.params.id;
        const response = await axios.post(`${FASTAPI_URL}/chats/sessions/${id}`, {
            ...req.body,
            user_id: req.user.id
        });
        res.json(response.data);
    }catch(err){
        console.error('Error resuming chat:', err.message);
        res.status(500).json({error:'Failed to resume the chat',details:err.message});
    }
}

export const newChat = async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_URL}/chats/sessions`, {
      ...req.body,
      user_id: req.user.id
    });
    res.json(response.data);
  } catch (err) {
    console.error('Error starting new chat:', err.message);
    res.status(500).json({ error: 'Failed to start new chat', details: err.message });
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
