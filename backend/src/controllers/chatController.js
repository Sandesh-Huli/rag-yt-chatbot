import dotenv from "dotenv";
dotenv.config();

import axios from "axios";
const FASTAPI_URL = process.env.FASTAPI_URL;

export const getSessions  = async (req,res) => {
    console.log('getting sessions')
    console.log(`FASTAPI_URL: ${FASTAPI_URL}`)
    try{
        const response = await axios.get(`${FASTAPI_URL}/sessions`);
        res.json(response.data);
    }catch (err){
        res.status(500).json({
        error : 'Failed to fetch sessions',
        details : err.message});
    }
}
export const getChat = async (req,res) =>{
    console.log('showing particular chat')
    try{
        const id = req.params.id;
        const response = await axios.get(`${FASTAPI_URL}/sessions/${id}`);
        res.json(response.data);
    }catch(err){
        res.status(500).json({error:"Failed to fetch chats",details:err.message});
    }
}
export const resumeChat = async (req,res)=>{
    console.log('resuming a chat');
    try{
        const id = req.params.id;
        const response = await axios.post(`${FASTAPI_URL}/sessions/${id}`,req.body);
        res.json(response.data);
    }catch(err){
        res.status(500).json({error:'Failed to resume the chat',details:err.message});
    }
}
export const newChat = async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_URL}/sessions`, req.body);
    res.json(response.data);
  } catch (err) {
    res.status(500).json({ error: 'Failed to start new chat', details: err.message });
  }
};

export const deleteChat = async (req, res) => {
  try {
    const id = req.params.id;
    const response = await axios.delete(`${FASTAPI_URL}/sessions/${session_id}`);
    res.json(response.data);
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete chat', details: err.message });
  }
};
