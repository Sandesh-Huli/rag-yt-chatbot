import dotenv from "dotenv";
dotenv.config();

import express from 'express'
import cors from 'cors'
import {chatRoutes} from './routes/chatRoutes.js';

const app = express();

app.use(express.json())
app.use(cors())

app.use('/chats',chatRoutes)

app.get('/',(req,res)=>{
    res.send('Backend is yet to be built')
})

export default app;