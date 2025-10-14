import dotenv from "dotenv";
dotenv.config();

import express from 'express'
import cors from 'cors'
import cookieParser from "cookie-parser";
import session from "express-session";
import './config/mongodb.js'
import {chatRoutes} from './routes/chatRoutes.js';
import {userRouter} from './routes/userRoutes.js';

const app = express();

app.use(express.json())
app.use(cors({
    origin: 'http://localhost:5173',
    credentials: true
}));
app.use(cookieParser())

app.use(session({
    secret:process.env.SESSION_SECRET,
    resave:false,
    saveUninitialized:false,
    cookie:{
        httpOnly:true,
        secure:false,
        maxAge: 1000 * 60 * 60 * 24 * 7,    //1 week
        sameSite:"lax"
    }
}));
app.use('/chats',chatRoutes)
app.use('/user',userRouter)

app.get('/',(req,res)=>{
    res.send('Backend is yet to be built')
})

export default app;