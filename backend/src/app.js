import dotenv from "dotenv";
dotenv.config();

import express from 'express'
import cors from 'cors'
import cookieParser from "cookie-parser";
import session from "express-session";
import { requestLoggingMiddleware, errorLoggingMiddleware } from './logging/structuredLogger.js';
import './config/mongodb.js'
import {chatRoutes} from './routes/chatRoutes.js';
import {userRouter} from './routes/userRoutes.js';

const app = express();

// Parse CORS origins from environment variable
const corsOriginsStr = process.env.CORS_ORIGINS || 'http://localhost:5173,http://localhost:5174,http://localhost:5175';
const corsOrigins = corsOriginsStr.split(',').map(origin => origin.trim());

app.use(express.json())
app.use(cors({
    origin: corsOrigins,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(cookieParser())

<<<<<<< Updated upstream
=======
// Setup structured request logging middleware (Issue 40)
>>>>>>> Stashed changes
requestLoggingMiddleware(app);

// Session configuration with env variables
const sessionMaxAge = parseInt(process.env.SESSION_MAX_AGE || '604800000');  // 1 week in ms
const sessionSecure = process.env.SESSION_SECURE === 'true';  // false for dev, true for production HTTPS
const sessionSameSite = process.env.SESSION_SAME_SITE || 'lax';

app.use(session({
    secret:process.env.SESSION_SECRET,
    resave:false,
    saveUninitialized:false,
    cookie:{
        httpOnly:true,
        secure:sessionSecure,
        maxAge: sessionMaxAge,
        sameSite:sessionSameSite
    }
}));
<<<<<<< Updated upstream

// Health check endpoint for Docker/K8s probes (Blocker 3)
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'backend' })
});

=======
>>>>>>> Stashed changes
app.use('/chats',chatRoutes)
app.use('/user',userRouter)

app.get('/',(req,res)=>{
    res.send('Backend is yet to be built')
})

<<<<<<< Updated upstream
=======
// Setup error logging middleware (Issue 40)
>>>>>>> Stashed changes
errorLoggingMiddleware(app);

export default app;