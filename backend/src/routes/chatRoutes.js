import dotenv from "dotenv";
dotenv.config();

import express from 'express'
import {getSessions,getChat, resumeChat, newChat, deleteChat} from '../controllers/chatController.js'
const router = express.Router()

//display all chats route
router.get('/sessions',getSessions)

//show particular chat route
router.get('/sessions/:id',getChat)

//new chat route
router.post('/sessions',newChat)

//resume a chat
router.post('/sessions/:id',resumeChat)

//delete a chat
router.delete('/sessions/:id',deleteChat)

router.get('/',(req,res)=>{
    res.send('chats route')
})
export const chatRoutes = router